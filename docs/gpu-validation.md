# Actual B200 execution: public PyTorch WeightNorm

The public baseline and a synchronization-accepted candidate passed independent
CPU-reference numerical tests on NVIDIA B200. A rejected candidate exposed a
real shared-memory race. Three paired benchmark trials show **no demonstrated
speedup**. No model call was involved.

Open the [runtime evidence viewer](../evidence/round4-20261031/runtime-report.html).
The [public source mapping](supported-public-case.md) remains unchanged. This
is compiler-generated production-library PTX, not the hand-authored toy example.

## Three evidence layers

| Layer | Baseline | Accepted candidate | Rejected counterexample |
| --- | --- | --- | --- |
| SentryWard synchronization, fixed public input | race_free | race_free | potential_race |
| Numerical run 1, 39 cases × 3 launches | 39/39 pass | 39/39 pass | 35/39 pass; 958 mismatched values across repetitions |
| Numerical run 2, identical cases | 39/39 pass | 39/39 pass | 39/39 pass |
| Compute Sanitizer racecheck, both runs | 0 hazards | 0 hazards | 1 reported error category, annotated as 1024 hazards |
| Compute Sanitizer memcheck smoke, both runs | 0 errors | 0 errors | 0 errors |

Each numbered run above is a validation batch with separate numerical,
memcheck and racecheck processes. Batch 002's uninstrumented suite passed all
39 cases (three launches each). A separate racecheck execution loaded the same
edited PTX, reported a race, and failed its own one-case numerical check
(2050 mismatches). Batch 001's racecheck execution also failed that check.
The 39/39 pass and race finding therefore do not describe one GPU execution.
The rejected edit never becomes an accepted kernel, and its runtime is not
used for a speedup claim. See [the evidence audit](gpu-claim-audit.md).

The [new CPU candidate loop](../evidence/round4-20261031/weightnorm-cpu/report.html)
extends the previous bounded search by one attempt. Candidate 004 removes the
barrier at original PTX line 167; the fixed 256-thread launch takes the branch
at lines 155–156 that skips this part of the reduction. Static barriers drop
from 16 to 15, but executed synchronization is unchanged. Candidate 001, the
negative control, removes original line 127 before a shared-memory reduction.
All non-barrier PTX tokens, launch dimensions, pointer identities and public
input bytes remain unchanged. There is no retargeting or verifier modification.

The upstream three enabled assumptions remain enabled and are reported
untriggered by the static verifier. Its `assumption_dependent=true` label is
retained. Synchronization is not a numerical-equivalence proof. Formal
reference equivalence remains `not_requested`.

## Numerical method

`gpu/weightnorm_runner.cpp` uses the CUDA Driver API to load the exact PTX on
SM100 and launch two blocks of 256 threads with 1024 shared bytes per block.
The ABI is four distinct device pointers (`w`, `norms`, `v`, `g`) plus
`rowSize=1024`. Device allocations supply the actual buffer sizes absent from
the static pointer-extent model. The host harness was compiled using existing
g++ and CUDA 13.0 headers; the installed CUDA driver JIT compiles the PTX.
No CUDA source recompilation or equivalence to a separately compiled PyTorch
binary is claimed.

The independent CPU reference sums squares in long double, takes the square
root, scales by the quantized BF16 gain, and rounds outputs to BF16 using
round-to-nearest-even. It does not execute SentryWard's Python reference or
reuse the kernel's reduction implementation. Before execution, the limits were
fixed at **1 BF16 ULP** for `w` and **2e-6 relative + 1e-7 absolute** for float32
`norms`. They were not tuned after observing results.

Inputs include 32 deterministic random cases (MT19937 seeds 1701–1732 with an
explicit integer-to-float mapping), all ones, alternating signs, sparse
impulses, 1e-10 and 1e10 scales, zero gains, and zero norms. Each case is run
three times. Zero-norm outputs must have the expected NaN classification;
they are not silently discarded. Each launch reinitializes poisoned outputs,
checks 64-byte canaries around all four allocations, and checks input bytes
were not modified. The instrumented memcheck and racecheck runs each execute
the first random case once; their coverage is narrower than the 39-case suite.

