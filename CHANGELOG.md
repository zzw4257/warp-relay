# Changelog

Notable changes to Warp Relay, newest first. The project has no tagged releases
yet; entries are grouped by date. Dates come from saved record timestamps and
file dates on the development machine. `pyproject.toml` declares version
`0.2.0`; it has not been published to any package index.

## Unreleased

### Added

- Owner-approved public repository, branded film cover and native 720p README
  preview, with the 1080p YouTube film retained. See
  [publication record](docs/hackathon/publication-round55.md).

- Shareable workbench locations: `#case/<id>/<version>/<tab>[/<step>[/L<line>]]`
  restores a case, version, tab, Meta step and inspected PTX region after a
  reload or in a new browser. The address bar follows the selection without
  adding history entries; unknown parts are ignored and corrected.
- A **Meta diagnosis** entry in the workbench and Evidence loop headers, and a
  **Meta** tag on the case it belongs to. Both appear only when a saved,
  validated model response exists. A one-line statement of purpose in the header.
- On phones, the header keeps **GPU records** reachable with short labels and
  full accessible names.

- Fresh isolated native build and results for all 73 distinct Python tests,
  including the seven previously missing-build errors and ten formerly skipped
  native tests. The sandbox-bound HTTP check has its passing host retest recorded.
- Reproduction receipts for repair, public WeightNorm, unsupported inspection
  and the offline Meta audit; no new model or GPU call. See `docs/native-validation.md`.
- Redesigned README with the project mark, factual badges, a 60-second
  quickstart, Meta-role and evidence tables, and screenshots captured from the
  real workbench served from this tree.
- Documentation index with a workbench guide (`docs/README.md`),
  `docs/architecture.md`, `docs/maintaining.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, this changelog, and GitHub issue and pull-request templates.
- `scripts/check_release_docs.py`: offline check of README and doc links, anchors,
  image assets, badge targets and forbidden placeholder links.
- Current hackathon copy and publication status under `docs/hackathon/`.

### Fixed

- B200 records now explicitly distinguish the 39-case numerical suite from the
  separate instrumented racecheck execution of the same edited PTX. The
  instrumented one-case numerical check failed; its result was never 39/39.
  Raw evidence is unchanged.

- Opening an unknown case ID while the workbench was already showing a case
  left the previous kernel on screen under the new URL. It now shows an error
  with a link back to the library.
- On phones, returning from the source pane to the evidence pane no longer
  switches away from the Diagnosis tab and the Meta step being read.

### Removed

- The R47 submission and video-description drafts, replaced by the R49 copy
  under `docs/hackathon/`.
- Superseded film-era submission, video-description and media-terms drafts
  (rounds 39–43). They concern the separately produced film, not this source
  tree, and remain in the production archive.

## 2026-11-04

### Added

- First public-core candidate: an allowlisted tree with `PUBLIC-MANIFEST.json`
  (source and distributed SHA-256 per file), `DEPENDENCIES.json`, and
  `scripts/verify_public_snapshot.py`.
- `scripts/audit_meta_review.py`: offline audit of the recorded Meta exchange
  (source identity, request hash, typed citations, receipt consistency).

## 2026-11-03

### Added

- **One real Meta diagnosis.** A single user-authorized `muse-spark-1.3` request
  on the TMA pipeline case: 24.525 s, 6,278 input + 3,309 output tokens, no
  retries. Imported with its packet, request, response, receipt and audit.
- Diagnosis tab with **Evidence → Meta → Checks → Inspect**. The Inspect step
  reads 124 real PTX lines locally (regions 348, 402, 510, 613) with no second call.
- Fixed-rule diagnostic baseline for comparison (ties the model at 2/2 accesses
  cited and 2/2 mapping limits noted).
- `diagnosis.py` (typed claims, citation validation) and `investigation.py`
  (bounded inspection rounds).

### Changed

- Continuous kernel workspace: persistent case navigator; Code, Changes and
  Structure views; evidence tabs; the `#flow` evidence-loop view.

## 2026-11-02

### Added

- Case library of twelve cases: eight saved upstream SentryWard records and
  four local CPU archives, imported by `scripts/import_case_library.py`
  with per-case provenance.
- Spatial witness scene (Three.js) illustrating a recorded access pair, with a
  non-WebGL fallback.

### Changed

- Light workbench visual revision.

## 2026-11-01

### Added

- Interactive loopback workbench: input editing, real bounded CPU jobs,
  candidate diffs, witness navigation, saved phase events, cancellation and
  immutable retry. An exclusive state-directory lock prevents two servers from
  sharing live evidence.

## 2026-10-31

### Added

- Project start. Candidate runner with a deterministic fixed-rule provider and
  barrier-only admission against SentryWard `421ff2c7d140341f64d2bc1f1edd045b65a7c403`.
- Input contract schema (`warp-relay.task/v1`) and original shared-exchange
  microfixtures.
- CPU evidence: microfixture repair (`potential_race` → `race_free`), redundant-
  barrier removal, public MultiMarginLoss stopped as `unsupported`, and public
  WeightNorm: three deletions rejected, a fourth retained within its fixed launch.
- Two recorded B200 validation batches of the rejected WeightNorm candidate
  (numerical suites pass 35/39 and 39/39; separate racecheck executions both
  report a race and fail their own one-case numerical checks) and the GPU validation harness.

---

A promotional film was produced separately during the same period. It is not
part of this source tree and is not tracked in this changelog.
