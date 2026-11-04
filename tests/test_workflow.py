import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from warp_relay.core import RESULTS, Verifier, accepted, barrier_count, check_candidate, feedback
from warp_relay.providers import MetaProvider, OfflineProvider, make_request, parse_response
from warp_relay.runner import ROOT, run


def result(category="race_free", synchronization="passed", equivalence="not_requested"):
    return {"result": category, "checks": {"synchronization": synchronization, "equivalence": equivalence},
            "diagnostics": [], "evidence": {}}


class AcceptanceTests(unittest.TestCase):
    def test_inconclusive_results_never_pass_even_with_partial_passed_check(self):
        for category in RESULTS - {"race_free", "verified"}:
            with self.subTest(category=category):
                self.assertFalse(accepted(result(category), "synchronization"))

    def test_scope_and_checks_are_both_required(self):
        self.assertTrue(accepted(result(), "synchronization"))
        self.assertFalse(accepted(result(), "reference_equivalence"))
        self.assertTrue(accepted(result("verified", "passed", "passed"), "reference_equivalence"))
        self.assertFalse(accepted(result("verified", "incomplete", "passed"), "reference_equivalence"))
        self.assertFalse(accepted({"result": "race_free"}, "synchronization"))
        self.assertFalse(accepted(result("verified"), "synchronization"))

    def test_all_diagnostics_and_truncation_are_retained(self):
        raw = result("potential_race", "failed")
        raw.update({"diagnostics": [{"code": "first"}, {"code": "second"}],
                    "warnings_complete": False, "evidence": {"race_samples_truncated": True},
                    "assumptions": [{"key": "representative_branches", "enabled": False}]})
        reduced = feedback(raw)
        for key in ("diagnostics", "warnings_complete", "evidence", "assumptions"):
            self.assertEqual(reduced[key], raw[key])

    def test_only_barrier_edits_allowed(self):
        source = "ld.shared.u32 %r1, [%r2];\nst.global.u32 [%rd0], %r1;\n"
        check_candidate(source, "bar.sync 0;\n" + source)
        for candidate in ("ret;", source.replace("%r1", "%r3"), "@%p bar.sync 0;\n" + source):
            with self.assertRaises(ValueError):
                check_candidate(source, candidate)
        self.assertEqual(barrier_count("// bar.sync 0;\nbar.sync 0;\nbar.sync 0;\n"), 2)


class AdapterTests(unittest.TestCase):
    def verify_fake(self, process):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            kernel, config = directory / "kernel.ptx", directory / "input.json"
            kernel.write_text("ret;")
            config.write_text("{}")
            with patch("warp_relay.core.run_process", return_value=process):
                raw = Verifier().run(kernel, {"input": str(config)}, directory / "verification")
            self.assertTrue((directory / "verification/receipt.json").exists())
            self.assertEqual((directory / "verification/stdout.json").read_bytes(), process.stdout)
            return raw

    def test_zero_exit_code_is_not_a_pass(self):
        process = subprocess.CompletedProcess([], 0, json.dumps(result("potential_race", "failed")).encode(), b"")
        self.assertFalse(accepted(self.verify_fake(process), "synchronization"))

    def test_malformed_output_is_tool_failure_and_kept(self):
        self.assertEqual(self.verify_fake(subprocess.CompletedProcess([], 0, b"not-json", b"error"))["result"], "tool_failure")

    def test_crash_with_passing_payload_is_not_accepted(self):
        process = subprocess.CompletedProcess([], 9, json.dumps(result()).encode(), b"crashed")
        self.assertEqual(self.verify_fake(process)["result"], "tool_failure")

    def test_timeout_retains_partial_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            kernel, config = directory / "kernel.ptx", directory / "input.json"
            kernel.write_text("ret;"); config.write_text("{}")
            with patch("warp_relay.core.run_process", side_effect=subprocess.TimeoutExpired([], 20, output=b"partial")):
                raw = Verifier().run(kernel, {"input": str(config)}, directory / "verification")
            self.assertEqual(raw["result"], "timeout")
            self.assertEqual((directory / "verification/stdout.partial").read_bytes(), b"partial")


