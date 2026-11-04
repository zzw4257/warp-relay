export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const label = index => index ? `Candidate ${index}` : 'Original kernel';
export const terminal = new Set(['completed','inconclusive','failed','cancelled','interrupted']);
export const rejected = new Set(['potential_race','not_wellsynced','invalid_lifecycle','policy_rejected']);
export function verdictFor(row){const status=row.accepted?'accepted':rejected.has(row.result)?'rejected':'inconclusive';return {status,symbol:status==='accepted'?'✓':status==='rejected'?'×':'?',verdict:status==='accepted'?'Accepted within scope':status==='rejected'?'Rejected':'Inconclusive'};}
export function candidateModel(data, index=0) {
  const row=data.rounds[index];
  if (!row) return null;
  const raw=row.verification;
  const race=raw?.evidence?.races?.[0];
  const accesses=race ? ['first','second'].map((key,i)=>({...race[key],key,tag:i?'B':'A',line:race[key].location?.line})) : [];
  return {row,raw,race,accesses,index,name:label(index),...verdictFor(row),
    retained:data.rounds.findIndex(r=>r.path===data.summary?.selected),original:data.rounds[0],
    range:race?.region?.offset!==undefined?`${race.region.offset}–${race.region.offset+race.region.bytes-1}`:null};
}
export function annotations(model, diff) {
  return model.accesses.filter(a=>Number.isInteger(a.line)&&a.line>0).map(a=>({lineNumber:a.line,...(diff?{side:'additions'}:{}),metadata:{id:a.key,tag:a.tag,mode:a.mode,actor:a.actor,line:a.line,range:model.range}}));
}
// Only describe a barrier deletion when the exact original/candidate bytes
// differ by that single instruction. Do not infer a removal from a verdict.
export function barrierAnnotations(model, diff) {
  if(!diff)return [];
  const old=model.original.source.split('\n'),next=model.row.source.split('\n');
  if(old.length!==next.length+1)return [];
  let at=0;while(at<next.length&&old[at]===next[at])at++;
  if(!/^\s*bar\.sync\s+\d+\s*;\s*$/.test(old[at]??''))return [];
  if(old.slice(at+1).join('\n')!==next.slice(at).join('\n'))return [];
  return [{lineNumber:at+1,side:'deletions',metadata:{kind:'removed-barrier',line:at+1}}];
}
export const phases={queued:['Queued','Waiting for the local verification worker.'],preparing:['Prepare inputs','Freeze the PTX and launch contract.'],verifying_baseline:['Check original','Run SentryWard against the original PTX.'],proposing_candidate:['Propose an edit','The offline rule provider proposes a constrained barrier edit.'],verifying_candidate:['Check candidate','Re-run SentryWard against the edited PTX.'],baseline_verified:['Original checked','The original synchronization result is preserved.'],candidate_verified:['Candidate checked','The candidate decision and verifier evidence are preserved.'],finished:['Finished','Results and artifacts are retained.'],cancelling:['Cancelling','Waiting for the verifier process to stop.'],cancelled:['Cancelled','The cancellation is retained; retry creates a separate run.'],failed:['Failed','Inspect the preserved error before retrying.'],interrupted:['Interrupted','The previous worker ended before completion.']};
