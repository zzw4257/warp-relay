# Reproduce the core application

[Docs index](README.md) · [Architecture](architecture.md) · [Maintaining](maintaining.md)

Run commands from the extracted source root. Recorded browsing needs only
Python 3.10+ on macOS/Linux; the code uses Unix process groups, resource limits
and file locking. Windows has not been validated. Python dependencies for the
core application are empty. The checked-in browser bundle loads locally.

```sh
python3 scripts/verify_public_snapshot.py
python3 -m warp_relay serve --port 8876 --state runs/my-workbench
```

Open `http://127.0.0.1:8876/#library`. Before bootstrap, the saved cases, imported
Meta response and B200 records are available; the live verifier reports missing
setup. No model/GPU request is made by opening or inspecting the application.

## Native verifier and bounded CPU runs

Existing system prerequisites: CMake 3.27+, Ninja, C++20, OpenSSL, Boost headers,
Z3, Git and Python. The pinned upstream CMake files are authoritative for their
own dependency constraints. `CMAKE_PREFIX_PATH` may be set for your installation;
bootstrap defaults to `/opt/homebrew` for the original development Mac.

```sh
sh scripts/bootstrap.sh
python3 -m warp_relay doctor
python3 -m warp_relay run examples/neighbor_exchange/task.json \
  --out runs/repair-new --iterations 3 --timeout 15 --memory-mib 1024
python3 -m warp_relay run examples/pytorch_weightnorm/runtime-task.json \
  --out runs/weightnorm-new --iterations 4 --timeout 10 --memory-mib 1024
python3 -m warp_relay run examples/pytorch_multimargin/task.json \
  --out runs/unsupported-new --timeout 10 --memory-mib 1024
```

The last command is expected to exit 2 and preserve `unsupported`. Exit 0 from
the other commands means an artifact was retained under the requested scope,
not a speedup or universal correctness claim. Output directories must be new.
No candidate may edit the checker, contract, reference or non-barrier PTX tokens.

## Offline model-record audit

```sh
python3 scripts/audit_meta_review.py evidence/round23-meta/first-response \
  --out runs/meta-audit-new --no-install
```

This checks source identity, request hash, typed citations, response/receipt
consistency and the actual mapped lines. It makes no API call and does not
replace the installed record. Hash consistency is not provider attestation or
a proof that every model sentence is correct. The diagnostic response is real;
the candidate-edit Meta adapter has only contract tests, not a real repair run.
The key-input helper remains an explicit human CLI step; no credentials are
shipped or collected by the browser. No new call is necessary for this demo.

## Development and tests

UI rebuild requires Node/npm and a one-time dependency install. Run the pinned
lockfile command deliberately when network access is available; it was not
performed during the offline release audit.

```sh
npm --prefix ui ci --ignore-scripts
npm --prefix ui run build
npm --prefix ui test
python3 -m unittest discover -s tests -v
```

The UI model tests themselves need only Node (no `npm ci`), and the docs check
needs only Python:

```sh
node --test ui/src/*.test.mjs
python3 scripts/check_release_docs.py
```

The full Python suite includes actual verifier tests and expects bootstrap.
For a fresh source tree without a native build, use the credential-free recorded
snapshot check above and the non-native tests:

```sh
python3 -m unittest discover -s tests -p test_diagnosis.py -v
python3 -m unittest discover -s tests -p test_local_secret.py -v
python3 -m unittest discover -s tests -p test_gpu_protocol.py -v
```

Optional headless browser QA uses Playwright 1.57.0 and an existing Chromium:

```sh
python3 scripts/check_meta_review.py --base-url http://127.0.0.1:8876 \
  --browser /path/to/existing/chromium --out runs/browser-check
```

No browser installation is automatic. The audit used an already installed
headless executable. A fresh native build and all 73 distinct Python tests
were verified on the existing Mac; see [native validation](native-validation.md)
for the isolated setup and the one loopback-permission retest. A fresh network
fetch, dependency installation and another OS were not exercised.
A wheel alone is not a supported complete
distribution because example/evidence paths are source-root relative.

## GPU reproduction

The GPU harness is optional and disabled by default. Its exact numerical,
sanitizer and timing methodology is in `docs/gpu-validation.md`. Prepare a new
bundle only after a CPU run and execute only on an independently authorized
SM100 allocation with the required CUDA tools. No cloud rental, credential
creation, model download or GPU run is part of the normal quick start.

## Evidence checksums

`PUBLIC-MANIFEST.json` records each included file's source and distributed hash.
Host-path substitutions, if any, are counted. Original model/evidence bytes are
preserved unless a manifest explicitly records a change. Public case JSON has
earlier documented build-path normalization; its upstream hash describes the
original public file, not the normalized payload. The manifest is locally
generated and unsigned. Rebuilding the UI or editing files intentionally
invalidates the snapshot check until a new candidate is prepared.
