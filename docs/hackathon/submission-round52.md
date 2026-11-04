# Warp Relay — submission copy

Prepared for **Meta Global AI Developer Hackathon 2026** by **zzw4257**. Local
draft; nothing has been submitted. These general-purpose copy blocks accompany
the verified, field-specific text in [submission-form-round52.md](submission-form-round52.md).
Use that document for the signed-in form's 3,000-character fields. This R52 copy supersedes R49; prior drafts remain in the production history.
The GPU wording distinguishes two separate executions of the same edited PTX.

The [official rules](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver)
weight impact, use of Meta AI tooling, technical depth and the demo. The full
version follows that order so each part is easy to find. It makes no claims beyond
the saved records.

## Short (one sentence)

Warp Relay is a local workbench that brings GPU-kernel candidate history,
verifier findings and recorded Meta and GPU investigations together, so a
reviewer can see why a synchronization edit was kept or rejected.

## Medium (one paragraph)

In saved B200 batch 002, a barrier-deletion candidate passed all 39 cases in
the numerical suite. A separate racecheck execution of the same edited PTX
reported a shared-memory race and failed its own one-case numerical check. Warp Relay keeps the kernel, its frozen input contract, each
candidate and the evidence for every decision in one place, and links each
reported access to its PTX line. We sent one real request to Meta's
`muse-spark-1.3` with an immutable verifier packet. Its saved diagnosis is
checked locally against source hashes and typed citations, and its proposed next
step is carried out on the real PTX: Python line 290 maps to four PTX regions,
and one of them (L402) is address arithmetic, not a store. The exact conflicting
pair stays marked unresolved. All included records can be browsed offline with
Python and no GPU, API key or dependency installation; new CPU analyses need the native verifier build, and
no new model or GPU call is made.

## Full

### The problem and who it helps

GPU kernels are increasingly edited by tools and models, and synchronization
mistakes are easy to miss. Finite numerical tests do not establish synchronization safety. In saved B200
validation batch 002, the barrier-deletion candidate passed all **39 cases**
in the uninstrumented suite. A **separate racecheck execution of the same
edited PTX** reported a shared-memory race and failed its own one-case
numerical check. Batch 001 also detected the race in its separate racecheck
execution. These are separate processes and GPU launches with different
coverage and instrumentation, not one execution that both passed and raced.

Warp Relay is for engineers who review synchronization edits on fixed-launch PTX
kernels, and for anyone checking a model's explanation of a kernel bug. It
answers a reviewer's real question: which accesses lost their ordering, under
which contract, and what evidence shows it? Rejected, retained and inconclusive
results stay distinct, and an unsupported input stops as `unsupported` instead
of becoming a pass. It fits the *Push the Frontier* theme's software direction;
choose the track and theme in the form itself.

### How it uses Meta's model

We sent **one** request to **`muse-spark-1.3`** (24.525 s; 6,278 input + 3,309
output tokens; no retry or second round). The request carried an immutable packet:
two recorded 4-byte writes by actors 0 and 64 at shared offset 49152 with no
proven ordering, public PTX excerpts and the fixed contract.

We treat the response as evidence to audit, not as an answer to trust:

1. **Evidence.** The workbench shows exactly what the model was given.
2. **Meta.** The saved hypothesis, its cited facts and its proposed next step:
   *resolve the source mapping*.
3. **Checks.** Source hashes, the request hash and typed citations are validated
   locally. These checks don't prove the explanation correct.
4. **Inspect.** The proposed step is carried out locally on the real PTX (124
   source lines, 0 extra API calls). Python line 290 maps to PTX regions 348, 402,
   510 and 613. L402 is address arithmetic; the other three begin `stmatrix`
   stores. The exact conflicting instruction pair remains unresolved.

The model's contribution is a cited diagnosis plus an inspection plan that the
tool executes and grounds in real source. A deterministic fixed-rule baseline
covers the same evidence: both cite 2/2 accesses and 2/2 mapping limits, so no
model advantage is claimed. The model did not edit any kernel.

### Engineering

