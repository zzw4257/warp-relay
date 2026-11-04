import {esc,label,terminal,verdictFor} from './model.mjs';
import {renderInspection} from './inspection.mjs';
import {mountCode} from './code-view.mjs';

export const eventNames={preparing:'Freeze inputs',verifying_baseline:'Check original',baseline_verified:'Original result',proposing_candidate:'Propose change',candidate_proposed:'Change saved',verifying_candidate:'Check candidate',candidate_verified:'Candidate result',policy_rejected:'Policy rejected',finished:'Run finished'};
export function observedEvents(data){return (data.job.events||[]).map((e,i)=>({...e,id:i,name:eventNames[e.phase]||e.phase,elapsed:(Date.parse(e.at)-Date.parse(data.job.events[0].at))/1000}));}
export function selectedRound(data,old,follow){return follow?Math.max(0,data.rounds.length-1):Math.min(Math.max(old,0),Math.max(0,data.rounds.length-1));}
const rememberedRuns=new Map();

// Polls real persisted worker snapshots. No fabricated events or paced progress.
export async function mountRunWorkspace(host,navigate,id,initial={}){
 let data,disposed=false,timer,request=null,code=null,codeTicket=0,inspectionKey='',lastCount=0;
 const remembered=rememberedRuns.get(id);
 let state=remembered?{...remembered.state}:{index:initial.index??0,tab:initial.tab||'diff',focus:null,expanded:false},follow=remembered?.follow??true,first=true;
 const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 const $=s=>host.querySelector(s);
 host.className='run-workspace';
 host.innerHTML=`<header class="kernel-topbar"><a href="#library" class="kernel-brand"><img src="/mark.svg" alt="">Warp Relay</a><span class="workspace-name">Analysis</span><nav><button id="run-library">Kernels</button><button id="run-new" class="primary">New analysis</button></nav></header><main class="run-layout"><aside class="run-journal"><div class="journal-heading"><h1>Activity</h1><span id="run-origin"></span></div><div class="worker-state" role="status" aria-live="polite"><span class="worker-indicator"></span><span id="worker-phase">Connecting…</span></div><button id="follow-run" aria-pressed="true">Following latest result</button><ol id="observed-events"></ol><div class="journal-footer"><span>Fixed-rule proposals</span><span>No model call · no GPU run</span><a id="open-pipeline" href="#flow/${encodeURIComponent(id)}">Architecture & saved replay ↗</a></div></aside><section class="run-reader"><header class="run-title"><div><p id="run-identity"></p><h1 id="run-name">Opening analysis</h1></div><div id="run-actions"></div></header><div id="run-connection" role="alert" hidden></div><div id="run-outcome"></div><nav class="mobile-run-panes" aria-label="Analysis panes"><button data-pane="source" aria-pressed="true">Source</button><button data-pane="evidence" aria-pressed="false">Evidence</button></nav><div id="run-inspection" data-mobile-pane="source"><div class="run-wait"><span class="wait-mark">W</span><h2>Waiting for the worker</h2><p>Source and evidence appear here as each check finishes.</p></div></div><footer class="run-boundary">Synchronization under a fixed contract. Numerical equivalence and GPU performance require separate evidence.</footer></section></main>`;
 $('#run-library').onclick=()=>navigate('#library');$('#run-new').onclick=()=>navigate('#new');
 const activityToggle=document.createElement('button');activityToggle.id='toggle-activity';activityToggle.textContent='Show activity';activityToggle.setAttribute('aria-expanded','false');$('.journal-heading').append(activityToggle);
 activityToggle.onclick=()=>{const open=activityToggle.getAttribute('aria-expanded')!=='true';activityToggle.setAttribute('aria-expanded',String(open));activityToggle.textContent=open?'Hide activity':'Show activity';$('.run-journal').dataset.open=String(open);};
 function pane(value){$('#run-inspection').dataset.mobilePane=value;host.querySelectorAll('[data-pane]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.pane===value)));}
 host.querySelectorAll('[data-pane]').forEach(b=>b.onclick=()=>pane(b.dataset.pane));
 $('#follow-run').onclick=()=>{follow=!follow;if(follow&&data)state.index=Math.max(0,data.rounds.length-1);draw();};
 async function action(kind){
  const button=$('#'+kind+'-job');if(button)button.disabled=true;
  try{const response=await fetch(`/api/jobs/${encodeURIComponent(id)}/${kind}`,{method:'POST',headers:{'Content-Type':'application/json','X-Warp-Request':'1'},body:'{}'});const value=await response.json();if(!response.ok)throw Error(value.error||'Action failed');if(disposed)return;if(kind==='retry')navigate('#run/'+value.id);else{data.job={...data.job,...value};draw();}}
  catch(e){if(!disposed){$('#run-connection').hidden=false;$('#run-connection').textContent=`${e.message}. Check the saved state before retrying.`;if(button)button.disabled=false;}}
 }
 function choose(index,keyboard=false){follow=false;state.index=index;state.focus=null;drawInspection(keyboard);drawJournal();$('#observed-events .selected')?.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});}
 function drawJournal(){
  const events=observedEvents(data),list=$('#observed-events');
  if(events.length&&list.querySelector('.event-empty'))list.replaceChildren();
  // Keep existing rows and keyboard focus while new actual events arrive.
  for(const event of events.slice(list.children.length)){
   const li=document.createElement('li');li.dataset.event=event.id;
   li.innerHTML=`<button data-event-index="${event.id}" ${Number.isInteger(event.iteration)?'':'disabled'}><span class="event-tick">${event.accepted===false?'×':event.result?'✓':'·'}</span><span><strong>${esc(event.name)}</strong><small>${Number.isInteger(event.iteration)?esc(label(event.iteration)):'Local worker'}${event.result?' · '+esc(event.result.replaceAll('_',' ')):''}</small></span><time>+${event.elapsed.toFixed(3)}s</time></button>`;
   li.querySelector('button').onclick=e=>{if(event.iteration<data.rounds.length)choose(event.iteration,e.detail===0);};list.append(li);
   if(!first&&!reduced())li.animate([{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:'cubic-bezier(.23,1,.32,1)'});
  }
  list.querySelectorAll('[data-event-index]').forEach(b=>{const e=events[+b.dataset.eventIndex];b.disabled=!Number.isInteger(e.iteration)||e.iteration>=data.rounds.length;b.classList.toggle('selected',e.iteration===state.index&&e.result!==undefined);});
  if(events.length>lastCount&&follow)list.scrollTop=list.scrollHeight;lastCount=events.length;
  $('#follow-run').textContent=follow?'Following latest result':'Follow latest result';$('#follow-run').setAttribute('aria-pressed',String(follow));
 }
 function drawInspection(keyboard=false){
  const rows=data.rounds;if(!rows.length)return;
  const row=rows[state.index],key=[state.index,state.tab,row.kernel_sha256,row.result].join(':');
  if(key===inspectionKey)return;inspectionKey=key;
  const area=$('#run-inspection');code?.cleanUp();code=null;const ticket=++codeTicket;
  area.innerHTML=renderInspection(data,state);
  const bind=()=>{
   area.querySelectorAll('button[data-round]').forEach(b=>b.onclick=e=>choose(+b.dataset.round,e.detail===0));
   area.querySelectorAll('button[data-tab]').forEach(b=>b.onclick=e=>{state.tab=b.dataset.tab;drawInspection(e.detail===0);});
   area.querySelectorAll('button[data-access]').forEach(b=>b.onclick=()=>{state.focus=b.dataset.access;pane('source');if(!['diff','code'].includes(state.tab)){state.tab='code';drawInspection();}else{area.querySelectorAll('.access').forEach(n=>n.classList.toggle('focused',n===b));code?.focus(state.focus);}if(matchMedia('(max-width:850px)').matches)$('#diff-host')?.scrollIntoView({block:'start',behavior:'instant'});});
   area.querySelector('[data-action="focus-evidence"]')?.addEventListener('click',e=>{if(matchMedia('(max-width:850px)').matches){pane($('#run-inspection').dataset.mobilePane==='source'?'evidence':'source');return;}state.expanded=!state.expanded;area.querySelector('.inspection-shell').classList.toggle('evidence-expanded',state.expanded);e.currentTarget.setAttribute('aria-pressed',String(state.expanded));e.currentTarget.textContent=state.expanded?'Return to diff':'Focus evidence';});
  };bind();
  const source=area.querySelector('#diff-host');
  if(source)mountCode(source,data,state).then(instance=>{if(disposed||ticket!==codeTicket){instance.cleanUp();return;}code=instance;if(state.focus)code.focus(state.focus);source.dataset.ready='true';}).catch(()=>{if(source.isConnected)source.textContent='Source viewer unavailable. Download the preserved PTX from the evidence panel.';});
  if(!first&&!keyboard&&!reduced())area.animate([{opacity:.55},{opacity:1}],{duration:150,easing:'ease-out'});
 }
 function draw(){
  if(disposed)return;const job=data.job,active=!terminal.has(job.state);state.index=selectedRound(data,state.index,follow);
  if(first&&job.recorded&&!remembered){follow=false;state.index=Math.min(initial.index??1,Math.max(0,data.rounds.length-1));}
  $('#run-name').textContent=job.name;$('#run-identity').textContent=job.id+(job.retry_of?' · retry of '+job.retry_of:'');
  $('#run-origin').textContent=job.recorded?'Saved evidence':active?'Live CPU':'Completed CPU';host.dataset.state=job.state;
  $('#worker-phase').textContent=job.state==='cancelling'?'Stopping owned worker…':active?(eventNames[job.phase]||job.phase):job.outcome==='inconclusive'?'Finished · inconclusive':job.state.replaceAll('_',' ');
  const actions=active?'<button id="cancel-job">Cancel analysis</button>':job.recorded?'':'<button id="retry-job">Retry as new run</button>';
  if($('#run-actions').innerHTML!==actions){$('#run-actions').innerHTML=actions;$('#cancel-job')?.addEventListener('click',()=>action('cancel'));$('#retry-job')?.addEventListener('click',()=>action('retry'));}
  const retained=data.summary?.selected, outcome=retained?`<span>Retained <strong>${esc(label(data.rounds.findIndex(r=>r.path===retained)))}</strong></span><a href="/api/jobs/${encodeURIComponent(id)}/files/selected.ptx" download>Download PTX ↗</a>`:active?'Waiting for a verified result':'No artifact retained';
  if($('#run-outcome').innerHTML!==outcome)$('#run-outcome').innerHTML=outcome;
  if(job.error){$('#run-connection').hidden=false;$('#run-connection').textContent=job.error;}
  if(!job.events?.length)$('#observed-events').innerHTML='<li class="event-empty">This archive predates phase logging. Its recorded candidate results are available on the right.</li>';
  drawJournal();drawInspection();
  const rail=$('.candidate-strip');
  if(rail){
   const railKey=JSON.stringify([data.rounds.map(r=>[r.path,r.accepted,r.result]),state.index,retained]);
   if(rail.dataset.key!==railKey){rail.dataset.key=railKey;rail.innerHTML=data.rounds.map((r,i)=>`<button class="round ${i===state.index?'active':''}" role="tab" aria-selected="${i===state.index}" data-round="${i}"><span class="round-symbol ${verdictFor(r).status}">${verdictFor(r).symbol}</span>${label(i)}${r.path===retained?'<span class="retained-dot" title="Retained by this run"></span>':''}</button>`).join('');rail.querySelectorAll('button').forEach(b=>b.onclick=e=>choose(+b.dataset.round,e.detail===0));}
   rail.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const n=data.rounds.length;choose(e.key==='Home'?0:e.key==='End'?n-1:(state.index+(e.key==='ArrowRight'?1:-1)+n)%n,true);$('.candidate-strip .active')?.focus();}};
  }
  first=false;
 }
 async function refresh(){
  if(disposed)return;request=new AbortController();
  try{const response=await fetch('/api/jobs/'+encodeURIComponent(id),{signal:request.signal});if(!response.ok)throw Error('Run unavailable');const value=await response.json();if(disposed)return;data=value;$('#run-connection').hidden=true;draw();if(!terminal.has(data.job.state))timer=setTimeout(refresh,150);}
  catch(e){if(disposed||e.name==='AbortError')return;$('#run-connection').hidden=false;$('#run-connection').textContent='Connection interrupted. Existing evidence stays visible; reconnecting…';timer=setTimeout(refresh,1500);}
 }
 await refresh();
 return{cleanUp(){rememberedRuns.set(id,{state:{...state},follow});disposed=true;++codeTicket;request?.abort();clearTimeout(timer);code?.cleanUp();}};
}
