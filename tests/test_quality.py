import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from warp_relay.core import Verifier, accepted, check_candidate, digest, run_process, validate_result, write_json
from warp_relay.providers import MetaProvider, OfflineProvider, parse_response
from warp_relay.runner import ROOT, run


def unknown(category="unsupported"):
    return {"result": category, "checks": {"synchronization": "not_run", "equivalence": "not_requested"},
            "diagnostics": [{"code": "control_predicate_not_static", "stage": "synchronization"}], "evidence": {}}


class BoundaryTests(unittest.TestCase):
    def test_token_boundaries_and_string_literals_cannot_change(self):
        for original, changed in [("mov.u32 %r1, 12;", "mov.u32 %r1, 1 2;"),
                                  (' .file 1 "a b.cu"', ' .file 1 "ab.cu"'),
                                  ("mov.u32 %r1, %foo;", "mov.u32 %r1, %f/**/oo;")]:
            with self.subTest(original=original), self.assertRaises(ValueError):
                check_candidate(original, changed)
        check_candidate(' .file 1 "https://example.com/a.cu"\nret;',
                        ' .file 1 "https://example.com/a.cu"\n// comment\nbar.sync 0;\nret;')

    def test_shell_or_python_payload_is_never_an_allowed_candidate(self):
        for payload in ('import os; os.system("touch marker")', '$(touch marker)', '`touch marker`',
                        'ret;\n.include "/private/data"', ''):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                check_candidate('ret;', payload)

    def test_malformed_result_types_are_fail_closed(self):
        for raw in [[], {"result": []}, {"result": "race_free", "checks": {"synchronization": [], "equivalence": "passed"}},
                    {**unknown(), "diagnostics": ["bad"]}, {**unknown(), "evidence": {"races": "bad"}},
                    {**unknown(), "evidence": {"races": [{"first": {"location": {"line": "28"}}}]}}]:
            with self.subTest(raw=raw):
                self.assertFalse(accepted(raw, "synchronization"))
        self.assertFalse(accepted(unknown(), []))

    def test_invalid_budgets_rejected_before_process(self):
        for value in [True, 0, -1, float("nan"), float("inf"), "15"]:
            with self.subTest(timeout=value), self.assertRaises(ValueError):
                Verifier(timeout=value)

    def test_malformed_model_choices_and_oversized_candidate(self):
        for raw in [{"choices": [None]}, {"choices": [[]]}, {"choices": [{"finish_reason": "stop", "message": []}]},
                    {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"kernel":"a"*256001,"rationale":"test"})}}]}]:
            with self.assertRaises(ValueError):
                parse_response(raw)


class ProcessTests(unittest.TestCase):
    def test_arguments_are_not_shell_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "injected"
            argument = f'; touch "{marker}"; $(touch "{marker}")'
            done = run_process([sys.executable, "-c", "import sys; print(sys.argv[1])", argument], 2)
            self.assertEqual(done.stdout.decode().strip(), argument)
            self.assertFalse(marker.exists())

    def test_timeout_kills_child_process_group(self):
        code = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)']); print(p.pid,flush=True); time.sleep(20)"
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            run_process([sys.executable, "-c", code], 0.5)
        self.assertGreater(int(caught.exception.stdout.strip()), 0)
        # The descendant inherits the output pipe. Killing only the worker
        # would leave communicate() waiting for the 20-second descendant.
        self.assertLess(time.monotonic() - started, 3)

    def test_missing_worker_keeps_failure_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            kernel, config = directory / "kernel.ptx", directory / "input.json"
            kernel.write_text("ret;"); config.write_text("{}")
            with patch("warp_relay.core.run_process", side_effect=FileNotFoundError("worker missing")):
                raw = Verifier().run(kernel, {"input": str(config)}, directory / "verification")
            self.assertEqual(raw["result"], "tool_failure")
            self.assertTrue((directory / "verification/receipt.json").is_file())

    def test_unsupported_payload_preserved_verbatim(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); kernel=directory/'k.ptx'; config=directory/'input.json'
            kernel.write_text('ret;'); config.write_text('{}')
            payload = json.dumps(unknown()).encode()
            with patch('warp_relay.core.run_process', return_value=subprocess.CompletedProcess([], 0, payload, b'')):
                raw = Verifier().run(kernel, {'input':str(config)}, directory/'verification')
            self.assertEqual(raw, unknown())
            self.assertEqual((directory/'verification/stdout.json').read_bytes(), payload)


