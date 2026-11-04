"""Run the real CPU verifier twice; no models, GPU, network or credentials."""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from warp_relay.providers import OfflineProvider
from warp_relay.runner import run

destination = ROOT / "runs" / datetime.now(timezone.utc).strftime("demo-%Y%m%dT%H%M%S%fZ")
for task, name in (("task.json", "repair"), ("optimization.json", "optimize")):
    result = run(ROOT / "examples/neighbor_exchange" / task, destination / name, OfflineProvider())
    print(name, [(i["result"], i["accepted"]) for i in result["iterations"]])
    print(destination / name / "report.html")
    if result["selected"] is None or result["stop_reason"] == "blocked":
        raise SystemExit(2)
