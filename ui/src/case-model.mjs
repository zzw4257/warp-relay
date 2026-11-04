export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function outcome(result){return ['potential_race','not_wellsynced','invalid_lifecycle'].includes(result)?{label:'Conflict',tone:'conflict'}:['verified','race_free'].includes(result)?{label:'Passed in scope',tone:'scoped'}:{label:'Inconclusive',tone:'unknown'};}
export function structure(source){const groups={Synchronization:[],Memory:[],Control:[],Async:[]};let debug=false;source.split('\n').forEach((text,i)=>{const code=text.replace(/\/\/.*$/,'').trim();if(/^\.section\s+\.debug/.test(code))debug=true;if(!code||debug)return;const kind=/\b(?:mbarrier|cp\.async|tcgen05|tma)\b/.test(code)?'Async':/\b(?:bar\.sync|barrier\.|fence\.)/.test(code)?'Synchronization':/\b(?:ld|st|atom|red)\.(?:volatile\.)?(?:shared|global|local)/.test(code)?'Memory':/\b(?:bra|ret)\b|^[\w$]+:$/.test(code)?'Control':null;if(kind)groups[kind].push({line:i+1,text:code});});return groups;}
export function sourceLocations(source,location){
 const lines=source.split('\n');if(!location||!Number.isInteger(location.line))return {kind:'unmapped',lines:[],label:'No source location recorded'};
 const file=location.file||'';const leaf=file.split('/').pop();
 if(file.endsWith('.ptx')&&location.line>0&&location.line<=lines.length)return {kind:'ptx',lines:[location.line],label:`PTX L${location.line}`};
 const ids=new Set();for(const text of lines){const m=text.match(/^\s*\.file\s+(\d+)\s+"([^"]+)"/);if(m&&m[2].split('/').pop()===leaf)ids.add(m[1]);}
 const matches=[];lines.forEach((text,i)=>{const m=text.match(/^\s*\.loc\s+(\d+)\s+(\d+)\b/);if(m&&ids.has(m[1])&&Number(m[2])===location.line){let j=i+1;while(j<lines.length&&(!lines[j].trim()||lines[j].trim().startsWith('.loc')))j++;if(j<lines.length)matches.push(j+1);}});
 return {kind:matches.length?'debug':'unmapped',lines:[...new Set(matches)],label:`${leaf||'Debug source'}:${location.line}${matches.length?' · mapped debug regions':' · no PTX mapping'}`};
}
export function regionLabel(r){return r&&Number.isFinite(r.offset)&&Number.isFinite(r.bytes)?`${r.address_space||'memory'} · bytes ${r.offset}–${r.offset+r.bytes-1}`:'Address interval not recorded';}

// A single selected version drives the row, preview, comparison and investigation.
export function selectedVersion(c, remembered){
 if(!Array.isArray(c.versions))return {index:c.initial??0,record:{label:c.selected_label||'Public PTX',raw:{result:c.result}}};
 const candidate=remembered??c.initial??0;
 const index=Number.isInteger(candidate)&&candidate>=0&&candidate<c.versions.length?candidate:0;
 return {index,record:c.versions[index]};
}
export function diagnosticLocations(source,raw){
 const locations=[];
 for(const [i,d] of (raw.diagnostics||[]).entries()){
  const location=d?.location||d?.details?.location;
  if(location)locations.push({id:`diagnostic-${i}`,label:'Diagnostic location',context:d.code||d.message||'Recorded diagnostic',location,mapping:sourceLocations(source,location),unresolved:false});
 }
 const pair=raw.evidence?.unsupported_memory_pair;
 for(const [key,tag] of [['first','A'],['second','B']]){
  const a=pair?.[key];if(!a?.location)continue;
  locations.push({id:`unresolved-${key}`,label:`Unresolved access ${tag} · ${String(a.mode||'access').toUpperCase()} · actor ${a.actor??'unknown'}`,context:'Overlap unresolved; not a confirmed race',location:a.location,mapping:sourceLocations(source,a.location),unresolved:true});
 }
 return locations;
}