@unittest.skipUnless((ROOT / ".build/sentryward/sentryward-ptx").exists(), "build pinned public verifier first")
class LoopQualityTests(unittest.TestCase):
    def test_reference_python_requires_opt_in_and_is_not_executed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary); reference=directory/'reference.py'; marker=directory/'executed'
            reference.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
            binding=directory/'binding.json'; binding.write_text('{}')
            task=json.loads((ROOT/'examples/neighbor_exchange/task.json').read_text())
            task.update(kernel=str(ROOT/'examples/neighbor_exchange/kernel.ptx'), input=str(ROOT/'examples/neighbor_exchange/input.json'),
                        reference=str(reference), reference_binding=str(binding))
            path=directory/'task.json'; write_json(path,task)
            with self.assertRaisesRegex(ValueError, 'allow-reference-code'):
                run(path,directory/'out',OfflineProvider())
            self.assertFalse(marker.exists()); self.assertFalse((directory/'out').exists())

    def test_inconclusive_baseline_never_reaches_candidate_provider(self):
        def fake_verify(kernel, task, output):
            output.mkdir(); write_json(output/'result.json',unknown()); return unknown()
        provider=Mock(name='provider'); provider.name='test double'
        with tempfile.TemporaryDirectory() as temporary, patch('warp_relay.runner.Verifier.run',side_effect=fake_verify):
            summary=run(ROOT/'examples/neighbor_exchange/task.json',Path(temporary)/'out',provider)
            self.assertEqual(summary['stop_reason'],'baseline_inconclusive')
            self.assertIsNone(summary['selected']); provider.propose.assert_not_called()

    def test_invalid_proposal_is_recorded_without_verification(self):
        provider=Mock(); provider.name='invalid test double'; provider.propose.return_value={'kernel':123,'rationale':'test'}
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'out'; summary=run(ROOT/'examples/neighbor_exchange/task.json',out,provider)
            self.assertEqual(summary['stop_reason'],'invalid_proposal')
            self.assertTrue((out/'001-candidate/rejection.json').is_file())
            self.assertFalse((out/'001-candidate/verification').exists())

    def test_selected_kernel_survives_provider_failure(self):
        provider=Mock(); provider.name='failing test double'; provider.propose.side_effect=ValueError('test provider failure')
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'out'; summary=run(ROOT/'examples/neighbor_exchange/optimization.json',out,provider)
            self.assertEqual(summary['stop_reason'],'blocked')
            self.assertEqual((out/'selected.ptx').read_bytes(),(out/'000-baseline/kernel.ptx').read_bytes())

    def test_public_kernel_uses_real_frontend_and_does_not_choose_branches(self):
        provider=Mock(); provider.name='unused test provider'
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'out'; summary=run(ROOT/'examples/pytorch_multimargin/task.json',out,provider)
            self.assertEqual(summary['iterations'][0]['result'],'unsupported')
            raw=json.loads((out/'000-baseline/verification/stdout.json').read_text())
            self.assertEqual(raw['checks']['synchronization'],'not_run')
            self.assertEqual(raw['diagnostics'][0]['code'],'control_predicate_not_static')
            self.assertEqual(raw['diagnostics'][0]['details']['location']['line'],115)
            inputs=json.loads((out/'inputs/input.json').read_text())
            self.assertNotIn('branch_decisions',inputs); self.assertFalse(any(inputs['assumptions'].values()))
            provider.propose.assert_not_called(); self.assertIsNone(summary['selected'])
            self.assertNotIn(str(Path.home()),(out/'000-baseline/verification/stdout.json').read_text())
            manifest=json.loads((ROOT/'examples/pytorch_multimargin/source-map.json').read_text())
            self.assertEqual(digest((out/'000-baseline/kernel.ptx').read_bytes()),manifest['ptx_sha256'])
            self.assertIn('neither numerical equivalence nor whole-program correctness',(out/'report.html').read_text())

    def test_public_weightnorm_preserves_contract_and_rejects_unsafe_deletions(self):
        example = ROOT / 'examples/pytorch_weightnorm'
        upstream = ROOT / 'vendor/sentryward/examples/pytorch__aten_WeightNorm__sm_100a/input.json'
        public_ptx = ROOT / 'vendor/sentryward/corpus/pytorch__aten_WeightNorm__sm_100a.ptx'
        mapping = json.loads((example / 'source-map.json').read_text())
        self.assertEqual((example / 'input.json').read_bytes(), upstream.read_bytes())
        self.assertEqual(digest(upstream.read_bytes()), mapping['input_sha256'])
        self.assertEqual(digest(public_ptx.read_bytes()), mapping['ptx_sha256'])
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'out'
            summary = run(example / 'task.json', out, OfflineProvider(), iterations=3)
            self.assertEqual([row['result'] for row in summary['iterations']],
                             ['race_free', 'potential_race', 'potential_race', 'potential_race'])
            self.assertEqual(summary['selected'], '000-baseline')
            self.assertEqual(summary['stop_reason'], 'iteration_budget')
            self.assertEqual((out / 'selected.ptx').read_bytes(), public_ptx.read_bytes())
            self.assertEqual((out / 'inputs/input.json').read_bytes(), upstream.read_bytes())
            self.assertFalse(summary['model_executed']); self.assertFalse(summary['gpu_executed'])
            self.assertIsNone(summary['speedup'])
            enabled = set(json.loads(upstream.read_text())['assumptions'])
            for index, row in enumerate(summary['iterations']):
                raw = json.loads((out / row['path'] / 'verification/stdout.json').read_text())
                self.assertEqual(raw['checks']['synchronization'], 'failed' if index else 'passed')
                self.assertEqual(raw['checks']['equivalence'], 'not_requested')
                self.assertTrue(raw['assumption_dependent'])
                self.assertEqual({a['key'] for a in raw['assumptions'] if a['enabled']}, enabled)
                self.assertTrue(all(a['triggered'] is False for a in raw['assumptions']))
                if index:
                    self.assertFalse(row['accepted'])
                    self.assertGreater(raw['evidence']['race_count'], 0)


class ModelFailureTests(unittest.TestCase):
    def test_transport_error_keeps_unknown_outcome_and_never_retries(self):
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary); client=Mock(); client.open.side_effect=urllib.error.URLError('test failure')
            task={'objective':'repair','description':'test','acceptance':'synchronization','input':str(ROOT/'examples/neighbor_exchange/input.json')}
            with patch.dict(os.environ,{'MODEL_API_KEY':'unit-test-placeholder'}),patch('urllib.request.build_opener',return_value=client):
                with self.assertRaisesRegex(ValueError,'uncertain'):
                    MetaProvider('test-model',allow_call=True).propose(task,'ret;',unknown(),[],out)
            self.assertEqual(client.open.call_count,1)
            receipt=json.loads((out/'model-receipt.json').read_text())
            self.assertEqual(receipt['outcome'],'unknown'); self.assertEqual(receipt['automatic_retries'],0)
            self.assertNotIn('unit-test-placeholder',(out/'model-receipt.json').read_text())


if __name__=='__main__':
    unittest.main()
