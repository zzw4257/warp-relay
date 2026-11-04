## What changed

## Why

## Checks run

- [ ] `python3 scripts/verify_public_snapshot.py` (expected to fail if files changed; note which)
- [ ] `python3 scripts/check_release_docs.py`
- [ ] `node --test ui/src/*.test.mjs`
- [ ] Relevant `python3 -m unittest` modules:

## Evidence and claims

- [ ] No files under `evidence/`, `warp_relay/cases/` or `warp_relay/reviews/` were edited
- [ ] Any new claim links the saved record that supports it, with its limits beside it
- [ ] CHANGELOG.md updated under **Unreleased**
- [ ] No keys, tokens, account details or private paths added
