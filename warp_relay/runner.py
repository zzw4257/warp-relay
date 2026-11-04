from __future__ import annotations

import difflib
import copy
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core import ACTIONABLE_FAILURES, RunCancelled, Verifier, accepted, barrier_count, check_candidate, digest, feedback, read_task, write_json
from .report import render_report

ROOT = Path(__file__).resolve().parents[1]
SENTRYWARD_REVISION = "421ff2c7d140341f64d2bc1f1edd045b65a7c403"


def configure_verifier() -> dict:
    source = ROOT / "vendor/sentryward"
    native = ROOT / ".build/sentryward/sentryward-ptx"
    if not native.is_file():
        raise ValueError("Public SentryWard build missing. Follow README setup first.")
    rev = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True)
    if rev != SENTRYWARD_REVISION or dirty:
        raise ValueError("SentryWard must be the unmodified pinned public checkout")
    os.environ["PYTHONPATH"] = str(source)
    os.environ["SENTRYWARD_PTX_NATIVE"] = str(native)
    return {"repository": "https://github.com/gpu-verifier/sentryward", "revision": rev,
            "native_sha256": digest(native.read_bytes()), "python": sys.version,
            "platform": platform.platform(),
            "agent_sources": {str(p.relative_to(ROOT)): digest(p.read_bytes())
                              for p in sorted((ROOT / "warp_relay").glob("*.py"))}}


