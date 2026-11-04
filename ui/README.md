# Shared workbench UI

The Python server serves the checked-in browser bundle. Opening the workbench
requires no npm install and makes no CDN, font, model or media requests.

To edit and rebuild:

```sh
npm ci --prefix ui --ignore-scripts
npm run build --prefix ui
npm test --prefix ui
```

`src/inspection.mjs` renders the real candidate, witness, activity and contract
views. `src/model.mjs` owns verdict presentation and evidence coordinates.
`src/code-view.mjs` mounts vanilla Pierre File/FileDiff with persistent annotations.
`src/workbench.css` supplies the base layout. The build appends
`src/workbench-light.css` and `src/kernel-workspace.css` to produce the current product stylesheet.
Historical video compositions retain their original styling. The vanilla application remains in
`warp_relay/web/app.js`. The browser output is bundled ESM; no framework migration.

Pierre Diffs is pinned to 1.6.2. Its packaged Shiki catalog has 346 languages and
no PTX entry. A deliberately small custom PTX grammar and original `warp-light`
theme add restrained lexical colors only;
this is not PTX parsing, semantic analysis or a CUDA-source mapping. Unrecognized
syntax remains literal. The two-column unified gutter uses Pierre's original
and candidate coordinates (`data-alt-line` / `data-line`) and retains the
component's interaction metadata. Recheck this adapter before upgrading Pierre.

A focused evidence view expands the context panel and address scope while the
same code nodes and both witness annotations remain mounted. The app uses a
short CSS transition (disabled for reduced motion); the movie drives those
same dimensions and expansion progress explicitly from its frame number.

The immutable demo record is regenerated with:

```sh
python3 scripts/export_demo_record.py
```

It contains only the public WeightNorm case and its recorded static verification.
No live-run result, private path, model activity or hardware timing is synthesized.

## Continuous investigation surface

`kernel-workspace.mjs` owns the persistent navigator, current case and comparison
mode. `case-library.mjs` owns the actual selected version, code/diff and linked
witness; `diagnosis-view.mjs` reads immutable review records and navigates cited
locations. `flow-view.mjs` replays actual candidate decisions in an interactive
architecture. Its animation speed is editorial, not execution telemetry.

The diagram does not fabricate a Meta path: absent responses are visibly pending.
No browser action accepts credentials or makes an inference request. The Python
CLI adapter/controller and explicit validated import are documented in
`../docs/evidence-investigation.md`. A request-generation ticket prevents delayed
case/review responses from replacing the latest selection. The browser regression
also delays a real case response to exercise overlapping navigation, verifies
source focus at zoom, and checks the 390px Evidence/Source return path.
