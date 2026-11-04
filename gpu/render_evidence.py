"""Render the actual two B200 runs without replacing their immutable records."""
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def render(root):
    locations={n:root/f'gpu-run-{n:03d}'/f'gpu-results-{n:03d}' for n in (1,2)}
    summaries={n:json.loads((p/'summary.json').read_text()) for n,p in locations.items()}
    metrics={}
    for n,path in locations.items():
        for name in ('baseline','selected','counterexample'):
            rows=[json.loads(line) for line in (path/f'{name}-numerical.stdout').read_text().splitlines()]
            cases=[r for r in rows if r.get('kind')=='case']
            metrics[n,name]={'cases':len(cases),'failed':sum(not c['passed'] for c in cases),
                             'max_ulp':max(c['max_output_bf16_ulp'] for c in cases),
                             'max_norm_relative':max(c['max_norm_relative_error'] for c in cases)}
    manifest=json.loads((root/'gpu-run-002/manifest.json').read_text())
    e=html.escape
    rows=''
    for name,label in [('baseline','Public baseline'),('selected','Accepted deletion'),('counterexample','Rejected deletion')]:
        m1,m2=metrics[1,name],metrics[2,name]
        status=manifest['variants'][name]['synchronization_result']
        race='Hazard detected' if name=='counterexample' else '0 hazards'
        rows+=f'<tr><th>{label}</th><td>{e(status)}</td><td>{m1["cases"]-m1["failed"]}/{m1["cases"]}</td><td>{m2["cases"]-m2["failed"]}/{m2["cases"]}</td><td>{race}</td></tr>'
    timings=''.join(f'<tr><th>{i+1}</th><td>{r["baseline_median_us"]:.4f}</td><td>{r["selected_median_us"]:.4f}</td><td>{r["paired_ratio_median"]:.4f}×</td></tr>' for i,r in enumerate(summaries[2]['benchmark']))
    links=''
    for n,path in locations.items():
        rel=path.relative_to(root).as_posix()
        links+=f'<details><summary>GPU run {n}: raw records</summary><ul><li><a href="{rel}/summary.json">Original run summary</a></li>'
        for name in ('baseline','selected','counterexample'):
            for suffix in ('numerical.stdout','memcheck.log','racecheck.log'):
                links+=f'<li><a href="{rel}/{name}-{suffix}">{name}: {suffix}</a></li>'
        links+='</ul></details>'
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Warp Relay — measured on B200</title><style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f7f9fc;color:#172c42;font:16px/1.65 "Avenir Next","Segoe UI",sans-serif}}header{{padding:22px 6vw;background:#fff;border-bottom:1px solid #c9d7e6;display:flex;justify-content:space-between}}main{{max-width:1120px;margin:auto;padding:50px 6vw 80px}}h1{{font-size:clamp(34px,5vw,58px);line-height:1.1;letter-spacing:-2px;margin:12px 0 24px}}h2{{font-size:25px;margin:0 0 16px}}p{{max-width:82ch}}.eyebrow{{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#52677c}}.card{{background:#fff;border:1px solid #c9d7e6;border-radius:10px;padding:28px;margin:26px 0}}.scope{{background:#eaf0f8;border-left:4px solid #245da5;padding:16px 24px}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;padding:13px 12px;border-bottom:1px solid #dce5ef;white-space:nowrap}}thead{{color:#52677c}}.bad{{color:#a53d34}}a{{color:#245da5;text-underline-offset:4px}}details{{padding:14px 0;border-top:1px solid #c9d7e6}}summary{{cursor:pointer}}code{{font-size:13px;overflow-wrap:anywhere}}small{{color:#52677c}}@media(max-width:600px){{main{{padding:28px 5vw}}.card{{padding:18px}}header{{font-size:13px}}}}
</style></head><body><header><strong>Warp Relay</strong><span>Recorded B200 execution · 31 Oct 2026</span></header><main>
<p class="eyebrow">Public PyTorch WeightNorm / unchanged sm_100a PTX</p><h1>Real execution.<br>Separate evidence.</h1>
<p>The public baseline and the accepted barrier deletion passed numerical testing on B200. The rejected deletion exposed a real race. The measured candidate offers no demonstrated speedup.</p>
<div class="scope"><strong>Three different questions</strong><p>SentryWard checks synchronization under the fixed contract. CPU-reference comparisons test sampled numerical outputs. CUDA-event measurements report execution time. None substitutes for the others.</p></div>
<section class="card"><h2>Correctness and the negative control</h2><div class="table-wrap"><table><thead><tr><th>Variant</th><th>Static synchronization</th><th>Numerical run 1</th><th>Numerical run 2</th><th>Racecheck, both runs</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Each numerical run uses 39 cases, repeated three times. Positive variants matched every BF16 reference output exactly in these samples; maximum relative norm error was {metrics[2,'baseline']['max_norm_relative']:.3g}. The predeclared limits were 1 BF16 ULP, and float norm tolerance 2e−6 relative + 1e−7 absolute.</p>
<p class="bad">The rejected candidate failed {metrics[1,'counterexample']['failed']} cases in run 1 but passed the numerical samples in run 2. Racecheck found a shared-memory hazard in both runs. Passing samples do not establish race freedom.</p>
<p>All three variants had zero memcheck findings in the instrumented smoke case. This does not approve the rejected variant.</p></section>
<section class="card"><h2>Measured latency, no demonstrated gain</h2><div class="table-wrap"><table><thead><tr><th>Trial</th><th>Baseline median, µs</th><th>Selected median, µs</th><th>Median paired ratio</th></tr></thead><tbody>{timings}</tbody></table></div>
<p>31 alternating pairs per trial, three trials; each sample replays a 100-node CUDA graph. Numbers are event time per kernel, including graph replay overhead, with hot buffers. They exclude CPU reference work, compilation, transfers and sanitizer overhead.</p>
<p>The selected change removes the barrier at original PTX line 167, on a branch skipped by the fixed 256-thread launch. Static barrier count drops from 16 to 15; executed work is not reduced. One shape and one B200 were benchmarked; clocks were not locked on this shared server.</p></section>
<section class="card"><h2>Inspect the evidence</h2><p><a href="weightnorm-cpu/report.html">Full candidate loop and static diagnostics</a> · <a href="gpu-run-002/manifest.json">Hashes and frozen GPU contract</a> · <a href="server-inventory.json">Sanitized server inventory</a> · <a href="tests.log">38-test log</a></p>{links}
<p><a href="../../docs/gpu-validation.md">Source mapping, method, commands and limits</a></p></section>
<small>Run 1's raw summary preserves an adapter bug: the parser looked for memcheck's footer in racecheck output and blocked timing. Raw racecheck logs already showed zero hazards for both positive variants. The parser was corrected and regression-tested before run 2. Both records are retained.<br>No model call was made. Formal numerical equivalence was not requested. Optional upstream assumptions remain unchanged.</small>
</main></body></html>'''
    (root/'runtime-report.html').write_text(page)
    return metrics

if __name__=='__main__':
    render(ROOT/'evidence/round4-20261031')
