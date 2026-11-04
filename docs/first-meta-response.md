# One real Meta diagnosis

The user executed one authorized request with hidden, process-local key input on
2026-11-03. The project now contains that response, its public input, its local
receipt, the fixed-rule comparison and an offline audit. No new request was made
while importing, inspecting, testing or filming it. The response is available at
`http://127.0.0.1:8876/#case/tma` under **Diagnosis → Meta**.

| Recorded fact | Value |
| --- | --- |
| Requested and returned model | `muse-spark-1.3` |
| Response ID | `chatcmpl-01a1a273-d165-758e-8c66-aea476643b2c` |
| Attempted calls / automatic retries | 1 / 0 |
| Local request elapsed time | 24.525 s |
| Usage | 6,278 prompt + 3,309 completion = 9,587 tokens |
| Case / version | Public TMA pipeline / 0 |
| Source SHA-256 | `905051ea85bc9b8444fa65699618c05d632bc87b310bc1f5edbcf92e684f49ce` |

## What the response says, and what we checked

The model identifies two modeled four-byte writes overlapping shared offset
49152, with no proven required ordering. It keeps the source mapping ambiguous:
Python line 290 maps to PTX region starts 348, 402, 510 and 613. These are not
four proven conflicting instructions. Source inspection confirms that line 402
is `add.s32` address arithmetic, while the other three begin `stmatrix` regions.
Nearby `cp.async.bulk.wait_group.read` and `bar.sync` instructions are present;
their existence alone does not establish ordering between the witnessed writes.
Representative election is enabled and triggered. The result remains dependent
on the verifier's assumptions, fixed launch and supplied TMA descriptors.

The audit checked the frozen source/verifier identity, exact packet and request
hash, response model/ID/usage against the receipt, parsed response against the
stored diagnosis, and every typed citation. It also read the actual surrounding
source and checked the main explanation. These are local consistency and source
checks, not a provider-signed attestation or a proof that arbitrary prose is true.

The model's proposed next inspection was carried out **locally**: four immutable
regions, 124 source lines, zero further model calls. The workbench exposes each
region as a source-navigation action and keeps the non-exact mapping label.

## Comparison and remaining gap

Both the fixed rules and the model cite 2/2 accesses and acknowledge 2/2 mapping
ambiguities. There is no measured advantage on those metrics. The model adds a
source-inspection question connecting the overlap, instruction classes and
nearby synchronization. This is a qualitative observation on one visible case,
not a held-out accuracy gain or a measured investigation-time improvement.

Exact conflicting PTX instructions remain unresolved. No model code edit,
repair, second model round, numerical-equivalence result, new GPU execution or
speedup follows from this response. The separate CPU candidate loop still uses
fixed rules. This is not recursive self-training or agent self-modification.

## Reproduce the audit and UI checks without a credential

```sh
python3 scripts/audit_meta_review.py evidence/round23-meta/first-response \
  --out evidence/local-meta-audit --no-install
python3 -m warp_relay serve --port 8876
# In a second terminal, with Playwright installed:
python3 scripts/check_meta_review.py
```

`warp_relay/reviews/tma-0.json` is the imported response;
`tma-0-audit.json` is the source/hash-matched offline audit. The original public
packet, request, raw response and receipt are copied into
`evidence/round23-meta/first-response/`. No key is present. The script refuses an
inconsistent record; the workbench only attaches the audit to matching source
and diagnosis hashes.

## Product behavior

The four native stages are Evidence, Meta, Checks and Inspect. They show the
actual immutable input, recorded call, audit limits and completed local source
inspection. They are navigable records, not a fake live inference animation.
State changes use a short interruptible transition with reduced-motion support.
Desktop source remains beside diagnosis; phones switch from the selected region
back to source. The recorded response opens at Evidence, while other cases retain
their honest missing-model state.

Browser checks cover the request receipt, all four region links, baseline/model
switching, the 390px layout, correct version labels and no browser POST requests.
The broader case regression preserves comparison, back navigation, 3D linkage,
inconclusive diagnostics and protection against delayed stale responses.

## Completed-run consistency fix

Final movie inspection revealed that the last CPU snapshot could finish while
latest-result following still displayed the previous candidate. Following now
advances to the final snapshot even when the job becomes terminal; an explicitly
pinned selection still stays pinned. The real browser regression asserts that a
completed followed run displays Candidate 4, then tests pinning, resuming,
cancellation and retry. This was corrected in the application, not edited away
in the film.

The historical round23 demonstration was 127.1 seconds, 1600×1000 at 30 fps,
H.264/AAC. It captured 35 actual UI actions and one new 20-event fixed-rule CPU
run at the time of recording. The current round37 film is 151.47 seconds and
reuses recorded evidence; it does not run a fresh model, CPU or GPU job during
playback. The model call is a recorded result, not reenacted inference. No
subjective audio audition was available in this execution environment.