Both positive variants had **zero BF16 bit differences** in both full runs,
and maximum relative norm error `7.25631972414e-08`. The negative control's
first run reached 3 BF16 ULP and about 0.00964 relative norm error. These are
finite tests, not universal correctness, exhaustive bounds safety or full
IEEE numerical equivalence.

## Performance method and actual measurements

Timing runs only after both positive variants pass numerical tests, memcheck
and racecheck. A dedicated nonblocking CUDA stream captures 100 repeated
kernel launches in a graph for each variant. After warmup and graph upload,
CUDA events measure graph replay, normalized per kernel. Each trial contains
31 baseline/candidate pairs with alternating order; three trials run in fresh
processes. Reference computation, transfers, JIT compilation and sanitizer
overhead are outside these timing intervals. Graph replay overhead is included.

| Trial | Baseline median, µs | Selected median, µs | Median paired baseline/selected ratio |
| --- | ---: | ---: | ---: |
| 1 | 1.8272 | 1.8256 | 1.0000× |
| 2 | 1.8278 | 1.8259 | 1.0000× |
| 3 | 1.8176 | 1.8288 | 0.9956× |

This is a small, hot-cache, two-row workload on one B200. Clocks were not
locked, and other GPUs on the server were active. These numbers do not support
an improvement claim, production throughput claim or general optimization
claim. The selected deletion lies outside the executed path for this contract.

## Hardware scope

Two saved runs used NVIDIA B200 hardware with existing CUDA 13.x tools.
No server identity, account inventory or access configuration is distributed.
Reproduction requires a separate authorized compatible allocation.

## Reproduce within an existing authorized allocation

On the local project, with the pinned verifier already built:

```sh
python3 -m warp_relay run examples/pytorch_weightnorm/runtime-task.json \
  --out runs/weightnorm-runtime --iterations 4 --timeout 10 --memory-mib 1024
python3 -m gpu.prepare_bundle --run runs/weightnorm-runtime --out staging/gpu-bundle-new
```

Copy only the generated bundle into a new isolated directory on an authorized
SM100 server. Inside that directory, using the existing CUDA installation:

```sh
g++ -std=c++17 -O2 -Wall -Wextra -I/usr/local/cuda-13.0/include \
  weightnorm_runner.cpp -lcuda -o runner
./runner self-test
cmu-gpu status --gc
cmu-gpu run --project warp-relay-meta --count 1 \
  --purpose "Public WeightNorm validation" --ttl 20m -- \
  timeout 240s python3 run_validation.py --out gpu-results-new --allow-gpu \
  --sanitizer /usr/local/cuda-13.2/bin/compute-sanitizer
```

This wrapper is specific to the original site allocation procedure, not a substitute
for other sites' allocation rules. It requires an active claim, checks artifact
hashes and declines mismatched hardware. All subprocesses use argument lists;
timeouts terminate their own process groups. This is reviewed, trusted local
GPU execution, not a sandbox for arbitrary model-generated kernels.

## Preserved failures and evidence

Run 1 completed numerical and sanitizer execution but did not time kernels:
the adapter expected memcheck's `ERROR SUMMARY` footer for racecheck, which
uses `RACECHECK SUMMARY`. It incorrectly classified both zero-hazard positive
logs as failures and stopped before timing. That original summary and all raw
logs remain unchanged. The parser now checks each tool's exact zero-finding
footer, successful target execution and process exit status. A regression test
covers the different formats, missing target output and nonzero exit status.
Run 2 used the fixed parser and completed the benchmark.

The two folders preserve their exact harness and adapter snapshots, PTX,
input, manifest, compiler version, binary SHA-256, stdout/stderr, sanitizer logs
and per-command receipts. At the time of those GPU experiments the suite had 38 passing tests and no
model call was involved. A later, separate Meta diagnosis is documented in
first-meta-response.md; it does not change these original GPU records.

## Portability boundary

The `cmu-gpu` allocation wrapper is not included in this source package.
`run_validation.py` requires its real `CMU_GPU_CLAIM_ID` and `CUDA_VISIBLE_DEVICES`.
On other clusters, the allocation integration needs a reviewed adaptation; do
not bypass this check by inventing claim values. The saved records and CPU
workflow remain usable without this site-specific wrapper.
