import {esc} from './case-model.mjs';
const names={inspect_source:'Inspect source',inspect_debug_regions:'Resolve the source mapping',inspect_contract:'Inspect the input contract',inspect_lifecycle:'Inspect lifecycle ordering',reverify_existing_scope:'Reverify the same scope',run_numerical_reference:'Run numerical reference checks',run_racecheck:'Run hardware racecheck',benchmark_after_correctness:'Benchmark after correctness checks'};
export async function mountDiagnosis(host,caseId,version,onLocate,{provider:wantedProvider=null,stage:wantedStage=null,line:wantedLine=null,onState=()=>{}}={}){
 const ticket=Symbol('review');host._reviewTicket=ticket;
 host.innerHTML='<p class="fine">Opening the evidence review…</p>';
 const response=await fetch(`/api/reviews/${encodeURIComponent(caseId)}/${version}`);if(!response.ok)throw Error('Diagnostic review is unavailable');const record=await response.json();if(!host.isConnected||host._reviewTicket!==ticket)return;
 const facts=new Map(record.packet.facts.map(f=>[f.id,f]));let provider=['model','baseline'].includes(wantedProvider)?wantedProvider:record.model.status==='received_validated'?'model':'baseline',flowStage=['packet','response','checks','source'].includes(wantedStage)?wantedStage:'packet',inspected=null;
 // Only the visible selection is reported (for the address bar); nothing is saved.
 const report=()=>onState({provider,stage:provider==='model'&&record.audit?flowStage:null,line:inspected});
 function draw(){
  const entry=record[provider],d=entry.diagnosis,m=entry.evaluation;
  host.innerHTML=`<div class="review-switch"><button data-review-provider="baseline" class="${provider==='baseline'?'active':''}">Fixed rules</button><button data-review-provider="model" class="${provider==='model'?'active':''}">Meta ${record.model.status==='received_validated'?'':'· not run'}</button></div>${d?`<h2>${esc(d.summary)}</h2><p class="fine">${provider==='baseline'?'Deterministic diagnostic baseline. No model inference.':'Recorded Meta response. Its claims remain hypotheses.'}</p><div class="review-metrics"><span><strong>${m.access_coverage.matched}/${m.access_coverage.total}</strong>Accesses cited</span><span><strong>${m.mapping_ambiguity.acknowledged}/${m.mapping_ambiguity.total}</strong>Mapping limits noted</span></div><h3>Evidence locations</h3>${d.findings.map(f=>`<div class="review-finding"><p>${esc(f.claim)}</p><div class="review-citations">${f.locations.map(l=>`<button data-review-fact="${esc(l.evidence_id)}" data-review-line="${l.ptx_line}">${l.kind==='debug_region'?'Region':'PTX'} ${l.ptx_line}</button>`).join('')}${!f.locations.length?f.citations.map(id=>`<span class="fine">${esc(id)}</span>`).join(''):''}</div></div>`).join('')||'<p class="fine">No conflicting accesses are recorded for this version.</p>'}<h3>Next inspections</h3>${d.next_steps.map((s,i)=>`<div class="review-step"><span>${i+1}</span><p><strong>${esc(names[s.action]||s.action)}</strong><br>${esc(s.reason)}</p></div>`).join('')}<details><summary>Uncertainties & boundaries (${d.uncertainties.length})</summary>${d.uncertainties.map(u=>`<p>${esc(u.detail)}</p>`).join('')}</details><p class="review-boundary">Citation checks validate references, not the truth of every explanation. No verifier verdict or source is changed.</p>`:`<div class="review-empty"><h2>No Meta result yet</h2><p>${esc(entry.reason)}</p><p>The same evidence packet and rubric are ready. Fixed-rule output remains separately labeled.</p><p class="fine">A model comparison appears only after a real response and request receipt are saved and its citations validated.</p></div>`}<details><summary>Record identity</summary><p class="fine">${esc(record.packet.provenance)}<br>${esc(record.packet.version_label)}<br>Source SHA-256: ${esc(record.packet.source_sha256)}</p></details>`;
  host.querySelectorAll('[data-review-provider]').forEach(b=>b.onclick=()=>{provider=b.dataset.reviewProvider;inspected=null;draw();report();});
  if(provider==='model'&&record.model.status==='received_validated'){
   const receipt=document.createElement('div');receipt.className='review-receipt';receipt.innerHTML=`<span class="receipt-dot"></span><strong>${esc(record.model.model)}</strong><span>1 recorded call · ${Number(record.receipt.elapsed_seconds).toFixed(3)}s</span>`;
   host.querySelector('.review-switch').after(receipt);
  }
  if(provider==='model'&&record.audit){
   const audit=record.audit,flow=document.createElement('section');flow.className='review-evidence-flow';flow.setAttribute('aria-label','Recorded model evidence path');
   flow.innerHTML=`<nav aria-label="Model evidence stages">${[['packet','Evidence'],['response','Meta'],['checks','Checks'],['source','Inspect']].map(([key,text],i)=>`<button data-model-stage="${key}" aria-pressed="${flowStage===key}"><span>${i+1}</span>${text}</button>${i<3?'<i aria-hidden="true">›</i>':''}`).join('')}</nav><div class="model-stage-detail"></div>`;
   receiptAfter().after(flow);
   function receiptAfter(){return host.querySelector('.review-receipt');}
   function stage(key,animate=false){
    flowStage=key;inspected=null;flow.querySelectorAll('[data-model-stage]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.modelStage===key)));
    const detail=flow.querySelector('.model-stage-detail');
    const regions=audit.follow_up.regions;
    // Round 37: every stage shows the saved record itself — what was sent, the saved next step, and what the
    // local follow-up found — so the question is visible before and during inspection. Nothing new is inferred.
    const accesses=record.packet.facts.filter(f=>f.kind==='access'),rel=record.packet.facts.find(f=>f.kind==='relationship'),diag=record.packet.facts.find(f=>f.kind==='diagnostic');
    const loc=a=>{const l=a.value.location;return l?`${l.file.split('/').pop()}:${l.line}`:'';};
    const step=(d.next_steps||[])[0],stepName=step?esc(names[step.action]||step.action):'';
    const sources=[...new Set(accesses.map(loc).filter(Boolean))];
    const found=(audit.supported_observations||[]).filter(o=>/\bL\d+\b|wait_group|bar\.sync/.test(o));
    const texts={packet:'Job: explain this recorded conflict only as far as the evidence supports it, and propose the smallest useful next inspection.',response:`One saved response. ${record.receipt.usage.total_tokens.toLocaleString('en-US')} tokens; no second model round.`,checks:'Source hashes and citations match. These checks do not prove the explanation correct.',source:'Four mapped regions. The exact conflicting instruction remains unresolved.'};
    // The saved finding that cites the most distinct PTX locations, shown verbatim as the response's own hypothesis.
    const fs=d.findings||[],distinct=f=>new Set((f.locations||[]).map(l=>l.ptx_line)).size,lead=fs.length?fs.reduce((a,b)=>distinct(b)>distinct(a)?b:a):null;
    const leadHtml=lead?`<div class="stage-finding"><small>Saved hypothesis · finding ${fs.indexOf(lead)+1} of ${fs.length} · cites ${lead.locations.map(l=>`${l.kind==='debug_region'?'Region':'PTX'} ${l.ptx_line}`).join(', ')}</small><p>${esc(lead.claim)}</p></div>`:'';
    const nextStep=(label)=>step?`<div class="stage-next"><small>${label}</small><strong>${stepName}</strong><p>${esc(step.reason)}</p></div>`:'';
    const packetRows=`<dl class="stage-packet">${accesses.length?`<div><dt>${accesses.length} recorded ${accesses.every(a=>a.value.mode==='write')?'writes':'accesses'}</dt><dd>${accesses.map(a=>`actor ${esc(String(a.value.actor))}`).join(' · ')} · ${esc(sources.join(', '))}</dd></div>`:''}${rel?`<div><dt>Same ${esc(String(rel.value.region.bytes))} bytes</dt><dd>${esc(rel.value.region.address_space)} offset ${esc(String(rel.value.region.offset))} · ${esc(diag?diag.value.message.toLowerCase():'')}</dd></div>`:''}<div><dt>Public PTX excerpts · fixed contract</dt><dd>${record.packet.facts.length} immutable facts</dd></div></dl>`;
    detail.innerHTML=key==='packet'?`<p class="stage-job">${esc(texts.packet)}</p>${packetRows}<code class="response-identity">${esc(record.packet.source_sha256.slice(0,24))}…</code>`
     :key==='response'?`<p>${esc(texts.response)}</p>${leadHtml}${nextStep('Proposed next inspection')}<code class="response-identity">${esc(record.receipt.response_id)}</code>`
     :key==='source'?`${nextStep('Next inspection · from the saved response')}<p class="stage-map"><strong>${esc(sources.join(', '))}</strong> → ${regions.length} mapped PTX regions</p><div class="model-region-list">${regions.map(n=>{const f=audit.follow_up.context.find(c=>c.mapping.lines.includes(n)),line=f.value.lines.find(l=>l.line===n).text.trim();return `<button data-acquired-line="${n}"><strong>L${n}</strong><code>${esc(line.split(/\s+/)[0])}</code><span>↗</span></button>`;}).join('')}</div>${found.length?`<div class="stage-found"><small>Local inspection</small>${found.map(o=>`<p>${esc(o)}</p>`).join('')}</div>`:''}<p class="stage-open">${esc(texts.source.replace(/^Four mapped regions\. /,''))}</p><small>${audit.follow_up.source_lines} real source lines inspected locally · 0 additional API calls</small>`
     :`<p>${esc(texts[key])}</p><p class="fine">Fixed rules and Meta both cite 2/2 accesses and acknowledge 2/2 ambiguous mappings. No measured win is claimed.</p>`;
    detail.querySelectorAll('[data-acquired-line]').forEach(b=>b.onclick=e=>{const n=Number(b.dataset.acquiredLine),f=[...facts.values()].find(f=>f.kind==='access'&&f.mapping.lines.includes(n));if(f){onLocate(f,n,{restore:e.detail===-1});inspected=n;detail.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));report();}});
    if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches)detail.animate([{opacity:.6,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}],{duration:160,easing:'cubic-bezier(.23,1,.32,1)'});
   }
   flow.querySelectorAll('[data-model-stage]').forEach(b=>b.onclick=e=>{stage(b.dataset.modelStage,e.detail!==0);report();});stage(flowStage);
   // A linked PTX region is restored exactly once; an unknown line is ignored rather than approximated.
   const linked=flowStage==='source'&&wantedLine!=null&&flow.querySelector(`[data-acquired-line="${Number(wantedLine)}"]`);wantedLine=null;
   if(linked)linked.dispatchEvent(new MouseEvent('click',{detail:-1}));
   const note=document.createElement('details');note.className='model-audit';note.innerHTML=`<summary>What this response adds</summary><p>${esc(audit.comparison.added_context)}</p><p>${esc(audit.comparison.limitation)}</p><p>${audit.remaining.map(esc).join(' ')}</p>`;flow.after(note);
  }
  if(provider==='model'&&!d){
   const setup=document.createElement('details');setup.className='local-model-setup';
   setup.innerHTML=`<summary>Run one Meta review locally</summary><p>In this project's terminal:</p><code>python3 scripts/meta_review_local.py --case ${esc(caseId)} --version ${Number(version)}</code><p>The command asks for your enabled model, confirms one request using existing credits, then accepts a hidden key. It does not save credentials. A completed, validated record can be imported into this view.</p>`;
   host.querySelector('.review-empty').append(setup);
  }
  host.querySelectorAll('[data-review-fact]').forEach(b=>b.onclick=()=>{const f=facts.get(b.dataset.reviewFact),line=Number(b.dataset.reviewLine);if(f?.mapping?.lines.includes(line))onLocate(f,line);});
 }
 draw();report();
}
