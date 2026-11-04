# Security

## Scope and design

Warp Relay is a **local, single-user tool**. Its threat model is a developer
running the workbench on their own machine:

- The HTTP server binds to `127.0.0.1` only, rejects requests whose `Host` or
  `Origin` is not loopback, and has **no authentication**. Do not expose it
  through a proxy, tunnel or public interface.
- The server accepts data, never file paths, shell commands, Python references,
  API keys or GPU launch requests. Existing evidence is served read-only.
- Verifier runs execute the pinned SentryWard binary in their own process group,
  with a timeout and memory budget, and only on PTX that passes the barrier-only
  admission check.
- Executing a Python reference requires an explicit `--allow-reference-code` flag.
- Model calls are off by default. They need an explicit flag plus a key supplied
  at runtime through the `MODEL_API_KEY` environment variable. No key is stored
  in the tree or collected by the browser.
- This snapshot was built from an explicit file allowlist and refused any file
  matching private-key, token or home-directory path patterns
  ([Maintaining](docs/maintaining.md#how-a-snapshot-is-built)). That scan is a
  bounded heuristic, not a guarantee against every secret format.

## Reporting a vulnerability

The repository is public. A dedicated private reporting channel has not been
verified. Until one is available:

- **Do not open a public issue containing secrets, tokens, private paths or
  exploit details.**
- Use the repository’s private vulnerability reporting feature if enabled. Otherwise, open a minimal public issue that
  asks the maintainer for a private channel, with no technical details.

If you find a credential in this tree, treat it as compromised: report its
location (not its value) so it can be revoked and removed.

## Supported versions

Only the latest snapshot of this tree is maintained.
