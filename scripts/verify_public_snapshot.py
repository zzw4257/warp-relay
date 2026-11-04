"""Offline core snapshot checks. No server, model, GPU or network request."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def verify():
    from warp_relay.diagnosis import validate_recorded_packet, parse_response
    from warp_relay.workbench import preset, story

    manifest_path = ROOT / 'PUBLIC-MANIFEST.json'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        for name, record in manifest['files'].items():
            path = ROOT / name
            assert path.is_file() and not path.is_symlink(), name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['distributed_sha256'], name
    index = json.loads((ROOT / 'warp_relay/cases/index.json').read_text())
    assert len(index) == 12 and len({c['id'] for c in index}) == 12
    for c in index:
        case = json.loads((ROOT / 'warp_relay/cases' / (c['id'] + '.json')).read_text())
        assert case['versions'] and case['contract'] and case['source_url']
        assert all(v['source'] and v['raw'] for v in case['versions'])
    for name in ['weightnorm', 'unsupported', 'repair', 'barriers']:
        data = preset(name)
        assert data['kernel'] and data['input']
    hardware = story()
    assert hardware['recorded'] and len(hardware['runs']) == 2
    assert [r['variants']['counterexample']['passed'] for r in hardware['runs']] == [35, 39]
    base = ROOT / 'evidence/round23-meta/first-response'
    review = json.loads((base / 'review.json').read_text())
    packet = validate_recorded_packet(review['packet'])
    response = json.loads((base / 'model-response.json').read_text())
    assert parse_response(response, packet) == review['model']['diagnosis']
    print(json.dumps({'case_count': 12, 'loadable_cpu_presets': 4,
                      'recorded_gpu_trials': 2, 'recorded_model': response['model'],
                      'new_model_calls': 0, 'new_gpu_runs': 0,
                      'manifest_verified': manifest_path.is_file()}, indent=2))


if __name__ == '__main__':
    verify()
