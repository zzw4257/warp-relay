// Shareable kernel locations: #case/<id>/<version>/<view>[/<stage>[/L<line>]].
// The hash only selects what to show. It never changes or creates a saved record.
export const VIEWS=['evidence','diagnosis','rules','meta','scope'];
export const STAGES={evidence:'packet',response:'response',meta:'response',checks:'checks',inspect:'source'};
const STAGE_SLUG={packet:'evidence',response:'response',checks:'checks',source:'inspect'};
export const versionSlug=label=>String(label||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'');

export function parseCaseRoute(hash){
 if(typeof hash!=='string'||!hash.startsWith('#case/'))return null;
 const parts=hash.slice(6).split('/').filter(Boolean).map(p=>{try{return decodeURIComponent(p);}catch{return null;}});
 const route={id:parts[0]||'',version:null,view:null,stage:null,line:null,ignored:[]};
 let i=1;
 if(parts.length>i&&!VIEWS.includes(parts[i]))route.version=parts[i++];
 if(VIEWS.includes(parts[i]))route.view=parts[i++];
 if(route.view==='meta'&&Object.hasOwn(STAGES,parts[i]??''))route.stage=STAGES[parts[i++]];
 if(route.stage==='source'&&/^L[1-9]\d{0,6}$/.test(parts[i]??''))route.line=Number(parts[i++].slice(1));
 route.ignored=parts.slice(i).map(p=>p??'(undecodable)');
 if(parts.slice(0,i).includes(null))route.ignored.push('(undecodable)');
 return route;
}

// Canonical form always names version and view, so a reload or new browser restores the same place.
export function formatCaseRoute({id,version,view='evidence',stage=null,line=null}){
 let hash=`#case/${encodeURIComponent(id)}/${encodeURIComponent(version)}/${view}`;
 if(view==='meta'&&STAGE_SLUG[stage]){hash+='/'+STAGE_SLUG[stage];if(stage==='source'&&Number.isInteger(line)&&line>0)hash+='/L'+line;}
 return hash;
}

// Tab names used by the investigation view.
export const tabForView=view=>view==='scope'?'scope':['diagnosis','rules','meta'].includes(view)?'review':view==='evidence'?'witness':null;
export const providerForView=view=>view==='rules'?'baseline':view==='meta'?'model':null;

// The first case whose saved review holds a validated Meta response. Read-only; no model call.
let metaRecord=null;
export function findMetaRecord(cases){
 metaRecord??=Promise.all(cases.map(c=>fetch(`/api/reviews/${encodeURIComponent(c.id)}/${Number(c.initial)||0}`).then(r=>r.ok?r.json():null).catch(()=>null).then(r=>r?.model?.status==='received_validated'?{id:c.id,version:Number(c.initial)||0,label:c.selected_label||'Public PTX',title:c.title}:null)))
  .then(found=>found.filter(Boolean));
 return metaRecord;
}
