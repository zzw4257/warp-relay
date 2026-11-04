from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RESULTS = {
    "verified", "race_free", "not_wellsynced", "potential_race", "invalid_lifecycle",
    "equivalence_not_proven", "unsupported", "invalid_input", "missing_input", "timeout",
    "memory_budget_exceeded", "analysis_budget_exceeded", "allocation_failed", "tool_failure",
}
CHECKS = {"passed", "failed", "incomplete", "not_run", "not_requested"}
ACTIONABLE_FAILURES = {"potential_race", "not_wellsynced", "invalid_lifecycle"}
PTX_LEXEMES = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|\s+|[A-Za-z_$%.][A-Za-z0-9_$%.]*|[0-9][A-Za-z0-9_.]*|.', re.S)


def digest(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def write_json(path: Path, data) -> None:
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


class RunCancelled(Exception):
    """The caller cancelled its owned process; this is not a verifier verdict."""
    def __init__(self, stdout=b'', stderr=b''):
        super().__init__('Analysis cancelled by the caller')
        self.stdout, self.stderr = stdout, stderr


def read_task(path: Path) -> dict:
    task = json.loads(path.read_text())
    if not isinstance(task, dict):
        raise ValueError("Task must be a JSON object")
    if task.get("schema") != "warp-relay.task/v1":
        raise ValueError("Expected warp-relay.task/v1")
    if not isinstance(task.get("name"), str) or not task["name"].strip():
        raise ValueError("A task name is required")
    if not all(isinstance(task.get(k), str) and task[k] for k in ("kernel", "input")):
        raise ValueError("kernel and input paths are required")
    if not isinstance(task.get("objective"), str) or task["objective"] not in {"repair", "optimize", "inspect"}:
        raise ValueError("objective must be repair, optimize or inspect")
    if not isinstance(task.get("acceptance"), str) or task["acceptance"] not in {"synchronization", "reference_equivalence"}:
        raise ValueError("Choose an explicit acceptance scope")
    if task.get("edit_policy") != "cta_barrier_only":
        raise ValueError("This MVP supports cta_barrier_only edits")
    if not isinstance(task.get("description"), str) or not task["description"].strip():
        raise ValueError("A nonempty kernel specification is required")
    if task["acceptance"] == "reference_equivalence" and not all(task.get(k) for k in ("reference", "reference_binding")):
        raise ValueError("Reference equivalence requires reference and reference_binding")
    for key in ("kernel", "input", "reference", "reference_binding"):
        if task.get(key):
            if not isinstance(task[key], str):
                raise ValueError(f"{key} must be a path string")
            task[key] = str((path.parent / task[key]).resolve(strict=True))
    if task.get("reference_binding") and not task.get("reference"):
        raise ValueError("reference_binding requires reference")
    return task


def validate_result(raw: dict) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("result"), str) or raw["result"] not in RESULTS:
        raise ValueError("Unknown or missing SentryWard result category")
    checks = raw.get("checks", {})
    if not isinstance(checks, dict) or any(not isinstance(checks.get(k), str) or checks[k] not in CHECKS for k in ("synchronization", "equivalence")):
        raise ValueError("Missing or malformed SentryWard checks")
    if not isinstance(raw.get("diagnostics", []), list) or not isinstance(raw.get("evidence", {}), dict):
        raise ValueError("Malformed SentryWard diagnostics/evidence")
    if any(not isinstance(d, dict) for d in raw.get("diagnostics", [])):
        raise ValueError("Diagnostic entries must be objects")
    races = raw.get("evidence", {}).get("races", [])
    if not isinstance(races, list) or any(not isinstance(race, dict) for race in races):
        raise ValueError("Malformed race witnesses")
    for race in races:
        for side in ("first", "second"):
            access = race.get(side, {})
            if not isinstance(access, dict) or not isinstance(access.get("location", {}), dict):
                raise ValueError("Malformed race access")
            line = access.get("location", {}).get("line")
            if line is not None and (type(line) is not int or line <= 0):
                raise ValueError("Race line must be a positive integer")
    return raw


def accepted(raw: dict, scope: str) -> bool:
    if not isinstance(scope, str) or scope not in {"synchronization", "reference_equivalence"}:
        return False
    try:
        validate_result(raw)
    except ValueError:
        return False
    checks = raw["checks"]
    if checks["synchronization"] != "passed":
        return False
    if scope == "reference_equivalence":
        return raw["result"] == "verified" and checks["equivalence"] == "passed"
    return (raw["result"] == "race_free" and checks["equivalence"] == "not_requested") or (
        raw["result"] == "verified" and checks["equivalence"] == "passed")


def feedback(raw: dict) -> dict:
    """Keep all public diagnostics and witnesses, including incomplete results."""
    hints = {
        "potential_race": "Inspect both witnessed accesses and their CTA/warp ownership; establish a legal ordering before consuming shared data.",
        "not_wellsynced": "Inspect failed required orders or barrier counterexamples; all participating threads must reach a matching barrier.",
        "invalid_lifecycle": "Keep initialization before use and completion before free/invalidation.",
        "unsupported": "This is inconclusive. Do not enable assumptions or shrink input scope to get a pass.",
        "equivalence_not_proven": "No equivalence proof was found; this is not a counterexample.",
        "race_free": "Synchronization passed only in the fixed input scope; numerical equivalence was not requested.",
        "verified": "Both requested checks passed under the recorded scope and assumptions.",
    }
    result = {k: raw[k] for k in (
        "result", "checks", "diagnostics", "warnings", "warning_count", "warning_samples_truncated",
        "warnings_complete", "evidence", "assumptions", "assumption_reporting", "assumption_dependent",
        "frontend_assumptions", "verification_limitations", "resource", "assumption_hints",
    ) if k in raw}
    result["action"] = hints.get(raw["result"], "Analysis did not establish acceptance. Preserve this category and inspect its diagnostics.")
    return result