def run(task_path: Path, out: Path, provider, iterations=3, timeout=15, memory_mib=1024, allow_reference_code=False, cancel_event=None, on_event=None) -> dict:
    if not 1 <= iterations <= 10:
        raise ValueError("Use 1–10 candidate attempts")
    task = read_task(task_path)
    if task.get("reference") and not allow_reference_code:
        raise ValueError("Reference capture executes Python. Review the trusted file and explicitly enable --allow-reference-code.")
    verifier = Verifier(timeout, memory_mib, cancel_event=cancel_event)
    provenance = configure_verifier()
    # Never overwrite prior evidence or reuse stale result directories.
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = out / "inputs"
    inputs.mkdir()
    frozen = dict(task)
    input_hashes = {}
    for key in ("kernel", "input", "reference", "reference_binding"):
        if task.get(key):
            name = {"kernel": "original.ptx", "input": "input.json", "reference": "reference.py",
                    "reference_binding": "reference_binding.json"}[key]
            destination = inputs / name
            shutil.copyfile(task[key], destination)
            frozen[key] = str(destination)
            input_hashes[key] = digest(destination.read_bytes())
    source = Path(frozen["kernel"]).read_text()
    original = source
    write_json(inputs / "task.json", {k: str(Path(v).name) if k in input_hashes else v for k, v in frozen.items()})
    write_json(out / "provenance.json", {**provenance, "inputs": input_hashes})
    summary = {
        "schema": "warp-relay.run/v1", "name": task["name"], "objective": task["objective"],
        "started_at": datetime.now(timezone.utc).isoformat(), "provider": provider.name,
        "acceptance_scope": task["acceptance"], "description": task["description"],
        "model_executed": False, "model_status": "not_called", "gpu_executed": False, "speedup": None,
        "performance_status": "not_measured", "iterations": [], "selected": None,
        "stop_reason": "iteration_budget", "verifier": provenance,
    }
    def checkpoint(phase, **details):
        summary['phase'] = phase
        summary['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_json(out / 'summary.json', summary)
        event = {'at': summary['updated_at'], 'phase': phase, **details}
        with (out / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(event) + '\n')
        if on_event:
            on_event(event)

    def check_cancelled():
        if cancel_event is not None and cancel_event.is_set():
            raise RunCancelled()

    try:
        check_cancelled()
        checkpoint('verifying_baseline', iteration=0)
        baseline = out / "000-baseline"
        baseline.mkdir()
        (baseline / "kernel.ptx").write_text(source)
        raw = verifier.run(baseline / "kernel.ptx", frozen, baseline / "verification")
        check_cancelled()
        baseline_ok = accepted(raw, task["acceptance"])
        baseline_row = {"kernel_sha256": digest(source), "result": raw["result"], "accepted": baseline_ok}
        history = [{**baseline_row, "verification": feedback(raw)}]
        summary["iterations"].append({"path": baseline.name, "kind": "baseline", **baseline_row})
        if baseline_ok:
            summary["selected"] = baseline.name

        checkpoint('baseline_verified', iteration=0, result=raw['result'], accepted=baseline_ok)
        if task["objective"] == "inspect":
            summary["stop_reason"] = "inspection_complete"
        elif task["objective"] == "repair" and baseline_ok:
            summary["stop_reason"] = "baseline_already_accepted"
        elif task["objective"] == "optimize" and not baseline_ok:
            summary["stop_reason"] = "optimization_requires_accepted_baseline"
        elif not baseline_ok and raw["result"] not in ACTIONABLE_FAILURES:
            summary["stop_reason"] = "baseline_inconclusive"
        else:
            for i in range(1, iterations + 1):
                check_cancelled()
                checkpoint('proposing_candidate', iteration=i)
                step = out / f"{i:03d}-candidate"
                step.mkdir()
                proposal = provider.propose(copy.deepcopy(frozen), source, copy.deepcopy(raw), copy.deepcopy(history), step)
                check_cancelled()
                if (step / "model-receipt.json").is_file():
                    receipt = json.loads((step / "model-receipt.json").read_text())
                    summary["model_executed"] |= receipt.get("outcome") == "received"
                if proposal is None:
                    summary["stop_reason"] = "no_more_candidates"
                    break
                if (not isinstance(proposal, dict) or set(proposal) != {"kernel", "rationale"}
                        or any(not isinstance(v, str) or not v.strip() for v in proposal.values())
                        or len(proposal["kernel"].encode()) > 256_000):
                    write_json(step / "rejection.json", {"reason": "Malformed or oversized proposal", "result": "policy_rejected"})
                    summary["stop_reason"] = "invalid_proposal"
                    break
                write_json(step / "proposal.json", {"provider": provider.name, **proposal})
                candidate = proposal["kernel"]
                (step / "kernel.ptx").write_text(candidate)
                (step / "change.diff").write_text("".join(difflib.unified_diff(
                    source.splitlines(True), candidate.splitlines(True), fromfile="previous.ptx", tofile="candidate.ptx")))
                checkpoint('candidate_proposed', iteration=i, kernel_sha256=digest(candidate))
                row = {"path": step.name, "kind": "candidate", "kernel_sha256": digest(candidate),
                       "rationale": proposal["rationale"], "accepted": False}
                try:
                    check_candidate(original, candidate)
                    if any(x["kernel_sha256"] == row["kernel_sha256"] for x in history):
                        raise ValueError("Repeated candidate")
                    if any(digest(Path(frozen[k]).read_bytes()) != h for k, h in input_hashes.items()):
                        raise ValueError("Frozen task inputs changed during run")
                except ValueError as exc:
                    row.update({"result": "policy_rejected", "reason": str(exc)})
                    summary["iterations"].append(row)
                    history.append(row)
                    checkpoint('policy_rejected', iteration=i, result='policy_rejected', accepted=False)
                    continue
                check_cancelled()
                checkpoint('verifying_candidate', iteration=i)
                candidate_raw = verifier.run(step / "kernel.ptx", frozen, step / "verification")
                check_cancelled()
                improves = task["objective"] != "optimize" or barrier_count(candidate) < barrier_count(source)
                row.update({"result": candidate_raw["result"], "accepted": accepted(candidate_raw, task["acceptance"]) and improves,
                            "barriers_before": barrier_count(source), "barriers_after": barrier_count(candidate)})
                if not improves:
                    row["reason"] = "No reduction in barrier count; GPU performance remains unmeasured"
                success_reason = ('Passed the requested synchronization scope and reduced static barriers; performance is not established.'
                                  if task['objective'] == 'optimize' else
                                  'Passed the requested synchronization scope after the proposed repair; numerical equivalence and performance are not established.')
                row.setdefault('reason', success_reason if row['accepted'] else feedback(candidate_raw)['action'])
                summary["iterations"].append(row)
                checkpoint('candidate_verified', iteration=i, result=candidate_raw['result'], accepted=row['accepted'])
                history.append({**row, "verification": feedback(candidate_raw)})
                if not row["accepted"] and candidate_raw["result"] not in ACTIONABLE_FAILURES | {"race_free", "verified"}:
                    summary["stop_reason"] = "candidate_inconclusive"
                    break
                if row["accepted"]:
                    summary["selected"] = step.name
                    source, raw = candidate, candidate_raw
                    if task["objective"] == "repair":
                        summary["stop_reason"] = "accepted_repair"
                        break
                elif task["objective"] == "repair":
                    # Repair the latest failed attempt. Optimization keeps the
                    # last accepted kernel and includes rejections in history.
                    source, raw = candidate, candidate_raw
    except RunCancelled:
        summary['stop_reason'] = 'cancelled'
    except (ValueError, OSError, KeyError, TypeError) as exc:
        summary["stop_reason"] = "blocked"
        summary["error"] = str(exc)
    finally:
        if summary["selected"]:
            shutil.copyfile(out / summary["selected"] / "kernel.ptx", out / "selected.ptx")
        # An actual model response can be malformed; still disclose that call.
        for receipt_path in out.glob("*/model-receipt.json"):
            receipt = json.loads(receipt_path.read_text())
            outcome = receipt.get("outcome")
            summary["model_status"] = outcome
            if outcome == "received":
                summary["model_executed"] = True
            elif outcome in {"unknown", "http_error"} and summary["model_executed"] is not True:
                summary["model_executed"] = None
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        checkpoint('finished', stop_reason=summary['stop_reason'])
        render_report(out)
    return summary
