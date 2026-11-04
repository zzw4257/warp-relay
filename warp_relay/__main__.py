import argparse
import json
import sys
from pathlib import Path

from .providers import MetaProvider, OfflineProvider
from .runner import configure_verifier, run


def main():
    parser = argparse.ArgumentParser(description="Warp Relay: verify, propose a constrained PTX edit, reverify and retain evidence.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check the pinned public verifier without a model call")
    workbench = commands.add_parser('serve', help='Open a loopback-only workbench for real CPU analysis')
    workbench.add_argument('--port', type=int, default=8765)
    workbench.add_argument('--state', type=Path, help='Local job storage; default runs/workbench')
    imported = commands.add_parser('import-review', help='Install a completed local Meta review after checking its source, request and response records')
    imported.add_argument('directory', type=Path)
    diagnostic = commands.add_parser('review', help='Compare fixed-rule and Meta diagnoses of immutable public evidence')
    diagnostic.add_argument('case')
    diagnostic.add_argument('--version', type=int)
    diagnostic.add_argument('--out', type=Path, required=True)
    diagnostic.add_argument('--model', help='Explicit team-enabled Meta model')
    diagnostic.add_argument('--allow-model-call', action='store_true')
    diagnostic.add_argument('--credits-authorized', action='store_true', help='Confirm existing credits/spend authorization; no purchase or top-up')
    investigation = commands.add_parser('investigate', help='Bounded Meta diagnosis → source inspection → revised diagnosis')
    investigation.add_argument('case')
    investigation.add_argument('--version', type=int)
    investigation.add_argument('--out', type=Path, required=True)
    investigation.add_argument('--model')
    investigation.add_argument('--rounds', type=int, default=2)
    investigation.add_argument('--allow-model-call', action='store_true')
    investigation.add_argument('--credits-authorized', action='store_true')
    command = commands.add_parser("run")
    command.add_argument("task", type=Path)
    command.add_argument("--out", type=Path, required=True, help="New evidence directory; existing paths are rejected")
    command.add_argument("--provider", choices=["offline-rule", "meta"], default="offline-rule")
    command.add_argument("--model", help="Explicit Meta model available to your team")
    command.add_argument("--allow-model-call", action="store_true", help="Permit paid Meta requests (no retries); requires MODEL_API_KEY")
    command.add_argument("--allow-reference-code", action="store_true", help="Permit execution of a reviewed, trusted Python reference; never model-generated code")
    command.add_argument("--iterations", type=int, default=3)
    command.add_argument("--timeout", type=float, default=15)
    command.add_argument("--memory-mib", type=int, default=1024)
    args = parser.parse_args()
    try:
        if args.command == 'import-review':
            from .diagnosis import import_review
            print(import_review(args.directory));return 0
        if args.command == 'investigate':
            from .investigation import investigate
            result=investigate(args.case,args.out,args.version,args.model,args.allow_model_call,args.credits_authorized,args.rounds)
            print(json.dumps(result,indent=2));return 0 if result['stop_reason'] in {'not_run','no_new_evidence','round_budget'} else 2
        if args.command == 'review':
            from .diagnosis import review
            result = review(args.case, args.out, args.version, args.model, args.allow_model_call, args.credits_authorized)
            print(json.dumps({'case':args.case,'model_status':result['model']['status'],'calls_attempted':result['receipt']['calls_attempted'],'comparison':result['comparison'],'out':str(args.out)},indent=2))
            return 0 if result['model']['status'] in {'not_run','received_validated'} else 2
        if args.command == "doctor":
            print(json.dumps(configure_verifier(), indent=2))
            return 0
        if args.command == 'serve':
            from .workbench import serve
            if not 0 <= args.port <= 65535:
                raise ValueError('Port must be between 0 and 65535')
            serve(args.port, args.state)
            return 0
        if args.allow_model_call and args.provider != "meta":
            raise ValueError("--allow-model-call requires --provider meta")
        provider = MetaProvider(args.model, args.allow_model_call) if args.provider == "meta" else OfflineProvider()
        result = run(args.task, args.out, provider, args.iterations, args.timeout, args.memory_mib, args.allow_reference_code)
        print(json.dumps({k: result[k] for k in ("selected", "stop_reason", "provider", "model_executed", "performance_status")}, indent=2))
        print("Evidence: " + str(args.out.resolve() / "report.html"))
        failed_stops = {"blocked", "cancelled", "invalid_proposal", "baseline_inconclusive", "candidate_inconclusive"}
        return 0 if result["selected"] and result["stop_reason"] not in failed_stops else 2
    except (ValueError, OSError) as exc:
        print(f"warp-relay: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
