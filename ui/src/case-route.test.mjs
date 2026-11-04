import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {parseCaseRoute,formatCaseRoute,versionSlug,tabForView,providerForView} from './case-route.mjs';
const get=id=>JSON.parse(fs.readFileSync(new URL(`../../warp_relay/cases/${id}.json`,import.meta.url)));

test('canonical case links round-trip version, view, Meta stage and inspected PTX line',()=>{
 const full='#case/tma/public-ptx/meta/inspect/L402';
 assert.deepEqual(parseCaseRoute(full),{id:'tma',version:'public-ptx',view:'meta',stage:'source',line:402,ignored:[]});
 assert.equal(formatCaseRoute(parseCaseRoute(full)),full);
 assert.equal(formatCaseRoute({id:'weightnorm',version:'candidate-4',view:'scope'}),'#case/weightnorm/candidate-4/scope');
 assert.equal(formatCaseRoute({id:'tma',version:'public-ptx',view:'meta',stage:'checks',line:402}),'#case/tma/public-ptx/meta/checks');
 assert.equal(formatCaseRoute({id:'tma',version:'public-ptx',view:'meta'}),'#case/tma/public-ptx/meta','no stage is claimed for a Meta view without an audited record');
 assert.equal(formatCaseRoute({id:'tma',version:'public-ptx',view:'meta',stage:'packet'}),'#case/tma/public-ptx/meta/evidence');
});
test('short and legacy links stay valid and leave unspecified parts to the current view',()=>{
 assert.deepEqual(parseCaseRoute('#case/weightnorm'),{id:'weightnorm',version:null,view:null,stage:null,line:null,ignored:[]});
 assert.deepEqual(parseCaseRoute('#case/tma/meta'),{id:'tma',version:null,view:'meta',stage:null,line:null,ignored:[]});
 assert.equal(parseCaseRoute('#case/tma/meta/meta').stage,'response');
 assert.equal(parseCaseRoute('#library'),null);
 assert.equal(parseCaseRoute('#run/x'),null);
});
test('malformed, unknown and out-of-range parts are ignored instead of guessed',()=>{
 const r=parseCaseRoute('#case/tma/public-ptx/meta/inspect/L0/extra');
 assert.equal(r.line,null);assert.deepEqual(r.ignored,['L0','extra']);
 assert.equal(parseCaseRoute('#case/tma/public-ptx/evidence/inspect/L402').stage,null,'stages belong to the Meta view only');
 assert.equal(parseCaseRoute('#case/tma/public-ptx/meta/checks/L402').line,null,'lines belong to the Inspect stage only');
 assert.equal(parseCaseRoute('#case/tma/public-ptx/meta/nope').stage,null);
 const bad=parseCaseRoute('#case/tma/%E0%A4%A/meta');assert.equal(bad.version,null);assert.equal(bad.view,'meta','a bad version segment does not discard a valid view');assert.ok(bad.ignored.includes('(undecodable)'));
 assert.equal(parseCaseRoute('#case/weightnorm/candidate-99/evidence').version,'candidate-99','resolution against the record happens in the view');
 assert.equal(parseCaseRoute('#case/tma/public-ptx/meta/inspect/L99999999').line,null);
});
test('version slugs are unique per saved case and map tabs/providers without inventing records',()=>{
 for(const id of ['weightnorm','tma','barriers','repair']){const slugs=get(id).versions.map(v=>versionSlug(v.label));assert.equal(new Set(slugs).size,slugs.length,id);assert.ok(slugs.every(Boolean));}
 assert.deepEqual(get('weightnorm').versions.map(v=>versionSlug(v.label)),['original','candidate-1','candidate-2','candidate-3','candidate-4']);
 assert.equal(tabForView('meta'),'review');assert.equal(tabForView('evidence'),'witness');assert.equal(tabForView('scope'),'scope');assert.equal(tabForView(null),null);
 assert.equal(providerForView('rules'),'baseline');assert.equal(providerForView('meta'),'model');assert.equal(providerForView('diagnosis'),null);
});
