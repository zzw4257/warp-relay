# Native build and release checks — November 4, 2026

[Reproduction](reproduction.md) · [Dependency inventory](../DEPENDENCIES.json)

The delivered R47 public-core ZIP was extracted into an isolated directory.
SentryWard was built from scratch at public commit
`421ff2c7d140341f64d2bc1f1edd045b65a7c403`; no existing verifier binary was reused.
The source checkout was seeded from the already verified, clean local copy of
that public commit. The bootstrap's network-fetch branch was not exercised.
No new system package was installed and no upstream source was modified.

## Build environment

| Component | Observed value |
| --- | --- |
| Machine | macOS, arm64 |
| Python | 3.15.0 |
| CMake / Ninja | 3.31.5 / 1.13.2 |
| Compiler | Apple Clang 21.0.0, C++20 |
| OpenSSL | 4.0.3, linked `libcrypto.4` |
| Boost | 1.92.0 headers |
| Z3 | 4.15.4, enabled |
| Build | Release, two jobs; private tests/tools/diagnostics disabled |

The tested native binary SHA-256 is
`b2ec8160a4c3441591867f180ccbf2a6068e0484cfc3fb61ea4f1198b53929ad`.
The binary and installed dependency trees are not shipped in this repository.
Compiler warnings from the pinned upstream source were retained in the local
build log; they did not fail compilation. No feature was disabled to pass.

## Test results

**All 73 distinct Python tests have a passing result, with zero skipped tests.**
The first full run passed 72; the remaining HTTP test could not bind an
ephemeral loopback port inside the execution sandbox. That exact test passed
in separately authorized host execution. No network setting was changed and
no server was exposed beyond loopback. This is a combined result, not a claim
that the first full command exited successfully.

The seven earlier missing-build errors all passed after bootstrap, including
cancellation at the provider/verifier boundary, retry evidence isolation,
queue continuation and unsupported-result handling. The ten native tests
previously skipped also executed.

```sh
sh scripts/bootstrap.sh
python3 -B -m unittest discover -s tests -v
# Only if the environment blocks loopback binding, repeat the exact HTTP
# test in an execution context authorized to bind a local ephemeral port:
PYTHONPATH=tests python3 -B -m unittest \
  test_workbench.RealWorkbenchTests.test_http_rejects_cross_origin_unknown_actions_and_bad_payloads -v
```

[Machine-readable results](../evidence/release-round48/native-checks.json),
[full initial log](../evidence/release-round48/unittest-native.log) and
[targeted HTTP result](../evidence/release-round48/unittest-http-host.log)
preserve the distinction.

## Documented commands exercised

| Command from the reproduction guide | Result |
| --- | --- |
| Shared-exchange repair, three-iteration budget | Exit 0; baseline potential race; inserted barrier retained as `001-candidate` |
| Public WeightNorm, four-iteration budget | Exit 0; three rejected deletions; `004-candidate` retained under the unchanged scope |
| Public MultiMarginLoss inspection | Expected exit 2; `unsupported`; no selected candidate |
| Offline Meta audit, `--no-install` | Exit 0; four mapped regions and 124 lines inspected; zero additional model calls |

[Command receipts](../evidence/release-round48/reproduction-checks.json) retain
arguments, exit statuses and selected artifact hashes. CLI wall times are
environment-specific execution timings, not kernel performance measurements.
No GPU execution, new Meta call, numerical-equivalence claim or speedup was
introduced by these checks.

## Dependency and portability scope

All 79 dependency-inventory entries match the UI lockfile. Its declared
licenses are 73 MIT, four Apache-2.0, one ISC and one BSD-3-Clause. Runtime
entries have corresponding distributed notices (Three.js also has a separate
license file). This is an inventory/notice check, not a vulnerability scan.
The core Python runtime requires no third-party package. Native verifier
dependencies are separately installed prerequisites and are not redistributed.

These checks validate one existing Mac environment. A new network fetch,
clean dependency installation, Linux, Windows and wheel-only distribution
remain outside this validation. The included source-root workflow is the
supported reproduction path.
