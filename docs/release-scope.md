# Release scope and licenses

This curated source tree was made public with the owner’s approval on November
4, 2026. The [publication record](hackathon/publication-round55.md) separates
repository publication, hosted film and the still-pending competition submission.
The offline audit described here is a bounded engineering check, not legal
clearance or a guarantee that every possible secret format would be detected.

## Included

- New Apache-2.0 code: application, runner, diagnosis/audit, workbench, GPU
  harness, tests and scripts.
- Original shared-exchange microfixtures and their input contracts.
- The pinned UI build files (`ui/package.json`, `ui/package-lock.json`,
  `ui/build.mjs`), UI source and the compiled bundle with its legal notices.
- Twelve case records; four local CPU archives; two recorded B200 trials; one
  Meta request, response, receipt and audit; public input mappings.
- Documentation, README images captured from this application, and the
  current hackathon copy under [`hackathon/`](hackathon/).

Dependencies are not vendored, except the compiled UI and its preserved notices.
SentryWard is fetched from its pinned public commit only when you run
`scripts/bootstrap.sh`.

## Excluded

- Keys, account and session configuration, local jobs, server inventory,
  machine-specific transfer receipts, agent/CLI transcripts, private research
  trees, feedback attachments, vendor/build/dependency caches and binaries.
- The offline packaging script does not create Git history or change remote visibility.
- **The promotional film and all production media**: captures, generated
  narration and imagery, music, sound effects, raw audio, mix stems and the film
  toolchain. This is a reproducible core application, not a film project. The
  separately delivered production archive keeps that work, its licenses and
  its history.

## Prior work and attribution

| Material | Evidence in this tree | Disposition |
| --- | --- | --- |
| SentryWard `421ff2c…` | Upstream Apache-2.0 license; per-case manifests | License retained; verifier unmodified; prior work, not a hackathon addition |
| PyTorch-derived PTX and source mappings | Pinned source revision; `licenses/PyTorch-LICENSE.txt` | Attribution and terms retained; compiler reproduction not established |
| Triton Gluon-derived PTX and mappings | Pinned source revision; Triton MIT license | Attribution and terms retained |
| TileLang Online softmax / TIRx RMSNorm snapshots | Public SentryWard distribution; case manifests | Distribution retained; **exact generator provenance incomplete**; not relicensed by this project |
| Pierre Diffs, Shiki, Three.js and build dependencies | `ui/package-lock.json`, bundled legal comments, `licenses/`, `DEPENDENCIES.json` | Exact versions and notices retained |

Warp Relay's own additions are orchestration and admission controls, evidence
persistence, Meta packet and response validation, the workbench and its linked
navigation, the GPU reference harness, original microfixtures and new tests.

The Online softmax snapshot has no exact public generator URL. The linked
RMSNorm source corroborates, but is not asserted to produce, the exact PTX. The
pinned SentryWard distribution is the source actually copied. Keep these gaps
visible; don't describe these kernels as original.

## Publication status

The source repository is public. The complete film is separately hosted on
YouTube, with a compressed GitHub attachment linked from the README. Neither
film is a binary in this core source tree. Their licenses and provenance are
recorded in [README media](hackathon/readme-media.md).

See [the current publication record](hackathon/publication-round55.md) and
[submission copy](hackathon/submission-round52.md). The R47–R53 readiness records
are historical checkpoints, not current claims that hosting is absent.
