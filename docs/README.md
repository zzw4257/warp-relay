# Warp Relay documentation

Start with the [project README](../README.md). This page routes you to the
focused documents in this tree and explains the workbench views.

## Pick a path

| I want to… | Read |
| --- | --- |
| Open the recorded demo and verify the snapshot | [Reproduction](reproduction.md) |
| Build the verifier and run a new CPU analysis | [Reproduction § native verifier](reproduction.md#native-verifier-and-bounded-cpu-runs) |
| Inspect fresh build and test results | [Native validation](native-validation.md) |
| Understand the modules and data flow | [Architecture](architecture.md) |
| Write or review an input contract | [Input contract](input-contract.md) |
| See what the Meta model did, and how it was checked | [First Meta response](first-meta-response.md) · [Evidence investigation](evidence-investigation.md) |
| Check where each case came from | [Case provenance](provenance.md) |
| Read the GPU method and its limits | [GPU validation](gpu-validation.md) |
| Follow the public PyTorch cases | [Public case](public-case.md) · [Supported public case](supported-public-case.md) |
| Know what is (and is not) in this tree | [Release scope and licenses](release-scope.md) |
| Contribute, maintain or cut a new snapshot | [Contributing](../CONTRIBUTING.md) · [Maintaining](maintaining.md) · [Changelog](../CHANGELOG.md) |
| Read the hackathon copy and publication status | [Hackathon records](hackathon/) |

## Use the workbench

Start the server with `python3 -m warp_relay serve --port 8876 --state runs/my-workbench`,
then open `http://127.0.0.1:8876/#library`. Every view below except **New analysis**
reads saved records; New analysis runs a live local CPU job and writes a new record.
Nothing contacts a model or a GPU.

| View | Route | What it does |
| --- | --- | --- |
| **Kernels** | `#library`, `#case/<id>/<version>/<tab>` | Twelve cases. Filter by family, compare cases, switch between Original and Candidate versions, read PTX in **Code**, **Changes** or **Structure** mode |
| **Evidence** tab | inside a case | The conflict witness: two accesses, their actors and PTX lines. Selecting one moves the source view to it |
| **Diagnosis** tab | `…/rules`, `…/meta/<step>` | **Fixed rules** versus **Meta**. For the TMA pipeline case, the recorded response unfolds as Evidence → Meta → Checks → Inspect. **Meta diagnosis** in the header opens it |
| **Scope** tab | inside a case | The fixed launch, assumptions and checks that bound the result |
| **Evidence loop** | `#flow` | Step through a saved CPU run: contract → proposal → edit policy → SentryWard → retain/reject |
| **GPU records** | `#story` | Two B200 validation batches, each with separate numerical and racecheck executions and links to their raw results |
| **New analysis** | `#new` | Load a sample contract and start, cancel or retry a bounded CPU job (needs the native verifier) |

Case IDs: `weightnorm`, `repair`, `barriers`, `multimargin`, `layernorm`,
`maxunpool`, `softmax`, `async-copy`, `tma`, `tcgen`, `online-softmax`, `rmsnorm`.

**Linking to evidence.** Case URLs have the form
`#case/<id>/<version>/<tab>[/<step>[/L<line>]]`: the version is its label in
lowercase (`original`, `candidate-4`, `public-ptx`), the tab is `evidence`,
`rules`, `meta` or `scope`, the Meta step is `evidence`, `response`, `checks` or
`inspect`, and `L<line>` selects a mapped PTX region in the Inspect step. For
example, `#case/weightnorm/candidate-4/scope` opens the retained candidate's
scope and `#case/tma/public-ptx/meta/inspect/L402` opens the address-arithmetic
region. The address bar follows these selections without adding history
entries; source-line focus and the Code/Changes/Structure mode are not part of the URL.
Unknown or out-of-range parts are ignored and the URL is corrected to what is
actually shown; an unknown case ID shows an error with a way back to the
library. A link only selects a view. It never starts a job or changes a record.

**Reading outcomes.** A red dot means a conflict was found; green means the
check passed *within the recorded scope*; amber marks a support boundary or
an inconclusive result. "Retained" means the verifier accepted a candidate under
the fixed contract. It does not mean faster or numerically equivalent code.

## Conventions used across these docs

- **Recorded** means read from a saved file whose hash is in `PUBLIC-MANIFEST.json`.
- **Upstream record** means a saved public SentryWard result, displayed rather than re-executed.
- **Local record** means a CPU run produced by this project.
- Commands run from the source root and write only to a new directory under `runs/`.
