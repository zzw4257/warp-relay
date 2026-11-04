# Contributing to Warp Relay

Thanks for taking a look. Warp Relay is a small project whose value depends on
one rule: **every claim on screen must trace back to a saved record.** These
guidelines exist to keep that true.

> This tree is an unpublished candidate. Until a public repository exists,
> there is no issue tracker or pull-request queue to send changes to.

## Before you start

```sh
python3 scripts/verify_public_snapshot.py      # manifest + recorded data load
python3 scripts/check_release_docs.py          # README/docs links, assets, badges
python3 -m unittest discover -s tests -p 'test_diagnosis.py' -v
python3 -m unittest discover -s tests -p 'test_local_secret.py' -v
python3 -m unittest discover -s tests -p 'test_gpu_protocol.py' -v
node --test ui/src/*.test.mjs
```

The full Python suite (`python3 -m unittest discover -s tests -v`) also runs
the real verifier and needs `sh scripts/bootstrap.sh` first.
[Reproduction](docs/reproduction.md) lists the exact prerequisites.

## Ground rules

1. **Evidence is immutable.** Do not edit files under `evidence/`,
   `warp_relay/cases/` or `warp_relay/reviews/`. Add a new record and
   document it instead.
2. **New claims need a record.** A result belongs in the README or UI only if a
   saved file supports it and a reader can open that file.
3. **Keep limits beside results.** If a result is scoped (fixed launch, assumptions,
   finite samples), say so in the same row, caption or panel, not only in a footnote.
4. **Don't turn "unsupported" into "passed".** Inconclusive outcomes stay visible.
5. **No credentials in the tree.** Model keys are entered at runtime only. Never
   commit `.env` files, tokens or account configuration. `.gitignore` covers the
   common cases; review `git status` anyway.
6. **Model calls and GPU runs are explicit.** Nothing in tests or the default
   workbench may contact a model API or launch GPU work.
7. **Respect upstream licenses.** SentryWard and the public kernel sources keep
   their own terms and attribution. Update `NOTICE`, `licenses/` and
   `docs/provenance.md` when adding material from elsewhere.

## Changing the UI

Edit `ui/src/`, then rebuild the checked-in bundle:

```sh
npm --prefix ui ci --ignore-scripts
npm --prefix ui run build
node --test ui/src/*.test.mjs
```

Commit the rebuilt `warp_relay/web/workbench.js`, `style.css` and
`workbench.js.LEGAL.txt` together with the source change. If you change what a
screen shows, re-capture the affected README images from a locally served tree
(see [Maintaining](docs/maintaining.md#readme-images)).

## Pull requests

Keep each change focused, say which checks you ran, and add a line under
**Unreleased** in [CHANGELOG.md](CHANGELOG.md). If a change adds or alters a
claim, link the record that supports it.

## Reporting problems

Describe what you ran, what you expected and what you saw. Include the run
directory's `summary.json` if relevant, after checking that it contains no
private paths. For security issues, follow [SECURITY.md](SECURITY.md).