class ModelContractTests(unittest.TestCase):
    def test_truncated_or_malformed_generation_is_rejected(self):
        for response in ({}, {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
                         {"choices": [{"finish_reason": "stop", "message": {"content": "[]"}}]}):
            with self.assertRaises(ValueError):
                parse_response(response)

    def test_schema_accepts_only_source_and_rationale(self):
        proposal = {"kernel": "ret;", "rationale": "example"}
        raw = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}]}
        self.assertEqual(parse_response(raw), proposal)

    def test_meta_is_disabled_without_explicit_flag_even_with_ambient_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            task = {"input": str(ROOT / "examples/neighbor_exchange/input.json"), "objective": "repair",
                    "description": "test", "acceptance": "synchronization"}
            with patch.dict(os.environ, {"MODEL_API_KEY": "test-secret"}), patch("urllib.request.build_opener") as network:
                with self.assertRaisesRegex(ValueError, "disabled"):
                    MetaProvider("explicit-test-model").propose(task, "ret;", result(), [], directory)
                network.assert_not_called()
            saved = (directory / "model-request.json").read_text()
            self.assertNotIn("test-secret", saved)
            self.assertEqual(json.loads(saved)["max_completion_tokens"], 4096)


@unittest.skipUnless((ROOT / ".build/sentryward/sentryward-ptx").exists(), "build pinned public SentryWard first")
class RealVerifierTests(unittest.TestCase):
    def test_repair_uses_real_witness_and_reverification(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "repair"
            summary = run(ROOT / "examples/neighbor_exchange/task.json", out, OfflineProvider())
            self.assertEqual([i["result"] for i in summary["iterations"]], ["potential_race", "race_free"])
            self.assertEqual(summary["selected"], "001-candidate")
            witness = json.loads((out / "000-baseline/verification/result.json").read_text())["evidence"]["races"][0]
            self.assertEqual({witness[s]["mode"] for s in ("first", "second")}, {"read", "write"})
            self.assertIsNone(summary["speedup"])
            self.assertFalse(summary["model_executed"])
            self.assertFalse(summary["gpu_executed"])
            self.assertTrue((out / "report.html").exists())
            with self.assertRaises(FileExistsError):
                run(ROOT / "examples/neighbor_exchange/task.json", out, OfflineProvider())

    def test_unsafe_optimization_is_rejected_and_prior_candidate_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "optimize"
            summary = run(ROOT / "examples/neighbor_exchange/optimization.json", out, OfflineProvider())
            self.assertEqual([i["result"] for i in summary["iterations"]], ["race_free", "race_free", "potential_race"])
            self.assertEqual(summary["selected"], "001-candidate")
            self.assertEqual(barrier_count((out / "selected.ptx").read_text()), 1)
            self.assertEqual((out / "selected.ptx").read_bytes(), (out / "001-candidate/kernel.ptx").read_bytes())

    def test_noop_model_cannot_pass_by_deleting_computation(self):
        class DestructiveProvider:
            name = "test-double (not a model)"
            def propose(self, *args):
                return {"kernel": ".visible .entry empty() { ret; }", "rationale": "test adversarial candidate"}
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "policy"
            summary = run(ROOT / "examples/neighbor_exchange/task.json", out, DestructiveProvider(), iterations=1)
            self.assertEqual(summary["iterations"][-1]["result"], "policy_rejected")
            self.assertIsNone(summary["selected"])
            self.assertFalse((out / "001-candidate/verification").exists())

    def test_reference_scope_cannot_silently_downgrade(self):
        with tempfile.TemporaryDirectory() as temporary:
            task = json.loads((ROOT / "examples/neighbor_exchange/task.json").read_text())
            task["acceptance"] = "reference_equivalence"
            file = Path(temporary) / "task.json"
            file.write_text(json.dumps(task))
            with self.assertRaisesRegex(ValueError, "requires reference"):
                run(file, Path(temporary) / "out", OfflineProvider())


if __name__ == "__main__":
    unittest.main()
