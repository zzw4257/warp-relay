import test from 'node:test';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {candidateModel,annotations,barrierAnnotations,verdictFor} from './model.mjs';
import {renderInspection,renderActivity} from './inspection.mjs';
const data=JSON.parse(readFileSync(new URL('./weightnorm-record.json',import.meta.url)));
test('inspected rejected candidate is separate from retained run artifact',()=>{
 const m=candidateModel(data,1);assert.equal(m.status,'rejected');assert.equal(m.retained,4);
 const html=renderInspection(data,{index:1,tab:'diff'});
 assert.match(html,/Candidate 1 decision/);assert.match(html,/Run outcome <strong>Candidate 4 retained/);
 assert.doesNotMatch(html,/Passed static synchronization scope/);
});
test('persistent annotations use original evidence coordinates and both actors',()=>{
 const m=candidateModel(data,1),notes=annotations(m,true);
 assert.deepEqual(notes.map(n=>[n.side,n.lineNumber,n.metadata.actor,n.metadata.mode]),[['additions',126,128,'write'],['additions',136,0,'read']]);
 assert.equal(m.range,'512–515');assert.match(m.original.source.split('\n')[136],/ld.shared.f32/);
 assert.match(m.original.source.split('\n')[126],/bar.sync/);
 assert.equal(annotations(candidateModel(data,4),true).length,0);
});
test('candidate display never trusts input HTML',()=>{
 const copy=structuredClone(data);copy.rounds[1].verification.diagnostics[0].message='<img src=x onerror=alert(1)>';
 const html=renderInspection(copy,{index:1});assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img src=x'));
});
test('recorded and live activity boundaries remain explicit',()=>{
 assert.match(renderActivity(data.job),/predates live phase events/);
 const html=renderActivity({recorded:false,events:[{phase:'proposing_candidate',at:'2026-11-01T01:02:03Z',iteration:1}]});
 assert.match(html,/offline rule provider/);assert.match(html,/01:02:03/);assert.doesNotMatch(html,/AI is thinking/);
});

test('every rejection category has the same rail and inspector verdict',()=>{for(const result of ['potential_race','not_wellsynced','invalid_lifecycle','policy_rejected']){const row={accepted:false,result};assert.deepEqual(verdictFor(row),{status:'rejected',symbol:'×',verdict:'Rejected'});const copy=structuredClone(data);copy.rounds[1]={...copy.rounds[1],...row};assert.match(renderInspection(copy,{index:1}),/round-symbol rejected/);}});

test("demo PTX bytes match the recorded kernel hashes",()=>{for(const row of data.rounds)assert.equal(createHash("sha256").update(row.source).digest("hex"),row.kernel_sha256);});

test('removed barrier explanation requires the exact one-line source edit',()=>{
 const m=candidateModel(data,1);
 assert.deepEqual(barrierAnnotations(m,true).map(a=>[a.side,a.lineNumber]),[['deletions',127]]);
 assert.deepEqual(barrierAnnotations(m,false),[]);
 assert.deepEqual(barrierAnnotations({...m,row:{...m.row,source:m.original.source}},true),[]);
 assert.deepEqual(barrierAnnotations({...m,row:{...m.row,source:m.row.source.replace('st.shared.f32','st.shared.u32')}},true),[]);
});
