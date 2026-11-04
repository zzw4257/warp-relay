# Evidence-driven kernel investigation

The current product is a continuous workspace, not a separate gallery and report.
Twelve curated cases share a persistent navigator. Selecting a case changes the
reader in place; each case retains its selected version and access. Code, actual
original/candidate diffs, diagnosis citations and the optional memory relationship
model all use the same recorded source coordinates. `#flow` exposes a real saved
candidate archive through an interactive architecture diagram.

## What is implemented

1. A fixed-rule diagnostic baseline reads immutable verifier facts and bounded
   source excerpts. It does not pretend to reason with a model.
2. A Meta chat-completions adapter sends that same packet, a typed response shape,
   and a frozen diagnostic instruction. The model may identify hypotheses,
   ambiguities and next inspections; it cannot change the verifier category.
3. Citation validation rejects nonexistent facts, invented source locations,
   exact-instruction claims made from debug-region starts, and typed claims of
   GPU execution, measured acceleration or a recorded instruction schedule.
   Validation does **not** prove that free-text explanations are true.
4. An investigation controller can acquire actual source context requested by a
   validated response, attach it to the next request and retain every round.
   It stops on missing authorization, absent credentials, an invalid response,
   uncertain transport, no new evidence, or its one-to-three-round budget.
5. A completed local response can be imported for the workbench. Import checks
   source/verifier hashes, actual context lines, request hash, response schema and
   receipt consistency. These are local audit records, not cryptographic proof
   supplied by the model provider.

This is **iterative diagnostic refinement**. It is not model training, autonomous
agent self-modification or a measured improvement over the fixed-rule baseline.
The existing constrained candidate-edit runner remains separate: it permits only
standalone CTA-barrier edits, runs the real verifier, archives rejected candidates
and preserves the last accepted one. Kernel code, input contract, verifier and
acceptance rules are not editable by the diagnostic loop.

## Current execution status

One real `muse-spark-1.3` TMA response has been imported. See
[the exact receipt, audit, comparison and limits](first-meta-response.md).
The model-requested source inspection read 124 actual lines locally, without a
second model call. Exact conflicting instructions remain unresolved and no model
repair has been executed. The earlier prepared benchmark and pending-round
records remain historical evidence, not updated or relabeled results. All twelve
cases were visible during development, so they are not a blind held-out set.

The available rubric measures citation coverage, mapping ambiguity disclosure and
preservation of inconclusive results. Causal usefulness needs human assessment.
A future model-versus-rule evaluation must retain the model response, request,
usage receipt, prompt policy version and exact input hashes. Citation coverage
alone cannot establish a better diagnosis or a successful repair.

## Commands

```sh
python3 -m warp_relay serve --port 8876
# http://127.0.0.1:8876/#library
# http://127.0.0.1:8876/#flow
python3 -m warp_relay review tma --out runs/tma-prepared
python3 -m warp_relay investigate tma --rounds 2 --out runs/tma-investigation
```

Those commands do not call a model. Only after a **new**, already authorized key
is safely configured, a team-enabled model and existing credits are confirmed:

```sh
python3 -m warp_relay investigate tma --rounds 2 --out runs/tma-meta \
  --model TEAM_ENABLED_MODEL --allow-model-call --credits-authorized
python3 -m warp_relay import-review runs/tma-meta/001-review
```

Import only a completed round; there might not be a second round. The command
rejects overwriting an already installed review. It never buys credits, creates a
key, configures persistent authentication or sends browser-provided credentials.
Each request has a 4,096 completion-token ceiling, a 100 KB evidence packet,
250 KB total request, one attempt and no automatic retry. Up to 240 real context
lines may be acquired per round. These are workload limits, not a dollar-price
estimate. Ambiguous transport is recorded as uncertain and is not retried.

Official transport reference checked:
https://dev.meta.ai/docs/protocols/chat-completions . The endpoint is fixed to
`https://api.meta.ai/v1/chat/completions`; redirects are disabled. No team access
to the documentation's example model is assumed.

## Case boundaries

- WeightNorm: candidate write L126 and read L136 (original L137), modeled actors
  128/0, shared bytes 512–515. No observed GPU interleaving is asserted.
- TMA: Python L290 maps to PTX region starts 348/402/510/613. They are not four
  proven conflicting instructions; the interface keeps every region available.
- TCGen: Python L133 maps to PTX region start L1091 (`shl`). It is not mislabeled
  as the exact memory instruction.
- MaxUnpooling and MultiMarginLoss: unresolved or unsupported analysis remains
  inconclusive and still offers source navigation; no pass/race is invented.
- Softmax's upstream equivalence record and local synchronization-only records
  remain distinct in comparison.
- The B200 35/39 and 39/39 numerical trials both reported a race. They are separate
  saved hardware records, not new runs produced by the CPU workbench.

## Research relationship

The parent research thread suggested GEPA (https://arxiv.org/abs/2507.19457,
https://github.com/gepa-ai/gepa), ShinkaEvolve
(https://github.com/SakanaAI/ShinkaEvolve) and DGM
(https://github.com/jennyzzt/dgm). This implementation borrows the general idea of
retaining feedback and candidates. It does not incorporate their code, claim to
reproduce their algorithms, or report their results as Warp Relay results.
Policy optimization and a genuinely frozen held-out comparison remain future
work. The source and licenses of the actual SentryWard foundation are preserved.

## Verification and reproducibility

Current tests: `evidence/round21-diagnosis/backend-tests.log`, `ui-tests.log`, and
`final/browser-check.json`. The browser checks source/diff identity, preserved
versions and accesses, rapid switching, comparison, inconclusive navigation,
Three.js picking/zoom/reset, 390px navigation and architecture replay controls.
Network transport tests are explicitly synthetic unit fixtures, never demo data.

The architecture animation replays actual saved candidate decisions at editorial
speed. It is not a live model trace or GPU timeline. A running job without final
iterations offers a link to the actual phase-event view; the diagram does not
manufacture progress. Run cancellation/retry remain in the existing job view.
