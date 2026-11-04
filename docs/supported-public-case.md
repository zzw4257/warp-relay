# Supported public case: PyTorch WeightNorm forward

This page records the original three-attempt CPU run. The subsequent
[B200 validation](gpu-validation.md) extends it by one accepted deletion and
adds actual numerical tests, sanitizer evidence and timings; the original
records below remain unchanged.

The unchanged public WeightNorm PTX completes synchronization analysis, and
three proposed barrier deletions produce real race witnesses and are rejected.
The original kernel remains selected. This is a successful integration of the
verification loop on a production-source kernel; no optimization was found in
these three attempts.

## Public source and specification

The baseline is the 473-line, compiler-generated
[WeightNorm corpus artifact](https://github.com/gpu-verifier/sentryward/blob/421ff2c7d140341f64d2bc1f1edd045b65a7c403/corpus/pytorch__aten_WeightNorm__sm_100a.ptx)
from SentryWard commit `421ff2c7d140341f64d2bc1f1edd045b65a7c403`.
Its header identifies CUDA 13.0.88, NVVM 20.0.0 and target `sm_100a`, and maps to
[PyTorch WeightNorm.cu](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/WeightNorm.cu)
and [DeviceUtils.cuh](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/cuda/DeviceUtils.cuh).
The public reference-binding provenance corroborates these URLs and the PTX
and input hashes. The source was inspected, not independently recompiled.

The first-dimension forward kernel in WeightNorm.cu (lines 94–139) computes a
row's Euclidean norm and scales its elements: `norms[r] = sqrt(sum(v[r,j]^2))`,
`w[r,j] = g[r] * v[r,j] / norms[r]`. The compiled specialization has BF16
`v`, `g` and `w`, with float32 accumulation and `norms`. The reduction helper
at lines 46–89 uses shared memory and CTA barriers, and the launch at lines
342–351 uses 256 threads and 1024 bytes of shared memory for this specialization.
These source facts explain the workload; they are **not** numerical results
established by this run. Zero norms, rounding and other numerical behavior
were not tested.

The [input.json](../examples/pytorch_weightnorm/input.json) is a byte-for-byte
copy of the pinned public example: two CTAs, 256 threads each, `rowSize=1024`,
1024 dynamic shared bytes per CTA, and distinct `w`, `norms`, `v`, `g` pointer
objects. The public mapping describes two rows of 1024 elements. The input
does not set allocation extents; the verifier reports distinct-object no-alias
pointers with unbounded extents. This run therefore does not establish buffer
size adequacy or bounds safety. There are no branch overrides or shape arrays.

The upstream configuration enables `duplicate_tma_store_benign`,
`representative_election` and `clc_always_fails`. The other three optional
assumptions use pinned defaults of false. We preserve these settings exactly.
All six have `triggered=false` in all four raw results; nevertheless
`assumption_dependent=true` remains the verifier's reported classification.
General frontend/model limitations and the fixed launch still apply. We did
not alter the verifier, input contract or assumptions to obtain a pass.

Artifact SHA-256 values and links are in
[source-map.json](../examples/pytorch_weightnorm/source-map.json):

- PTX: `0fa57a8625c2f74ffad1684891484cbddc22e3f01372aaa2881334509ed75288`
- Input: `66dd6502a0e8e24600fc203e574bfeef8f7fe02d1d48dc603765444412ad45c1`

## Actual bounded run

| Round | Edit relative to original PTX | Result | Retained? |
| --- | --- | --- | --- |
| 000 | Unchanged baseline, 16 CTA barriers | race_free; synchronization passed | Yes |
| 001 | Remove barrier at original line 127 | potential_race; synchronization failed | No |
| 002 | Remove barrier at original line 141 | potential_race; synchronization failed | No |
| 003 | Remove barrier at original line 154 | potential_race; synchronization failed | No |

For example, candidate 001 exposes an unordered shared-memory write by actor
128 at candidate line 126 and read by actor 0 at candidate line 136, overlapping
four bytes at shared offset 512. These are verifier witnesses, not observed
hardware failures. All candidates retain every non-barrier token and are
checked with the same frozen input. The selected PTX equals the public baseline
byte for byte. This does not show that every original barrier is necessary:
only three single-barrier deletions were tested.

Every round has `equivalence=not_requested`; no reference Python was executed.
The provider is `offline-rule (no model)`, `gpu_executed=false`, and
`speedup=null`. Synchronization success establishes neither numerical
equivalence nor whole-program correctness. CPU verifier elapsed times are not
GPU timings.

Open the [run report](../evidence/round3-20261031/public-weightnorm/report.html),
[summary](../evidence/round3-20261031/public-weightnorm/summary.json),
[baseline stdout](../evidence/round3-20261031/public-weightnorm/000-baseline/verification/stdout.json)
or [candidate 001 stdout](../evidence/round3-20261031/public-weightnorm/001-candidate/verification/stdout.json).
Each round keeps the complete raw result and receipt. The
[input audit](../evidence/round3-20261031/weightnorm-input-audit.json) reports
`coverage_complete`, which means parameter coverage, not correctness.

After `sh scripts/bootstrap.sh`, reproduce with a fresh output directory:

```sh
python3 -m warp_relay run examples/pytorch_weightnorm/task.json \
  --out runs/public-weightnorm-new --iterations 3 --timeout 10 --memory-mib 1024

python3 vendor/sentryward/skills/prepare-kernel-input/scripts/audit_input.py \
  --ptx vendor/sentryward/corpus/pytorch__aten_WeightNorm__sm_100a.ptx \
  --input examples/pytorch_weightnorm/input.json \
  --output runs/weightnorm-input-audit-new.json
```

The loop exits 0 because it retains the accepted baseline; it does not claim
an accepted optimization. Stop reason is `iteration_budget`.

## Search boundary

We inspected the metadata of 169 pinned `examples/*/output.json` files. There
were 87 records with a saved synchronization pass and matching public PTX and
input files. WeightNorm was selected for its explicit immutable source mapping,
existing configuration and modest size, without a broad experiment sweep.
Only this one additional kernel was run. Saved upstream verdicts were used for
selection, not substituted for new evidence; no upstream equivalence verdict
is claimed here. The earlier
[MultiMarginLoss unsupported case](public-case.md) remains in the deliverable.