- **Bounded loop.** Python freezes each input contract. A fixed-rule provider
  proposes one `bar.sync` insertion or removal at a time. An admission policy
  rejects anything but barrier edits, and the pinned, unmodified SentryWard
  verifier rechecks every candidate under the same contract. Jobs can be started,
  cancelled and retried. Every rejected candidate stays on disk with its evidence.
- **Results.** On public WeightNorm, three barrier deletions were rejected and a
  fourth retained. The barrier it removes sits on a path this fixed launch never
  executes. A separate hand-authored shared-exchange fixture is repaired by
  inserting a barrier.
- **Records.** Twelve cases: eight imported upstream results from PyTorch,
  Triton Gluon, TileLang and TIRx kernels, plus four local CPU archives. Every
  public file is hash-listed in a manifest. An offline script re-audits the Meta
  exchange.
- **Workbench.** Vanilla JavaScript with Pierre Diffs and Three.js. Each reported
  access opens its PTX line. Where only debug regions map, the view says so
  instead of guessing. Each case, version, tab, Meta step and inspected Meta region
  has its own URL, so a reviewer can share the exact evidence.
- **Verification.** A fresh native build passes all 73 distinct Python tests
  (recorded in `docs/native-validation.md`). UI unit tests and a browser
  regression check of the deep links also pass.

### Demo

```sh
python3 scripts/verify_public_snapshot.py
python3 -m warp_relay serve --port 8876 --state runs/my-workbench
```

Then click **Meta diagnosis** in the header for the Meta investigation
(`http://127.0.0.1:8876/#case/tma/public-ptx/meta/evidence`), open
`#case/weightnorm/candidate-1/evidence` for the linked accesses behind a rejected
barrier deletion, or `#story` for the two B200 trials. Browsing these records
needs no GPU, model key, dependency install or network. The full film shows the same records; the current correction changes only
the GPU passage and its provenance wording.

### Prior work and what we added

SentryWard and its research results predate this entry. We pin its public
Apache-2.0 commit `421ff2c7d140341f64d2bc1f1edd045b65a7c403`, leave the verifier
unmodified, and keep its license and the kernel-source attributions. We added the
orchestration and admission controls, the investigation workbench, Meta packet
and response auditing, evidence handling, the original microfixtures and the GPU
reference harness. Per-case provenance records two incomplete generator mappings
(Online softmax and RMSNorm).

### Limits

No measured GPU speedup, no held-out model advantage, no model-driven repair and
no self-training. Synchronization acceptance is not whole-program correctness,
and finite numerical samples are not proof. The TMA case keeps its
representative-election assumptions.

### Next

A frozen, held-out evaluation of diagnosis usefulness, and further model
rounds only where each is explicitly authorized.

## Links and operations: internal, do not paste

- Creator: [zzw4257](https://github.com/zzw4257).
- Repository URL: not created. Publish only the reviewed public-core candidate
  (`deliverables/round52/public-repository-candidate`), never the workspace.
- Video URL: not created. The R52 corrected full film and its Library receipt are the delivery authority.
  No public hosting URL has been created by this preparation.
- Official [event](https://dev.meta.ai/events/global-hackathon),
  [rules](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver),
  [submission portal](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit).
  Deadline November 4, 2026, 9:00 PM ET (November 5, 02:00 UTC).
- Field names, 3,000-character limits, the Public GitHub Repository field, and
  Indie Developer / Push the Frontier choices are verified in the signed-in form.
  Editing and resubmission behavior remain unverified.
- The localhost links work only on a machine running the server. Use the
  repository URL for anything a judge must open remotely.
- Rights and release status: `publication-readiness-round48.md`.

## Form mapping status — checked 2026-11-04

The participant has now been authenticated through the normal browser sign-in.
The actual form is documented in [submission-form-round52.md](submission-form-round52.md),
with field-specific copy under the verified 3,000-character limits. X is optional.
The form requests a Public GitHub Repository; the currently requested private
review repository must not be silently made public. Personal survey answers and
the explicit publication-permission checkbox remain pending. No submission has
been sent and no update/resubmission behavior is assumed.
