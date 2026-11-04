# B200 numerical and racecheck evidence audit

Checked 2026-11-04 against the retained command receipts, harness and raw results.
No new GPU execution was performed for this audit.

The **same edited PTX** passed the 39-case numerical suite in validation batch
002. A **separate instrumented racecheck execution** reported a shared-memory
race. Its own one-case numerical check failed. The two results are not from
one GPU execution; the processes differ in coverage and instrumentation.

## Exact commands and results

All links in this table identify batch 002, without borrowing a finding from
batch 001. `ENTRY` below is the unchanged mangled entry in the manifest and
both original receipts.

| Execution | Command | Raw result |
| --- | --- | --- |
| Uninstrumented numerical suite | `./runner check counterexample.ptx ENTRY counterexample.ptx` | [stdout](../evidence/round4-20261031/gpu-run-002/gpu-results-002/counterexample-numerical.stdout): 39 cases × 3 launches, all pass, zero mismatches; summary line 41. [Receipt](../evidence/round4-20261031/gpu-run-002/gpu-results-002/counterexample-numerical.receipt.json): exit 0. |
| Separate instrumented execution | `compute-sanitizer --tool racecheck --error-exitcode 3 --log-file gpu-results-002/counterexample-racecheck.log --racecheck-report analysis ./runner quick counterexample.ptx ENTRY counterexample.ptx` | [Racecheck log](../evidence/round4-20261031/gpu-run-002/gpu-results-002/counterexample-racecheck.log): shared-memory write/read race at offsets `+0x5f0` / `+0x650`, one report group annotated with 1024 hazards. [Receipt](../evidence/round4-20261031/gpu-run-002/gpu-results-002/counterexample-racecheck.receipt.json): exit 3. |
| Numerical check inside that instrumented process | Part of the same `runner quick` command above | [stdout](../evidence/round4-20261031/gpu-run-002/gpu-results-002/counterexample-racecheck.stdout): `random_0`, one launch, failed with 2050 mismatches; summary `passed:false,cases:1`. |

The [runner orchestration](../evidence/round4-20261031/gpu-run-002/run_validation.py)
launches distinct processes. The [harness](../evidence/round4-20261031/gpu-run-002/weightnorm_runner.cpp)
uses the same deterministic case generator, but `quick` selects only the first
case and one repeat. The full suite uses 32 seeded random cases and seven
structured cases, each repeated three times. No per-launch device-input dump
or recorded GPU instruction schedule is claimed.

## Shared artifact identity

- Edited PTX SHA-256: `b3c7876bacaeb8078a2b9731fb620cbf25fc7ce1aaab344da939f393db404e87`.
- Harness SHA-256: `0d9c8fca4b63552d6c422b29dda465149235c6dda8493d18edd2cd314acc911b`.
- Recorded executable SHA-256: `b7686499b019a31f94df1b8e450417f1b084840bc14e44387deb57f9e1b7d934`.
- [Manifest](../evidence/round4-20261031/gpu-run-002/manifest.json) preserves the exact entry, source identities and fixed contract.

The negative-control edit deletes original PTX line 127, `bar.sync 0;`, from
public WeightNorm PTX. It is not a claim that unchanged PyTorch failed. The
contract uses two rows of 1024 BF16 elements, grid 2, block 256 and 1024 shared
bytes per block. The independent CPU reference and fixed tolerances are in
[GPU validation](gpu-validation.md).

Batch 001 separately passed 35/39 numerical cases, and its racecheck process
also reported a race and failed its one-case numerical check. The two batches
are repeated validation records of the same candidate, not before/after repair.

## Limits

Shared PTX identity does not establish the same instrumented device binary,
GPU schedule, launch or device addresses. Compute Sanitizer instruments its
execution. Runtime offsets are not equated with the static verifier's PTX
witness lines without a demonstrated mapping. Finite reference tests,
synchronization verification and performance measurements remain distinct.
No speedup or model-generated repair follows from these records.

The baseline is the [public SentryWard WeightNorm artifact](https://github.com/gpu-verifier/sentryward/blob/421ff2c7d140341f64d2bc1f1edd045b65a7c403/corpus/pytorch__aten_WeightNorm__sm_100a.ptx),
with its pinned PyTorch source mapping and retained licenses in `NOTICE`.
