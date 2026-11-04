"""Offline evidence viewer: all displayed values come from saved run files."""
import html
import json
from pathlib import Path


def render_report(directory: Path) -> None:
    summary = json.loads((directory / "summary.json").read_text())
    e = html.escape
    panels = []
    for index, row in enumerate(summary["iterations"]):
        step = directory / row["path"]
        result_file = step / "verification/result.json"
        raw = json.loads(result_file.read_text()) if result_file.exists() else {"reason": row.get("reason")}
        diff = (step / "change.diff").read_text() if (step / "change.diff").exists() else "Original kernel; no change proposed."
        if row["accepted"]:
            status = "Synchronization-only acceptance" if summary["acceptance_scope"] == "synchronization" else "Requested checks passed within scope"
        else:
            status = "Finding; not accepted" if row["result"] in {"potential_race", "not_wellsynced", "invalid_lifecycle"} else "Inconclusive; not accepted"
        witness = raw.get("evidence", {})
        locations = []
        for race in witness.get("races", []):
            for side in ("first", "second"):
                access = race.get(side, {})
                loc = access.get("location", {})
                locations.append(f'{access.get("mode", "access")} at line {loc.get("line", "?")}')
        panels.append(f'''<article id="step-{index}" class="attempt">
          <div class="attempt-top"><span class="round">{index:02d}</span><div>
          <h2>{e(row["kind"].capitalize())}</h2><p class="verdict {"pass" if row["accepted"] else "fail"}">{e(row["result"])} <span>{status}</span></p></div>
          <a class="source-link" href="{e(row["path"])}/kernel.ptx">Kernel PTX</a></div>
          <p>{e(row.get("rationale", "Verify the original kernel before proposing a change."))}</p>
          {f'<p class="witness">Witness: {e(" / ".join(locations))}</p>' if locations else ""}
          <div class="split"><section><h3>Candidate diff</h3><pre>{e(diff)}</pre></section>
          <section><h3>Check results</h3><dl><dt>Synchronization</dt><dd>{e(raw.get("checks", {}).get("synchronization", "not run"))}</dd>
          <dt>Equivalence</dt><dd>{e(raw.get("checks", {}).get("equivalence", "not run"))}</dd></dl>
          <p class="hash">SHA-256 {e(row["kernel_sha256"])}</p>
          {f'<a href="{e(row["path"])}/verification/stdout.json">Raw verifier output</a>' if result_file.exists() else ""}</section></div>
          <details><summary>Diagnostics, witnesses and assumptions</summary><pre>{e(json.dumps({k:v for k,v in raw.items() if k != "internal"}, indent=2))}</pre></details>
          </article>''')
    selected = summary["selected"] or "No accepted candidate"
    nav = "".join(f'<a href="#step-{i}">{i:02d} {e(r["result"])}</a>' for i, r in enumerate(summary["iterations"]))
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Warp Relay — verification record</title><style>
      :root{color-scheme:light;--paper:#f7f9fc;--ink:#172c42;--blue:#245da5;--line:#c9d7e6;--green:#23624a;--red:#a53d34}
      *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:"Avenir Next",Avenir,"Segoe UI",sans-serif;font-size:16px;line-height:1.6}
      header{padding:24px 5vw;background:white;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:20px;align-items:center}.brand{font-weight:750;font-size:23px;letter-spacing:-1px}.brand svg{vertical-align:middle;margin-right:12px}a{color:var(--blue);text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid var(--blue);outline-offset:5px}
      main{max-width:1280px;margin:auto;padding:44px 5vw 80px}.intro{max-width:850px}h1{font-size:clamp(32px,4.3vw,54px);font-weight:650;line-height:1.13;letter-spacing:-2px;margin:12px 0 22px}h2{font-size:23px;margin:0}h3{font-size:15px;margin:0 0 12px;font-weight:650}p{max-width:80ch}small,.muted{color:#52677c}
      .scope{margin:28px 0 36px;border-left:4px solid var(--blue);padding:12px 20px;background:#eaf0f8;max-width:960px}.scope p{margin:4px 0}.workspace{display:grid;grid-template-columns:205px minmax(0,1fr);gap:36px}nav{align-self:start;position:sticky;top:20px}nav a{display:block;margin:0 0 15px;font-size:14px}nav p{font-weight:650}article{background:white;padding:28px;margin-bottom:24px;border:1px solid var(--line);border-radius:10px}.attempt-top{display:flex;gap:16px;align-items:center}.round{font-size:36px;color:#849bb2;line-height:1}.source-link{margin-left:auto;font-size:13px;white-space:nowrap}.verdict{font-weight:700;margin:2px 0}.verdict span{font-size:12px;font-weight:500;display:block}.pass{color:var(--green)}.fail{color:var(--red)}.split{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:22px}.split section{min-width:0}.witness{color:var(--red);font-size:14px}pre{font:12px/1.7 "SFMono-Regular",Consolas,monospace;overflow:auto;max-height:460px;background:#f1f5fa;padding:18px;border-radius:6px;tab-size:4}dl{margin:0}dt{color:#52677c;font-size:13px}dd{margin:0 0 12px;font-weight:600}.hash{font-size:11px;overflow-wrap:anywhere;color:#52677c}details{border-top:1px solid var(--line);margin-top:24px;padding-top:16px}summary{cursor:pointer;font-size:14px}footer{padding-top:24px;color:#52677c;font-size:13px}.run-mode{font-size:13px;text-align:right}.selection{font-weight:600}
      @media(max-width:800px){.workspace{grid-template-columns:1fr;gap:12px}nav{position:static;display:flex;flex-wrap:wrap;gap:12px}nav p{width:100%;margin:0}nav a{margin:0}.split{grid-template-columns:1fr}article{padding:20px}.attempt-top{flex-wrap:wrap}.source-link{margin-left:0}.run-mode{max-width:180px}main{padding-top:25px}h1{letter-spacing:-1px}}
      </style></head><body>'''
    page += f'''<header><div class="brand"><svg width="35" height="32" viewBox="0 0 35 32" aria-hidden="true"><path d="M2 7h12l7 18h12M2 25h12L21 7h12" fill="none" stroke="#245da5" stroke-width="3"/><circle cx="17.5" cy="16" r="4" fill="#245da5"/></svg>Warp Relay</div>
      <div class="run-mode">{e(summary["provider"])}<br><span class="muted">Recorded local verification</span></div></header><main>
      <div class="intro"><h1>{e(summary["name"])}</h1><p>{e(summary["description"])}</p></div>
      <div class="scope"><p class="selection">Selected: {e(selected)}</p><p>Acceptance scope: {e(summary["acceptance_scope"].replace("_", " "))}. Model call: {e(summary.get("model_status", "not_called").replace("_", " "))}. GPU execution: not performed. Speedup: not measured.</p><p>A synchronization-only pass establishes neither numerical equivalence nor whole-program correctness. Inconclusive results establish no pass.</p><p>Stop reason: {e(summary["stop_reason"])}</p>{f'<p>{e(summary["error"])}</p>' if summary.get("error") else ""}</div>
      <div class="workspace"><nav aria-label="Verification rounds"><p>Verification rounds</p>{nav}<a href="summary.json">Run manifest</a><a href="provenance.json">Provenance</a></nav><div>{"".join(panels)}</div></div>
      <footer>Static analysis only. Results apply to the saved launch, input contracts and verifier assumptions. SentryWard does not model the full PTX memory model; reference equivalence, when requested, uses real arithmetic. Verifier wall time is not GPU kernel latency.<br>Public SentryWard commit {e(summary["verifier"]["revision"])}. <a href="https://github.com/gpu-verifier/sentryward">Upstream source</a>.</footer></main></body></html>'''
    (directory / "report.html").write_text(page)
