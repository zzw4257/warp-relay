# Maintaining Warp Relay

How this tree is assembled, checked and kept honest. It's written for whoever
cuts the next snapshot.

## How a snapshot is built

This repository is a **curated export** of a larger development workspace that
also holds film production, private research notes and local job state. The
export is made by an allowlist script in that workspace, not by copying the
workspace wholesale:

1. Only listed directories and files are copied (application, UI source and
   bundle, examples, selected evidence, tests, core docs).
2. Release documents are mapped in: this README, the docs index, contributing,
   security, changelog, issue/PR templates and README images.
3. Every file is scanned. The build **stops** on private-key or token patterns,
   home-directory paths, or excluded media types (`.mp4`, `.mov`, `.wav`, `.mp3`,
   `.m4a`, `.aiff`, keys, certificates, bytecode). Workspace paths are replaced with
   `${WORKSPACE}` and each replacement is counted.
4. `PUBLIC-MANIFEST.json` records, for every file, its source path, the SHA-256 of
   the original bytes, the SHA-256 of the distributed bytes, and any substitutions.
5. A ZIP is written next to the tree and CRC-checked. Nothing is pushed, uploaded
   or published by the build.

`"published": false` in the manifest stays false until a human publishes the tree.

## Verify a snapshot

```sh
python3 scripts/verify_public_snapshot.py   # every manifest hash + recorded data load
python3 scripts/check_release_docs.py       # links, anchors, images, badges, placeholders
node --test ui/src/*.test.mjs               # UI model tests (Node only, no install)
python3 -m unittest discover -s tests -p 'test_diagnosis.py'
```

`verify_public_snapshot.py` fails if any file differs from its manifest hash, so
run it before editing. Any intentional edit invalidates the manifest until the
next snapshot is built.

## README images

All images in `docs/assets/readme/` are real:

| File | How it was made |
| --- | --- |
| `warp-relay-mark.svg`, `warp-relay-mark-dark.svg` | The workbench's own mark (`warp_relay/web/mark.svg`) with a title, plus a dark-mode color variant |
| `workbench-weightnorm.png` | `#case/weightnorm`, Candidate 1, 1440×900 viewport at 2×, scaled to 1600 px |
| `meta-inspect.png` | `#case/tma` → Diagnosis → Meta → step 4 Inspect with L402 selected; the evidence panel cropped to its own bounds |
| `meta-diagnosis-stages.png` | `#case/tma` → Diagnosis → Meta. The evidence panel at each of the four stages, cropped to its own bounds, arranged 2×2 without retouching |
| `evidence-loop.png` | `#flow`, first step of the saved WeightNorm run |
| `gpu-records.png` | `#story`, GPU run 2 |

To refresh them after a UI change, serve this tree on a free port with a
throwaway `--state` directory, capture the same routes with any headless
browser, and keep each PNG under about 300 KB (256-color PNG works well for
this UI). Update captions if what's on screen changed. Never substitute mockups
or generated UI.

## Changelog

Add a line under **Unreleased** with each change. When a snapshot is cut, move
those lines under a dated heading. Describe what changed and link the record
that supports any new claim. Don't introduce version numbers that weren't actually
released.

## Documentation conventions

- The README is the landing page; detail lives in `docs/`. Add new docs to the
  router in `docs/README.md`.
- Every number in the README must come from a saved record. If a record
  changes, update the README and the changelog in the same change.
- Put limits next to the result they qualify.
- Badges are static and must link to the local file that justifies them. Add CI,
  coverage or package badges only after those services actually exist for this
  repository.
- Use relative links only. `scripts/check_release_docs.py` rejects placeholder
  hosts and links to files that don't exist.

## Before publishing (not done yet)

- Choose and approve the repository destination; then add its URL where the
  README currently states that no repository exists.
- Decide on issue tracking and enable private vulnerability reporting, then
  update `SECURITY.md`.
- Re-run the checks above on the exact tree being pushed.
- The current release status lives in [hackathon/publication-readiness-round47.md](hackathon/publication-readiness-round47.md).
