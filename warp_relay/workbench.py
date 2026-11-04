"""Loopback-only workbench for real, bounded CPU verification jobs.

The HTTP surface accepts data, never server paths, commands, Python references,
API keys or GPU launch requests. Existing evidence remains read-only.
"""
from __future__ import annotations

import json
import fcntl
import math
import mimetypes
import queue
import re
import signal
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .core import feedback, read_task, write_json
from .providers import OfflineProvider
from .runner import ROOT, configure_verifier, run

PRESETS = {
    'weightnorm': ('Public WeightNorm', 'examples/pytorch_weightnorm/runtime-task.json', 4),
    'unsupported': ('Public MultiMarginLoss', 'examples/pytorch_multimargin/task.json', 1),
    'repair': ('Shared-memory repair', 'examples/neighbor_exchange/task.json', 3),
    'barriers': ('Redundant-barrier control', 'examples/neighbor_exchange/optimization.json', 3),
}
RECORDS = {
    'recorded-weightnorm': 'evidence/round4-20261031/weightnorm-cpu',
    'recorded-unsupported': 'evidence/round2-20261031/public-pytorch',
    'recorded-repair': 'evidence/round2-20261031/repair',
    'recorded-barriers': 'evidence/round2-20261031/optimize',
}
TERMINAL = {'completed', 'inconclusive', 'failed', 'cancelled', 'interrupted'}
WEB = Path(__file__).parent / 'web'


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_submission(value):
    fields = {'name', 'description', 'kernel', 'input', 'objective', 'iterations', 'timeout', 'memory_mib'}
    if not isinstance(value, dict) or set(value) - fields:
        raise ValueError('Use PTX, an input contract and analysis settings. Paths, commands, references and provider options are not accepted.')
    value = dict(value)
    for key, limit in [('name', 100), ('description', 6000), ('kernel', 256000)]:
        if not isinstance(value.get(key), str) or not value[key].strip() or len(value[key].encode()) > limit:
            raise ValueError(f'{key}: provide nonempty text of at most {limit} bytes.')
    if re.search(r'(?m)^\s*\.include\b', value['kernel']):
        raise ValueError('PTX includes are not supported. Supply one self-contained kernel.')
    config = value.get('input')
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError as exc:
            raise ValueError(f'Input JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.') from None
    if not isinstance(config, dict) or len(json.dumps(config).encode()) > 64000:
        raise ValueError('Input must be one JSON object, at most 64 KB.')
    if config.get('schema') != 'spverify.kernel-input/v1':
        raise ValueError('Input schema must be spverify.kernel-input/v1.')
    entry = config.get('entry')
    if not isinstance(entry, str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', entry):
        raise ValueError('Input entry must name one PTX kernel entry.')
    if not re.search(r'\.entry\s+' + re.escape(entry) + r'\s*\(', value['kernel']):
        raise ValueError('The input entry does not match a .entry declaration in the PTX.')
    launch = config.get('launch')
    if not isinstance(launch, dict):
        raise ValueError('Input launch must provide grid_dim and block_dim.')
    for field, limit in [('grid_dim', 64), ('block_dim', 1024), ('cluster_dim', 8)]:
        dims = launch.get(field, [1, 1, 1] if field == 'cluster_dim' else None)
        if not isinstance(dims, list) or len(dims) != 3 or any(type(x) is not int or x < 1 for x in dims) or math.prod(dims) > limit:
            raise ValueError(f'Launch {field} needs three positive integers with product at most {limit} in the workbench.')
    if value.get('objective') not in {'repair', 'optimize', 'inspect'}:
        raise ValueError('Choose repair, optimize or inspect.')
    for field, default, low, high in [('iterations', 3, 1, 10), ('timeout', 10, 1, 30), ('memory_mib', 1024, 128, 2048)]:
        number = value.get(field, default)
        if type(number) is not int or not low <= number <= high:
            raise ValueError(f'{field}: use an integer between {low} and {high}.')
        value[field] = number
    value['input'] = config
    return value


def preset(key):
    _, filename, iterations = PRESETS[key]
    task = json.loads((ROOT / filename).read_text())
    kernel = (ROOT / filename).parent / task['kernel']
    if not kernel.is_file() and key in {'weightnorm', 'unsupported'}:
        archive = RECORDS['recorded-weightnorm' if key == 'weightnorm' else 'recorded-unsupported']
        kernel = ROOT / archive / 'inputs/original.ptx'
    config = (ROOT / filename).parent / task['input']
    return {'name': task['name'], 'description': task['description'],
            'kernel': kernel.read_text(), 'input': json.loads(config.read_text()),
            'objective': task['objective'], 'iterations': iterations, 'timeout': 10, 'memory_mib': 1024}


def terminal_status(summary):
    if summary.get('stop_reason') == 'cancelled':
        return 'cancelled'
    results = [r['result'] for r in summary.get('iterations', [])]
    if summary.get('stop_reason') in {'blocked', 'invalid_proposal'} or 'tool_failure' in results:
        return 'failed'
    if any(r in {'unsupported', 'timeout', 'missing_input', 'invalid_input', 'memory_budget_exceeded', 'analysis_budget_exceeded', 'equivalence_not_proven', 'allocation_failed'} for r in results):
        return 'inconclusive'
    return 'completed'


def safe_file(base, relative):
    path = Path(relative)
    if path.is_absolute() or any(p in {'..', '.'} for p in path.parts) or not path.parts:
        raise ValueError('Invalid artifact path.')
    target = base / path
    if not target.resolve().is_relative_to(base.resolve()) or target.is_symlink() or not target.is_file():
        raise FileNotFoundError('Artifact not found.')
    return target


class Jobs:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._state_lock = (self.root / '.workbench.lock').open('a+')
        try:
            fcntl.flock(self._state_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._state_lock.close()
            raise ValueError('This workbench state directory is already open. Use the existing server or a different --state directory.') from None
        self.lock = threading.RLock()
        self.items = {}
        self.cancels = {}
        self.pending = queue.Queue()
        self.closing = threading.Event()
        for path in self.root.glob('*/job.json'):
            if not re.fullmatch(r'[0-9a-f]{16}', path.parent.name):
                continue
            try:
                item = json.loads(path.read_text())
                if item['state'] not in TERMINAL:
                    item.update(state='interrupted', phase='interrupted', error='The workbench stopped before this run completed. Retry creates a new run.', updated_at=now())
                    write_json(path, item)
                self.items[path.parent.name] = item
                self.cancels[path.parent.name] = threading.Event()
            except (ValueError, KeyError):
                continue
        try:
            info = configure_verifier()
            self.readiness = {'ready': True, 'revision': info['revision'], 'message': 'Pinned public SentryWard is ready. CPU analysis only.'}
        except (OSError, ValueError) as exc:
            self.readiness = {'ready': False, 'message': str(exc), 'action': 'Run sh scripts/bootstrap.sh in this project, then restart the workbench.'}
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()

    def persist(self, item):
        item['updated_at'] = now()
        write_json(self.root / item['id'] / 'job.json', item)

    def submit(self, value, retry_of=None):
        value = validate_submission(value)
        if not self.readiness['ready']:
            raise ValueError(self.readiness['message'])
        with self.lock:
            if self.closing.is_set():
                raise ValueError('Workbench is shutting down.')
            if sum(x['state'] not in TERMINAL for x in self.items.values()) >= 4:
                raise ValueError('The local queue has four jobs. Wait or cancel a queued job.')
            key = uuid.uuid4().hex[:16]
            folder = self.root / key
            folder.mkdir()
            write_json(folder / 'request.json', value)
            (folder / 'kernel.ptx').write_text(value['kernel'])
            write_json(folder / 'input.json', value['input'])
            write_json(folder / 'task.json', {'schema': 'warp-relay.task/v1', 'name': value['name'],
                       'description': value['description'], 'kernel': 'kernel.ptx', 'input': 'input.json',
                       'objective': value['objective'], 'acceptance': 'synchronization', 'edit_policy': 'cta_barrier_only'})
            item = {'id': key, 'name': value['name'], 'state': 'queued', 'phase': 'queued', 'created_at': now(),
                    'retry_of': retry_of, 'events': [], 'recorded': False}
            self.items[key] = item
            self.cancels[key] = threading.Event()
            self.persist(item)
            self.pending.put(key)
            return dict(item)

    def cancel(self, key):
        with self.lock:
            item = self.items[key]
            if item['state'] in TERMINAL:
                raise ValueError('This run has finished. Its evidence is preserved; retry creates a new run.')
            self.cancels[key].set()
            item['state'] = 'cancelled' if item['state'] == 'queued' else 'cancelling'
            item['phase'] = item['state']
            self.persist(item)
            return dict(item)

    def retry(self, key):
        with self.lock:
            item = self.items[key]
            if item['state'] not in TERMINAL:
                raise ValueError('Wait for the run to finish or cancel it before retrying.')
            value = json.loads((self.root / key / 'request.json').read_text())
        return self.submit(value, retry_of=key)

    def _work(self):
        while not self.closing.is_set():
            try:
                key = self.pending.get(timeout=0.2)
            except queue.Empty:
                continue
            with self.lock:
                item = self.items[key]
                if item['state'] == 'cancelled':
                    continue
                item.update(state='running', phase='preparing')
                item['events'].append({'at': datetime.now(timezone.utc).isoformat(), 'phase': 'preparing'})
                self.persist(item)
            def event(value):
                with self.lock:
                    item['events'].append(value)
                    if item['state'] != 'cancelling':
                        item['phase'] = value['phase']
                    item['iteration'] = value.get('iteration', item.get('iteration', 0))
                    self.persist(item)
            try:
                folder = self.root / key
                request = json.loads((folder / 'request.json').read_text())
                summary = run(folder / 'task.json', folder / 'run', OfflineProvider(),
                              request['iterations'], request['timeout'], request['memory_mib'],
                              cancel_event=self.cancels[key], on_event=event)
                with self.lock:
                    outcome = terminal_status(summary)
                    item.update(state='completed' if outcome == 'inconclusive' else outcome,
                                outcome=outcome, phase='finished', stop_reason=summary['stop_reason'])
                    if summary.get('error'):
                        item['error'] = summary['error']
                    self.persist(item)
            except Exception as exc:
                with self.lock:
                    item.update(state='failed', phase='failed', error=str(exc))
                    self.persist(item)

    def listing(self):
        with self.lock:
            rows = json.loads(json.dumps(list(self.items.values())))
        for key, relative in RECORDS.items():
            path = ROOT / relative / 'summary.json'
            if path.is_file():
                s = json.loads(path.read_text())
                outcome = terminal_status(s)
                rows.append({'id': key, 'name': s['name'], 'state': 'completed' if outcome == 'inconclusive' else outcome,
                             'outcome': outcome, 'recorded': True, 'created_at': s['started_at'], 'phase': 'finished'})
        return sorted(rows, key=lambda x: (x['recorded'], -float(datetime.fromisoformat(x['created_at']).timestamp())))

    def directory(self, key):
        if key in RECORDS:
            return ROOT / RECORDS[key]
        if key not in self.items:
            raise KeyError(key)
        return self.root / key / 'run'

    def view(self, key):
        folder = self.directory(key)
        if key in RECORDS:
            item = next(x for x in self.listing() if x['id'] == key)
        else:
            with self.lock:
                item = json.loads(json.dumps(self.items[key]))
        result = {'job': item, 'rounds': []}
        if not (folder / 'summary.json').is_file():
            return result
        summary = json.loads((folder / 'summary.json').read_text())
        result['summary'] = summary
        result['contract'] = json.loads((folder / 'inputs/input.json').read_text())
        for row in summary['iterations']:
            step = folder / row['path']
            raw = json.loads((step / 'verification/result.json').read_text()) if (step / 'verification/result.json').exists() else None
            result['rounds'].append({**row, 'source': (step / 'kernel.ptx').read_text(),
                                    'diff': (step / 'change.diff').read_text() if (step / 'change.diff').is_file() else '',
                                    'verification': feedback(raw) if raw else None})
        return result

    def close(self):
        self.closing.set()
        with self.lock:
            for key, item in self.items.items():
                if item['state'] not in TERMINAL:
                    self.cancel(key)
        self.worker.join(timeout=5)
        if not self.worker.is_alive():
            self._state_lock.close()


def story():
    base = ROOT / 'evidence/round4-20261031'
    result = {'runs': [], 'timings': [], 'recorded': True}
    for number in (1, 2):
        directory = base / f'gpu-run-{number:03d}' / f'gpu-results-{number:03d}'
        if not (directory / 'summary.json').exists():
            raise FileNotFoundError('The recorded B200 evidence is missing from this distribution.')
        summary = json.loads((directory / 'summary.json').read_text())
        row = {'number': number, 'variants': {}, 'sanitizers': summary['sanitizers']}
        for name in ('baseline', 'selected', 'counterexample'):
            cases = [json.loads(line) for line in (directory / f'{name}-numerical.stdout').read_text().splitlines()]
            cases = [x for x in cases if x.get('kind') == 'case']
            row['variants'][name] = {'total': len(cases), 'passed': sum(x['passed'] for x in cases),
                                     'failed_cases': [x['name'] for x in cases if not x['passed']]}
        result['runs'].append(row)
        if number == 2:
            result['timings'] = summary['benchmark']
    return result


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, jobs):
        self.jobs = jobs
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'WarpRelay/0.2'
    def setup(self):
        super().setup()
        self.connection.settimeout(5)
    def log_message(self, *_args):
        pass

    def response(self, value, status=200):
        self.send_bytes(json.dumps(value).encode(), 'application/json', status)

    def send_bytes(self, data, mime, status=200, download=False):
        self.send_response(status)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if download:
            self.send_header('Content-Disposition', 'attachment')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def valid_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def do_GET(self):
        if not self.valid_host():
            return self.response({'error': 'Invalid local host.'}, 403)
        path = unquote(urlsplit(self.path).path)
        try:
            if path == '/api/status':
                return self.response({'verifier': self.server.jobs.readiness, 'model': 'not_connected', 'execution': 'local_cpu', 'max_active': 1})
            if path == '/api/presets':
                return self.response([{'id': key, 'label': data[0]} for key, data in PRESETS.items()])
            if path.startswith('/api/presets/'):
                return self.response(preset(path.rsplit('/', 1)[1]))
            if path == '/api/cases':
                return self.response(json.loads((Path(__file__).parent / 'cases/index.json').read_text()))
            review_match = re.fullmatch(r'/api/reviews/([a-z0-9-]+)/([0-9]+)', path)
            if review_match:
                from .diagnosis import saved_review
                return self.response(saved_review(review_match[1], int(review_match[2])))
            if re.fullmatch(r'/api/cases/[a-z0-9-]+', path):
                file = safe_file(Path(__file__).parent / 'cases', path.rsplit('/', 1)[1] + '.json')
                return self.response(json.loads(file.read_text()))
            if path == '/api/jobs':
                return self.response(self.server.jobs.listing())
            if path == '/api/story':
                return self.response(story())
            match = re.fullmatch(r'/api/jobs/([a-z0-9-]+)(?:/files/(.+))?', path)
            if match:
                key, artifact = match.groups()
                if artifact:
                    file = safe_file(self.server.jobs.directory(key), artifact)
                    return self.send_bytes(file.read_bytes(), 'text/plain', download=True)
                return self.response(self.server.jobs.view(key))
            if path.startswith('/evidence/'):
                file = safe_file(ROOT / 'evidence', path.removeprefix('/evidence/'))
                return self.send_bytes(file.read_bytes(), 'text/plain', download=True)
            if path not in {'/', '/app.js', '/workbench.js', '/workbench.js.LEGAL.txt', '/style.css', '/mark.svg'}:
                raise FileNotFoundError()
            file = WEB / ('index.html' if path == '/' else path[1:])
            return self.send_bytes(file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'text/plain')
        except (KeyError, FileNotFoundError):
            self.response({'error': 'Run or artifact not found.'}, 404)
        except (ValueError, OSError) as exc:
            self.response({'error': str(exc)}, 400)

    def do_POST(self):
        origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
        if not self.valid_host() or self.headers.get('Origin') not in origins or self.headers.get('X-Warp-Request') != '1':
            return self.response({'error': 'Requests must originate from this local workbench.'}, 403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.response({'error': 'Use application/json.'}, 415)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 400000:
                return self.response({'error': 'Request body must be at most 400 KB.'}, 413)
            value = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path == '/api/validate':
                valid = validate_submission(value)
                return self.response({'valid': True, 'entry': valid['input']['entry'], 'assumptions': valid['input'].get('assumptions', {}), 'message': 'Submission structure validated. Only SentryWard can establish analysis support.'})
            if path == '/api/jobs':
                return self.response(self.server.jobs.submit(value), 201)
            match = re.fullmatch(r'/api/jobs/([0-9a-f]{16})/(cancel|retry)', path)
            if match:
                key, operation = match.groups()
                return self.response(getattr(self.server.jobs, operation)(key), 201 if operation == 'retry' else 200)
            self.response({'error': 'Action not found.'}, 404)
        except KeyError:
            self.response({'error': 'Run not found.'}, 404)
        except (ValueError, OSError) as exc:
            self.response({'error': str(exc)}, 400)


def serve(port=8765, state=None):
    jobs = Jobs(state or ROOT / 'runs/workbench')
    try:
        server = Server(('127.0.0.1', port), jobs)
    except OSError:
        jobs.close()
        raise
    # The signal handler raises in the main thread; finally cancels only our jobs.
    def stop(*_args):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    print(f'Warp Relay workbench: http://127.0.0.1:{server.server_port}', flush=True)
    print('Local CPU analysis. Meta API and GPU execution are not enabled here.', flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        jobs.close()
        server.server_close()
