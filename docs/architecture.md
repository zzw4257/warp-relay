# Architecture

Warp Relay is a small Python application (standard library only) with a
prebuilt browser UI. It has three jobs: run a bounded candidate-edit loop
against a pinned verifier, keep every result as an immutable record, and
present those records so a reader can follow a claim back to source.

```text
            task.json (schema warp-relay.task/v1)
            kernel.ptx · input.json · objective · acceptance · edit_policy
                               │
                               ▼
 ┌─ runner.run() ─────────────────────────────────────────────────────────────┐
 │ freeze inputs → verify baseline → [propose → admit → verify → decide] × N  │
 │                                                                            │
 │ providers.OfflineProvider   fixed rules: insert/remove `bar.sync 0;`       │
 │ core.check_candidate        rejects any change other than barriers         │
 │ core.Verifier               SentryWard subprocess: own process group,      │
 │                             timeout + memory budget, cancellable           │
 │ core.accepted               decision under the task's acceptance scope     │
 └───────────────────────────────┬────────────────────────────────────────────┘
                                 ▼
          runs/<new-dir>/  inputs/ · 000-baseline/ · 001-candidate/ …
                           summary.json · events.jsonl · provenance.json
                                 │
           ┌─────────────────────┼──────────────────────────┐
           ▼                     ▼                          ▼
   workbench.py            report.py                diagnosis.py
   loopback HTTP,          offline HTML             packet → typed claims
   one job at a time,      from saved files         → citation checks → audit
   state-directory lock                             (investigation.py: bounded rounds)
           │
           ▼
   warp_relay/web/  ← built from ui/src by esbuild (ui/build.mjs)
```

## Modules

| Module | Responsibility | Key guarantees |
| --- | --- | --- |
| `warp_relay/core.py` | Task reading, result validation, admission, verifier process control | Candidates may differ from the original only in standalone barrier lines (≤ 256 KB PTX); the verifier runs in its own process group, receives a memory budget, and is killed on timeout or cancel |
| `warp_relay/runner.py` | The candidate loop and evidence layout | Output directories must not exist; inputs are copied and hashed first; every phase is checkpointed to `summary.json` and `events.jsonl` |
| `warp_relay/providers.py` | Candidate proposals | `OfflineProvider` is deterministic. `MetaProvider` exists for chat-completions proposals but only has contract tests: no real repair run has used it |
| `warp_relay/diagnosis.py` | Evidence packets, model-response parsing and citation validation | Rejects invented facts, invented locations and exact-instruction claims made from debug-region starts. It cannot prove free text true |
| `warp_relay/investigation.py` | Bounded diagnosis → source acquisition → revised diagnosis | One to three rounds; stops on missing authorization, invalid output or no new evidence |
| `warp_relay/workbench.py` | Loopback HTTP server, job queue, presets, static UI | Accepts data, never paths, commands, keys or GPU launches; one active job; exclusive lock on the state directory |
| `warp_relay/report.py` | Offline HTML report of a run | Every displayed value is read from saved files |
| `warp_relay/cases/`, `warp_relay/reviews/` | Bundled case records and the imported Meta review | Loaded read-only; checked by `scripts/verify_public_snapshot.py` |
| `ui/src/` | Workbench source: case library, code view, diagnosis stages, evidence loop, witness scene | Built to `warp_relay/web/workbench.js` and `style.css`; dependency versions pinned in `ui/package-lock.json` |
| `gpu/` | WeightNorm reference and validation harness | Disabled by default; requires a separately authorized SM100 allocation |

## Objectives and stop reasons

`objective` in a task is one of `repair`, `optimize` or `inspect`. The runner
stops early when a repair baseline already passes (`baseline_already_accepted`),
when an optimization baseline does not (`optimization_requires_accepted_baseline`),
or when the verifier returns a non-actionable result (`baseline_inconclusive`).
Otherwise it runs up to `--iterations` candidates (1–10). The last accepted
version is retained; every rejected candidate stays on disk.

## What runs where

| Action | Where | Network |
| --- | --- | --- |
| Browse cases, Meta record, GPU records | Browser + loopback server | None |
| New CPU analysis | Local SentryWard build | None after bootstrap |
| `bootstrap.sh` | Fetches SentryWard at the pinned commit | Git over HTTPS |
| `review` / `investigate` with `--allow-model-call` | Meta chat-completions API | Yes. Off by default; needs an explicit flag, a key and spend authorization |
| GPU validation | Separately authorized SM100 allocation | Site-specific |

The UI rebuild (`npm --prefix ui ci && npm --prefix ui run build`) is only
needed when changing `ui/src`. The compiled bundle and its legal notices
(`workbench.js.LEGAL.txt`) are checked in.
