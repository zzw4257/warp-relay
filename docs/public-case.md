# Public real-world case: PyTorch MultiMarginLoss backward

This is a **verification integration / support-boundary case**, not a successful
optimization result. The selected PTX has 542 lines and originates from the
public SentryWard corpus at commit
`421ff2c7d140341f64d2bc1f1edd045b65a7c403`.
Its SHA-256 is `149349f2c99a1dcefe1fa96de5833cb19c9c94b16d5dbbc0dcf1d47df3ed495e`.
The PTX header maps it to
[PyTorch MultiMarginLoss.cu](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/MultiMarginLoss.cu).
The mapping is corroborated by the public reference-binding provenance. We
inspected the pinned CUDA source but did not independently recompile it.

The source declares 128 threads (line 21), the backward kernel at lines 64–120,
the margin-dependent branch at line 94, CTA barriers at lines 107 and 117, and
the one-frame launch at lines 279–293. The PTX header records CUDA 13.0.88,
NVVM 20.0.0 and `sm_100a`. No CUDA compilation, GPU launch, or timing occurred
for this MultiMarginLoss case. The source map and artifact hashes are in
[source-map.json](../examples/pytorch_multimargin/source-map.json).

## Frozen analysis contract

The original public input supplies one CTA of 128 threads, float32/P=1,
`nframe=1`, `dim=8`, null weights, margin 1, mean reduction, distinct global
allocations, and a fixed read-only target value `target[0]=5` via `shape_arrays`.
Those launch, ABI and target restrictions are retained and explicitly disclosed.

The upstream saved scenario also forces PTX branch line 115 to `taken=true`,
corresponding to positive margins. Our new input removes that override and
disables all six configurable assumptions. This broadens the analyzed tensor
data paths instead of selecting one path to obtain a pass. The public input
audit reports `coverage_complete`; that checks parameter coverage, not analysis
support or kernel correctness.

## Actual outcome

- `result = unsupported`
- `checks.synchronization = not_run`
- `checks.equivalence = not_requested`
- `diagnostics[0].code = control_predicate_not_static`
- Diagnostic location: PTX line 115, `@%p24 bra $L__BB10_7;`.

The frontend cannot statically determine that data-dependent control predicate
under this input contract. It suggests representative-control assumptions, but
the integration does not enable them. No candidate is generated, no kernel is
selected, and no result is relabeled as a pass or as a proven bug.

Open the [real run report](../evidence/round2-20261031/public-pytorch/report.html)
for raw stdout, diagnostic payloads and frozen inputs. Run it again with:

```sh
python3 -m warp_relay run examples/pytorch_multimargin/task.json \
  --out runs/public-inspection-new --timeout 10 --memory-mib 1024
```

Exit 2 means the inspected kernel was not accepted; it does not mean the saved
diagnostic is missing. `objective=inspect` runs the same real public verifier
entry but intentionally does not invoke a candidate provider.

## Applicable scope

The integration accepts public compiled PTX plus a concrete input contract.
It demonstrably reaches the real frontend on a production-library kernel.
It has not established broad frontend coverage or automatic repair of this
branched kernel. The deterministic repair baseline remains limited to small
straight-line shared-memory cases, and the edit policy permits only standalone
`bar.sync 0;` changes. The original toy cases remain useful regression tests;
they do not stand in for evidence on real-world optimization.
