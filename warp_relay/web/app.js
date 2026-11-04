'use strict';
const $ = (selector, root=document) => root.querySelector(selector);
const escapeText = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const terminal = new Set(['completed','inconclusive','failed','cancelled','interrupted']);
let app = {status:null, presets:[], jobs:[], selectedRound:1, mode:'diff', current:null, route:'', fingerprint:'', storyRun:2};
let toastTimer;
async function api(path, body) {
  const options = body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Warp-Request':'1'},body:JSON.stringify(body)};
  const response = await fetch(path,options);
  const data = await response.json();
  if (!response.ok) {const error=new Error(data.error || `Request failed (${response.status})`);error.status=response.status;throw error;}
  return data;
}
function toast(message) { const node=$('#notice'); node.textContent=message;node.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.hidden=true,5500); }
function dialog(title, value) { $('#dialog-title').textContent=title;$('#dialog-content').textContent=typeof value==='string'?value:JSON.stringify(value,null,2);$('#detail-dialog').showModal(); }
function navigate(hash) { $('.sidebar').classList.remove('expanded');$('#workspace-toggle').setAttribute('aria-expanded','false');if(location.hash===hash) route();else location.hash=hash; }
function statusBadge(state) { return `<span class="badge ${escapeText(state)}">${escapeText(state.replaceAll('_',' '))}</span>`; }
function artifact(id,path) { return `/api/jobs/${encodeURIComponent(id)}/files/${path.split('/').map(encodeURIComponent).join('/')}`; }
const exampleNames={'recorded-weightnorm':'WeightNorm · barrier removal','recorded-unsupported':'MultiMarginLoss · support boundary','recorded-repair':'Shared memory · repair'};
function renderNavigation() {
  const current=app.jobs.filter(j=>!j.recorded&&(!terminal.has(j.state)||app.route===`#run/${j.id}`));
  const history=app.jobs.filter(j=>!j.recorded&&!current.includes(j));
  const query=$('#history-search').value.trim().toLowerCase(), filter=$('#history-filter').value;
  const matches=history.filter(j=>`${j.name} ${j.id}`.toLowerCase().includes(query)&&(filter==='all'||(filter==='inconclusive'?j.outcome==='inconclusive':filter==='failed'?['failed','interrupted'].includes(j.state):j.state===filter&&j.outcome!=='inconclusive')));
  $('#current-analyses').hidden=!current.length;$('#history-count').textContent=history.length;
  for(const [selector,rows,empty] of [['#current-list',current,''],['#example-list',app.jobs.filter(j=>j.recorded),''],['#history-list',matches,history.length?'No saved analyses match this filter.':'Your completed analyses will appear here.']]) {
    const html=rows.map(j=>`<button class="run-link ${app.route===`#run/${j.id}`?'active':''}" data-id="${escapeText(j.id)}" title="${escapeText(j.name)}"><span class="label">${escapeText(exampleNames[j.id]||j.name)}</span><small>${escapeText(j.outcome==='inconclusive'?'inconclusive':j.state)}${j.recorded?' · recorded evidence':' · '+escapeText(j.id.slice(0,6))}</small></button>`).join('')||`<p class="history-empty">${empty}</p>`;
    const node=$(selector);if(node.innerHTML!==html){node.innerHTML=html;node.querySelectorAll('button').forEach(b=>b.onclick=()=>navigate(`#run/${b.dataset.id}`));}
  }
}
async function refreshList() {app.jobs=await api('/api/jobs');renderNavigation();}
function describeState(job) {
  if(job.state==='completed'&&job.outcome==='inconclusive')return 'Analysis completed with an inconclusive result. Unsupported is a support boundary, not a pass or an orchestration failure.';
  const messages={queued:'Queued. One local CPU analysis runs at a time.',verifying_baseline:'Analyzing the original PTX with SentryWard…',baseline_verified:'Original analysis returned. Preparing the next step.',proposing_candidate:`Proposing candidate ${job.iteration || ''} with the deterministic rule provider…`,verifying_candidate:`Analyzing candidate ${job.iteration || ''} with the same frozen contract…`,candidate_verified:'Candidate result saved. Evaluating the next step.',cancelling:'Cancellation requested. Stopping this run’s verifier process group…',cancelled:'Cancelled. Existing evidence is retained. Retry creates a new run.',interrupted:'Interrupted by a workbench restart. Nothing was silently resumed.',preparing:'Preparing immutable input snapshots…'};
  return messages[job.state] || messages[job.phase] || 'Analysis finished. Inspect each candidate and its acceptance scope below.';
}
function formValue() {
  return {name:$('#task-name').value,description:$('#specification').value,kernel:$('#kernel').value,input:$('#contract').value,objective:$('#objective').value,iterations:Number($('#iterations').value),timeout:Number($('#timeout').value),memory_mib:Number($('#memory').value)};
}
function fillForm(value) {
  $('#task-name').value=value.name;$('#specification').value=value.description;$('#kernel').value=value.kernel;
  $('#contract').value=typeof value.input==='string'?value.input:JSON.stringify(value.input,null,2);
  $('#objective').value=value.objective;$('#iterations').value=value.iterations;$('#timeout').value=value.timeout;$('#memory').value=value.memory_mib;
  clearValidation();
}
function clearValidation() {
  $('#form-feedback').innerHTML='';
  document.querySelectorAll('[aria-invalid]').forEach(node=>{node.removeAttribute('aria-invalid');node.removeAttribute('aria-describedby');});
}
async function newAnalysis(value) {
  $('#content').innerHTML=`<div class="page-head"><div><h1>Analyze a kernel</h1><p>Supply PTX and an explicit launch contract. Keep every candidate accountable.</p></div><span class="badge">Local CPU · offline rule provider</span></div>
  <div class="preset-bar"><label for="preset">Start from an example</label><select id="preset">${app.presets.map(p=>`<option value="${escapeText(p.id)}">${escapeText(p.label)}</option>`).join('')}</select><button id="load-preset">Load example</button></div>
  <p class="first-run-help"><strong>First run?</strong> Start with an example, review its fixed contract, validate the inputs, then start analysis. You will see the original kernel and any candidate changes, with an explanation of each decision.</p>
  <div id="form-feedback" aria-live="polite"></div><form id="analysis-form" class="panel"><div class="form-top">
  <label class="field">Analysis name<input id="task-name" maxlength="100" required></label><label class="field">Objective<select id="objective"><option value="optimize">Try removing a CTA barrier</option><option value="repair">Repair a shared-memory race</option><option value="inspect">Inspect only</option></select></label>
  <label class="field full">Kernel specification<textarea id="specification" rows="3" maxlength="6000" required></textarea><span class="help">Operation, dimensions, types and assumptions used to interpret this input.</span></label></div>
  <div class="editors"><section class="editor-pane"><div class="pane-heading"><label for="kernel">Kernel PTX</label><button type="button" id="upload-ptx">Choose .ptx file</button><input type="file" id="ptx-file" accept=".ptx,text/plain"></div><textarea id="kernel" spellcheck="false" aria-label="Kernel PTX" required></textarea></section>
  <section class="editor-pane"><div class="pane-heading"><label for="contract">Input contract JSON</label><button type="button" id="upload-json">Choose .json file</button><input type="file" id="json-file" accept=".json,application/json"></div><textarea id="contract" spellcheck="false" aria-label="Input contract JSON" required></textarea></section></div>
  <div class="settings"><label class="field">Candidate limit<input id="iterations" type="number" min="1" max="10" value="4" required></label><label class="field">Time / check (s)<input id="timeout" type="number" min="1" max="30" value="10" required></label><label class="field">Memory (MiB)<select id="memory"><option>512</option><option selected>1024</option><option>2048</option></select></label>
  <div class="submit-actions"><button type="button" id="validate-input">Validate inputs</button><button class="primary" id="start-analysis" ${app.status?.verifier.ready?'':'disabled'}>Start analysis</button></div></div>
  <p class="scope-note"><strong>Acceptance: synchronization only.</strong> Edits are limited to standalone CTA barriers. Numerical equivalence and GPU performance are separate checks. No Python reference, Meta call or GPU execution is started by this workbench.</p></form>
  <p class="screen-only-note">Limits: 256 KB PTX, 64 KB input JSON, up to 64 blocks and 1,024 threads per block. No server paths or arbitrary commands are accepted.</p>`;
  const initial=value || await api('/api/presets/weightnorm');
  if(app.route!=='#new')return;
  fillForm(initial);
  $('#load-preset').onclick=async()=>{try{fillForm(await api('/api/presets/'+$('#preset').value));toast('Example loaded. Review its fixed contract before starting.');}catch(e){toast(e.message);}};
  for(const [button,input,editor,limit] of [['upload-ptx','ptx-file','kernel',256000],['upload-json','json-file','contract',64000]]) {
    $('#'+button).onclick=()=>$('#'+input).click();
    $('#'+input).onchange=async e=>{const file=e.target.files[0];if(!file)return;if(file.size>limit){toast(`File exceeds ${limit} bytes.`);return;}$('#'+editor).value=await file.text();clearValidation();};
  }
  const feedback=(message,good=false,submissionUnknown=false)=>{
    clearValidation();
    const field=/input|json|launch|entry/i.test(message)?'contract':/kernel|ptx/i.test(message)?'kernel':/^name:/.test(message)?'task-name':/^description:/.test(message)?'specification':/^(iterations|timeout|memory_mib):/.test(message)?({iterations:'iterations',timeout:'timeout',memory_mib:'memory'}[message.split(':')[0]]):null;
    $('#form-feedback').innerHTML=`<div id="validation-message" class="${good?'valid-box':'error-box'}" role="${good?'status':'alert'}" tabindex="-1">${escapeText(message)}${good?' Review the contract, then start analysis.':submissionUnknown?' The submission outcome is unknown. Your edits are preserved; check saved analyses before retrying.':' No analysis was started; your edits are preserved.'}${!good&&field?'<br><button type="button" class="link-button" id="fix-input">Go to the field</button>':''}</div>`;
    if(!good){if(field){$('#'+field).setAttribute('aria-invalid','true');$('#'+field).setAttribute('aria-describedby','validation-message');$('#fix-input').onclick=()=>$('#'+field).focus();}$('#validation-message').focus();}
  };
  $('#analysis-form').addEventListener('input',clearValidation);
  $('#validate-input').onclick=async()=>{try{const result=await api('/api/validate',formValue());feedback(result.message,true);}catch(e){feedback(e.message);}};
  $('#analysis-form').onsubmit=async e=>{e.preventDefault();const button=$('#start-analysis');button.disabled=true;try{const result=await api('/api/jobs',formValue());navigate('#run/'+result.id);await refreshList();}catch(error){if(button.isConnected)feedback(error.message,false,error.status===undefined);else toast(error.message);}finally{if(button.isConnected)button.disabled=!app.status?.verifier.ready;}};
  if(!app.status?.verifier.ready) feedback(`${app.status?.verifier.message || 'Verifier unavailable'} ${app.status?.verifier.action || ''}`);
}
let mountedCode=null, mountedLibrary=null, viewGeneration=0;
function renderJob(data) {
  app.current=data;
  mountedCode?.cleanUp();mountedCode=null;
  const generation=++viewGeneration;
  const {job,summary,rounds}=data;
  if(app.selectedRound>=rounds.length)app.selectedRound=Math.max(0,rounds.length-1);
  const isActive=!terminal.has(job.state);
  const controls=job.recorded?'<button id="edit-inputs">Use as new analysis</button>':isActive?'<button id="cancel-job" class="danger">Cancel analysis</button>':'<button id="retry-job">Retry as new run</button><button id="edit-inputs">Use as new analysis</button>';
  const title=job.id==='recorded-weightnorm'?'WeightNorm / barrier inspection':job.name;
  const state={index:app.selectedRound,tab:app.mode==='diff'||app.mode==='code'||app.mode==='scope'?app.mode:'activity',focus:app.focus,expanded:app.expanded};
  $('#content').innerHTML=`<div class="page-head"><div><p class="recorded-label">${job.recorded?(['recorded-repair','recorded-barriers'].includes(job.id)?'Saved CPU evidence / shared-memory microfixture':'Saved evidence / public PyTorch kernel'):'Local CPU execution / offline rule provider'}</p><h1>${escapeText(title)}</h1><p>${escapeText(job.id)}${job.retry_of?' · retry of '+escapeText(job.retry_of):''}</p></div><div class="actions">${statusBadge(job.state)}<button id="open-pipeline">Evidence loop</button>${controls}</div></div>
  <div class="status-line"><span>${isActive?'<span class="spinner" aria-hidden="true"></span>':''}${escapeText(describeState(job))}</span>${summary?.selected?`<a id="download-retained" href="${artifact(job.id,'selected.ptx')}" download="${escapeText(job.id)}-retained.ptx">Download retained PTX ↗</a>`:''}</div>
  ${job.error?`<div class="error-box" role="alert">${escapeText(job.error)}</div>`:''}
  ${isActive?WarpUI.renderRunning(data):''}
  ${rounds.length?WarpUI.renderInspection(data,state):isActive?'':WarpUI.renderRunning(data)}
  <div class="run-foot"><span>${summary?`Stop reason: ${escapeText(summary.stop_reason||'pending')} · ${escapeText(summary.provider)}`:'Input snapshots are prepared before execution.'}</span><span>Meta model not connected</span></div>`;
  $('#open-pipeline')?.addEventListener('click',()=>navigate('#flow/'+job.id));
  $('[data-action="focus-evidence"]')?.addEventListener('click',event=>{app.expanded=!app.expanded;$('.inspection-shell').classList.toggle('evidence-expanded',app.expanded);event.currentTarget.textContent=app.expanded?'Return to diff':'Focus evidence';event.currentTarget.setAttribute('aria-pressed',String(app.expanded));});
  const host=$('#diff-host');
  if(host)WarpUI.mountCode(host,data,state).then(instance=>{if(generation===viewGeneration){mountedCode=instance;if(app.focus)instance.focus(app.focus);}else instance.cleanUp();}).catch(error=>{if(host.isConnected){host.textContent='Code viewer could not load: '+error.message;host.setAttribute('role','alert');}});
  document.querySelectorAll('[data-round]').forEach(button=>button.onclick=()=>{app.selectedRound=Number(button.dataset.round);app.focus=null;renderJob(data);});
  document.querySelectorAll('[data-tab]').forEach(button=>{if(button.tagName==='BUTTON')button.onclick=()=>{app.mode=button.dataset.tab;renderJob(data);};});
  document.querySelectorAll('[data-access]').forEach(button=>{if(button.tagName==='BUTTON')button.onclick=()=>{app.focus=button.dataset.access;if(!['code','diff'].includes(app.mode)){app.mode='diff';renderJob(data);}else{document.querySelectorAll('.access').forEach(b=>b.classList.toggle('focused',b===button));mountedCode?.focus(app.focus);if(matchMedia('(max-width:850px)').matches)$('#diff-host')?.scrollIntoView({block:'start',behavior:'instant'});}};});
  $('.candidate-strip')?.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();app.selectedRound=event.key==='Home'?0:event.key==='End'?rounds.length-1:(app.selectedRound+(event.key==='ArrowRight'?1:-1)+rounds.length)%rounds.length;app.focus=null;renderJob(data);$('.round.active').focus();}});
  $('#cancel-job')?.addEventListener('click',async()=>{try{await api(`/api/jobs/${job.id}/cancel`,{});await loadJob(job.id,true);}catch(e){toast(e.message);}});
  $('#retry-job')?.addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;try{const next=await api(`/api/jobs/${job.id}/retry`,{});app.selectedRound=0;navigate('#run/'+next.id);await refreshList();}catch(e){toast(e.status===undefined?'Retry outcome is unknown. Check saved analyses before submitting again.':e.message);if(button.isConnected)button.disabled=false;}});
  $('#download-retained')?.addEventListener('click',async event=>{
    event.preventDefault();const link=event.currentTarget;
    try{const response=await fetch(link.href);if(!response.ok)throw new Error(`Export failed (${response.status})`);
      const blob=await response.blob(),url=URL.createObjectURL(blob),download=document.createElement('a');
      download.href=url;download.download=link.download;download.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
      toast(`Retained PTX ready · ${blob.size.toLocaleString('en-US')} bytes`);
    }catch(error){toast(error.message);}
  });
  $('#edit-inputs')?.addEventListener('click',()=>{if(!summary||!rounds.length){toast('No completed input snapshot is available yet. Start a new analysis.');return;}app.draft={name:summary.name,description:summary.description,kernel:rounds[0].source,input:data.contract,objective:summary.objective,iterations:4,timeout:10,memory_mib:1024};navigate('#new');});
}
async function loadJob(id,force=false) {
  const data=await api('/api/jobs/'+encodeURIComponent(id));
  if(app.route!==`#run/${id}`)return;
  const fingerprint=JSON.stringify([data.job.updated_at,data.job.state,data.rounds.length,data.summary?.selected]);
  if(force||fingerprint!==app.fingerprint){app.fingerprint=fingerprint;renderJob(data);}
}
async function renderStory() {
  const data=await api('/api/story');if(app.route!=='#story')return;
  const row=data.runs.find(r=>r.number===app.storyRun), negative=row.variants.counterexample;
  const passed=negative.passed===negative.total;
  const root=`/evidence/round4-20261031/gpu-run-${String(row.number).padStart(3,'0')}/gpu-results-${String(row.number).padStart(3,'0')}`;
  $('#content').innerHTML=`<div class="story"><div class="story-head"><p class="recorded-label">Warp Relay / WeightNorm · NVIDIA B200</p><h1>Two recorded validation batches</h1><p>Same edited PTX · separate numerical and racecheck executions</p></div>
  <div class="story-switch" aria-label="Recorded validation batch"><button id="story-one" class="${app.storyRun===1?'active':''}">Batch 001</button><button id="story-two" class="${app.storyRun===2?'active':''}">Batch 002</button></div>
  <div class="story-proof"><section><h2>Numerical suite</h2><div class="big-result ${passed?'pass':'reject'}">${negative.passed} / ${negative.total} passed</div><p>${passed?'39 cases × 3 launches passed in the uninstrumented suite. Racecheck uses a separate execution of the same edited PTX.':`${negative.total-negative.passed} cases failed in the uninstrumented suite. Racecheck uses a separate execution.`}</p><a href="${root}/counterexample-numerical.stdout">Read actual numerical output</a></section>
  <section><h2>Separate racecheck execution</h2><div class="big-result reject">Race detected</div><p>The instrumented execution reports a shared-memory race. Its own one-case numerical check fails: 2050 mismatches.</p><a href="${root}/counterexample-racecheck.log">Read actual racecheck log</a></section></div>
  <div class="verdict-callout"><strong>Decision: reject the candidate.</strong> Passing numerical samples do not override a failed synchronization check.</div>
  <div class="actions"><button id="open-rejection" class="primary">Inspect the rejected change</button><button id="rerun-story">Run the real CPU analysis</button></div>
  <details class="story-section"><summary>Provenance & implementation</summary><div class="workflow"><span>Frozen PTX + contract</span><b>›</b><span>Propose barrier deletion</span><b>›</b><span>Verify candidate</span><b>›</b><span class="reject">Reject + retain original</span></div><p>New work is the orchestration, constrained edit policy, evidence retention and workbench. The public Apache-2.0 SentryWard verifier is the pre-existing foundation. This GPU study uses a deterministic rule provider. The separate Meta diagnosis replays one saved model response; it did not produce this edit.</p></details>
  <details class="story-section"><summary>Accepted candidate timing · no demonstrated speedup</summary><p>A later candidate removes a barrier on a branch that the fixed 256-thread launch does not execute. It passes synchronization and numerical testing. The measured runtime does not demonstrate a speedup.</p><table class="timings"><thead><tr><th>Trial</th><th>Original median</th><th>Accepted median</th><th>Median paired ratio</th></tr></thead><tbody>${data.timings.map((t,i)=>`<tr><td>${i+1}</td><td>${t.baseline_median_us.toFixed(4)} µs</td><td>${t.selected_median_us.toFixed(4)} µs</td><td>${t.paired_ratio_median.toFixed(4)}×</td></tr>`).join('')}</tbody></table><p class="check-description">Three trials of 31 alternating pairs; 100-node CUDA graph replay per sample. One B200, one fixed shape, warm buffers, unlocked clocks. Timing is separate from synchronization and finite numerical tests.</p></details>
  <details class="story-section"><summary>Assumptions & fixed contract</summary><p>The upstream assumptions remain enabled and the static result is <code>assumption_dependent=true</code>. Formal numerical equivalence was not requested. GPU results here are recorded evidence; opening this story does not start a GPU job.</p><p><a href="/evidence/round4-20261031/gpu-run-002/manifest.json">Artifact hashes and fixed contract</a></p></details></div>`;
  $('#story-one').onclick=()=>{app.storyRun=1;renderStory();};$('#story-two').onclick=()=>{app.storyRun=2;renderStory();};
  $('#open-rejection').onclick=()=>{app.selectedRound=1;app.mode='diff';navigate('#run/recorded-weightnorm');};
  $('#rerun-story').onclick=()=>navigate('#new');
}
async function route() {
  const nextRoute=location.hash||'#library';
  const kernelRoute=nextRoute==='#library'||nextRoute.startsWith('#case/');
  document.body.classList.toggle('kernel-mode',kernelRoute||nextRoute.startsWith('#flow')||nextRoute.startsWith('#run/'));
  if(kernelRoute&&mountedLibrary?.setRoute){app.route=nextRoute;await mountedLibrary.setRoute(nextRoute);return;}
  clearTimeout(toastTimer);$('#notice').hidden=true;mountedLibrary?.cleanUp();mountedLibrary=null;mountedCode?.cleanUp();mountedCode=null;++viewGeneration;
  app.route=location.hash||'#library';app.fingerprint='';const generation=viewGeneration;const host=document.createElement('div');
  try {
    if(app.route==='#library'||app.route.startsWith('#case/')){ $('#content').replaceChildren(host);const instance=await WarpUI.mountKernelWorkspace(host,app.route,navigate);if(generation===viewGeneration)mountedLibrary=instance;else instance?.cleanUp();}
    else if(app.route.startsWith('#flow')){$('#content').replaceChildren(host);mountedLibrary=await WarpUI.mountFlow(host,navigate,app.route.split('/')[1]||'recorded-weightnorm');}
    else if(app.route==='#new'){const draft=app.draft;app.draft=null;await newAnalysis(draft);}
    else if(app.route==='#story')await renderStory();
    else if(app.route.startsWith('#run/')){app.current=null;$('#content').replaceChildren(host);const instance=await WarpUI.mountRunWorkspace(host,navigate,app.route.slice(5),{index:app.selectedRound,tab:app.mode});if(generation===viewGeneration)mountedLibrary=instance;else instance?.cleanUp();}
    else navigate('#new');
    if(generation!==viewGeneration)return;
    window.scrollTo({top:0,left:0,behavior:'instant'});
    await refreshList();
  }catch(error){if(generation!==viewGeneration)return;$('#content').innerHTML=`<div class="broken" role="alert"><h1>Unable to open this view</h1><p>${escapeText(error.message)}</p><button id="retry-view">Retry loading</button></div>`;$('#retry-view').onclick=route;}
}
async function poll() {
  try {if(app.route.startsWith('#run/')&&app.current&&!terminal.has(app.current.job.state))await loadJob(app.route.slice(5));await refreshList();$('#connection-text').textContent=app.status?.verifier.ready?'SentryWard ready':'Verifier setup required';$('#ready-dot').classList.toggle('ready',Boolean(app.status?.verifier.ready));}
  catch(error){$('#connection-text').textContent='Connection lost. Your saved evidence remains on disk.';$('#ready-dot').classList.remove('ready');}
  setTimeout(poll,app.current&&!terminal.has(app.current.job.state)?300:1800);
}
async function init() {
  $('#workspace-toggle').onclick=()=>{const open=$('.sidebar').classList.toggle('expanded');$('#workspace-toggle').setAttribute('aria-expanded',String(open));};
  $('#history-search').oninput=renderNavigation;$('#history-filter').onchange=renderNavigation;
  $('#library-nav').onclick=()=>navigate('#library');$('#new-run').onclick=()=>navigate('#new');$('#story-nav').onclick=()=>navigate('#story');
  try {app.status=await api('/api/status');app.presets=await api('/api/presets');$('#connection-text').textContent=app.status.verifier.ready?'SentryWard ready':'Verifier setup required';$('#ready-dot').classList.toggle('ready',app.status.verifier.ready);await route();poll();}
  catch(error){$('#content').innerHTML=`<div class="error-box"><h1>Workbench connection failed</h1><p>${escapeText(error.message)}</p><button id="reload">Reconnect</button></div>`;$('#reload').onclick=()=>location.reload();}
}
window.addEventListener('hashchange',route);if(window.WarpUI)init();else window.addEventListener('warp-ui-ready',init,{once:true});
