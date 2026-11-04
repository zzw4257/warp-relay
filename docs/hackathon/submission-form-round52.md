# Verified submission form and prepared copy

Inspected 2026-11-04 after normal participant sign-in. No submission has been sent.

- Team Name: required. Team member shown: Ziwei Zhou / zzw4257.
- Track: required; Indie Developer Track and Startups Track.
- Problem statement: required; Build for Your World and Push the Frontier.
- X post URL: optional; only for Most Viral participation. Leave blank.
- Project Description: required; 3,000-character UI counter.
- Public GitHub Repository: required. A private review repository is not a public judge-accessible destination.
- 3-Minute Demo Video: required.
- Describe your use of Meta products: required; 3,000 characters.
- Why Meta models are important: required; 3,000 characters.
- Partner-technology feedback: optional; 150 characters.
- Future use likelihood and overall Meta API opinion: required personal survey responses; await the user.
- Recommendation scores, biggest obstacle, model comparison, choice/switching/production questions: additional survey controls; no required marker observed.
- Checkbox grants Meta and Cerebral Valley use/publication/sharing/promotion permissions. Left unchecked pending final concrete review.
- Submit button present; no save/edit/resubmission behavior established.

The counts below include spaces and newlines, and are within each displayed limit.

## team_name (10 characters)

Warp Relay

## track (21 characters)

Indie Developer Track

## problem_statement (17 characters)

Push the Frontier

## project_description (2165 characters)

Warp Relay is an investigation workbench for GPU-kernel synchronization edits. It connects a proposed change to the source, assumptions and evidence behind the decision to retain or reject it.

A small edit can look harmless in numerical tests. In our saved B200 validation batch 002, a barrier-deletion candidate passed all 39 cases in the uninstrumented numerical suite. A separate Compute Sanitizer racecheck execution of the same edited PTX reported a shared-memory race and failed its own one-case numerical check. These are distinct executions, not a single launch that both passed and raced.

The workbench follows that evidence back to the code. Users can load PTX and a fixed contract, start bounded CPU analysis, compare candidate diffs, inspect linked accesses, cancel or retry jobs, and export retained source and raw results. A constrained rule provider proposes individual barrier edits; an admission policy and the pinned SentryWard verifier check each proposal under the same contract. Rejected candidates remain inspectable, and unsupported cases remain inconclusive.

Twelve cases provide different investigation paths: eight imported upstream records and four local CPU archives. One real Meta muse-spark-1.3 diagnosis adds a cited hypothesis and source-inspection plan. The workbench exposes its exact input, response, integrity checks and the local inspection that follows it, while keeping the conflicting instruction pair unresolved where the source mapping cannot establish it.

Our contribution is the bounded orchestration, admission controls, workbench, Meta auditing, evidence handling and GPU reference harness. SentryWard is pre-existing Apache-2.0 work, pinned and unmodified; upstream kernel licenses and provenance are retained. A fresh native build passed 73 Python tests, alongside UI and browser checks.

The saved records can be browsed offline with Python and no GPU or model key. New CPU analyses require the native verifier build. Synchronization acceptance is scoped to the supported model and assumptions; finite numerical tests are not a proof. No measured GPU speedup or model-driven repair is claimed.

Built by zzw4257.

## meta_use (1752 characters)

We made one real request to Meta's muse-spark-1.3 through the Meta Model API. The recorded request took 24.525 seconds and used 6,278 input tokens and 3,309 output tokens, with no automatic retry or second model round.

The request carried an immutable verifier packet for a public Tensor Memory Accelerator pipeline: two modeled four-byte writes, actors 0 and 64, overlapping shared offset 49152 with no proven ordering, together with PTX excerpts, source mappings and the fixed contract. The model returned a cited diagnosis and proposed resolving the ambiguous mapping before drawing a stronger conclusion.

We implemented Evidence → Meta → Checks → Inspect as an auditable workflow. The first stage exposes exactly what the model received; the second shows its saved hypothesis and proposed next action. Local checks validate source and request hashes, response identity and typed citations. The Inspect stage carries out the suggested investigation on the actual immutable source: 124 lines across PTX regions 348, 402, 510 and 613, all mapped from Python line 290. Region 402 begins with address arithmetic; the other three begin with stmatrix stores. The exact conflicting instruction pair remains unresolved.

These checks establish record consistency and source grounding, not proof that arbitrary model prose is correct. Both the model and a deterministic diagnostic baseline cite 2/2 accesses and retain 2/2 mapping limitations on this case; no measured model advantage is claimed. The model did not generate a kernel edit. The bounded candidate-edit loop uses fixed rules, and the B200 validation records are separate experiments. The demonstration replays the saved Meta exchange and local inspection rather than simulating live inference.

## meta_importance (1371 characters)

A verifier can report a conflict without answering an engineer's next question: which source operations should I inspect, and what remains ambiguous? That is where Meta's model contributes to Warp Relay.

On the recorded TMA case, muse-spark-1.3 connects the overlapping accesses, instruction classes and nearby synchronization into a focused investigation plan. Warp Relay makes that plan actionable by opening the cited source regions and preserving the evidence and uncertainty behind each step. The reviewer can move from a low-level diagnostic to a concrete inspection without losing the original contract or source identity.

We designed the integration so the model's proposal is testable. It receives an immutable packet, must use typed citations, and cannot change the checker or silently convert uncertainty into acceptance. The product then performs the proposed local inspection and displays what it actually found. This makes the model part of the investigation process while leaving the safety decision grounded in verification evidence.

The current evidence is one visible case, with no held-out accuracy or investigation-time advantage established. It demonstrates a source-grounded diagnosis workflow, not autonomous repair or self-training. The next evaluation would compare usefulness across frozen held-out cases before expanding model-led iteration.