def without_comments(source: str) -> str:
    # Preserve strings and token boundaries. A comment is whitespace, not an
    # invitation to join identifiers or split a numeric literal.
    return "".join(re.sub(r"[^\n]", " ", t) if t.startswith(("//", "/*")) else t
                   for t in PTX_LEXEMES.findall(source))


def without_barriers(source: str) -> list[str]:
    source = without_comments(source)
    source = re.sub(r"(?m)^\s*bar\.sync\s+0\s*;\s*$", "", source)
    return [token for token in PTX_LEXEMES.findall(source) if not token.isspace()]


def check_candidate(original: str, candidate: str) -> None:
    if not isinstance(candidate, str) or not candidate.strip() or len(candidate.encode()) > 256_000:
        raise ValueError("Candidate must contain PTX of at most 256 KB")
    if without_barriers(original) != without_barriers(candidate):
        raise ValueError("Candidate changed non-barrier PTX; cta_barrier_only policy rejected it")


def barrier_count(source: str) -> int:
    source = without_comments(source)
    return len(re.findall(r"(?m)^\s*bar\.sync\s+0\s*;\s*$", source))


def run_process(command: list[str], timeout: float, cwd=None, cancel_event=None):
    """No shell. On POSIX, bound the entire worker/native process group."""
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          shell=False, start_new_session=True, cwd=cwd) as process:
        try:
            if cancel_event is None:
                stdout, stderr = process.communicate(timeout=timeout)
            else:
                deadline = time.monotonic() + timeout
                while True:
                    if cancel_event.is_set():
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        stdout, stderr = process.communicate()
                        raise RunCancelled(stdout, stderr)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(command, timeout)
                    try:
                        stdout, stderr = process.communicate(timeout=min(remaining, 0.05))
                        break
                    except subprocess.TimeoutExpired:
                        continue
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr) from None
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


class Verifier:
    def __init__(self, timeout: float = 15, memory_mib: int = 1024, cancel_event=None):
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0 or type(memory_mib) is not int or memory_mib <= 0:
            raise ValueError("Verifier budgets must be finite and positive")
        self.timeout, self.memory_mib = timeout, memory_mib
        self.cancel_event = cancel_event

    def run(self, kernel: Path, task: dict, output: Path) -> dict:
        output.mkdir()
        working_directory = kernel.resolve().parent
        command = [sys.executable, "-m", "sentryward", "./" + kernel.name, "--input",
                   os.path.relpath(task["input"], working_directory),
                   "--timeout", str(self.timeout), "--memory-limit-mib", str(self.memory_mib)]
        for key, flag in (("reference", "--reference"), ("reference_binding", "--reference-binding")):
            if task.get(key):
                command += [flag, os.path.relpath(task[key], working_directory)]
        started = time.monotonic()
        receipt = {"command": command, "cwd_relative_to_receipt": "..", "started_at": datetime.now(timezone.utc).isoformat(),
                   "kernel_sha256": digest(kernel.read_bytes()),
                   "input_sha256": digest(Path(task["input"]).read_bytes())}
        try:
            kwargs = {'cancel_event': self.cancel_event} if self.cancel_event is not None else {}
            process = run_process(command, self.timeout + 5, cwd=working_directory, **kwargs)
            stdout, stderr = process.stdout, process.stderr
            receipt["exit_code"] = process.returncode
            (output / "stdout.json").write_bytes(stdout)
            (output / "stderr.txt").write_bytes(stderr)
            raw = validate_result(json.loads(stdout))
            if process.returncode != 0 and raw["result"] in {"race_free", "verified"}:
                raise ValueError("Process failed despite a passing payload")
        except RunCancelled as exc:
            (output / 'stdout.partial').write_bytes(exc.stdout)
            (output / 'stderr.txt').write_bytes(exc.stderr)
            receipt.update(cancelled=True, elapsed_seconds=time.monotonic()-started)
            write_json(output / 'receipt.json', receipt)
            raise
        except (ValueError, OSError) as exc:
            raw = {"result": "tool_failure", "checks": {"synchronization": "not_run", "equivalence": "not_run"},
                   "diagnostics": [{"code": "adapter_failure", "stage": "pipeline", "message": str(exc)}]}
        except subprocess.TimeoutExpired as exc:
            (output / "stdout.partial").write_bytes(exc.stdout or b"")
            (output / "stderr.txt").write_bytes(exc.stderr or b"")
            raw = {"result": "timeout", "checks": {"synchronization": "not_run", "equivalence": "not_run"},
                   "diagnostics": [{"code": "adapter_wall_timeout", "stage": "pipeline"}]}
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["measurement"] = "CPU verifier wall time, not GPU kernel latency"
        write_json(output / "receipt.json", receipt)
        write_json(output / "result.json", raw)
        write_json(output / "feedback.json", feedback(raw))
        return raw
