"""Import a bounded public catalog; never execute imported reference programs."""
import hashlib,json,re
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from warp_relay.core import feedback
OUT=ROOT/'warp_relay/cases';OUT.mkdir(exist_ok=True)
REV='421ff2c7d140341f64d2bc1f1edd045b65a7c403'
def norm(text):
    # Preserve source line count and public suffix; remove original build host prefixes.
    def clean(match):
        value=match.group()
        for marker in ['python/tutorials/','corpus/']:
            if marker in value:return value[value.index(marker):]
        return 'build/' + value.rsplit('/',1)[-1]
    return re.sub(r"/(?:raid|home|Users|tmp|usr/local|opt)/[^\s\"'<>\\]+",clean,text)
def load(path):return json.loads(norm(path.read_text()))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
local=[('weightnorm','WeightNorm','PyTorch','Reduction','Barrier removal across a shared-memory reduction.','evidence/round4-20261031/weightnorm-cpu','recorded-weightnorm',1),('repair','Shared exchange','Microfixture','Repair','A missing synchronization point, repaired and checked.','evidence/round2-20261031/repair','recorded-repair',0),('barriers','Barrier control','Microfixture','Edit policy','Two barriers, one retained, then an unsafe deletion.','evidence/round2-20261031/optimize','recorded-barriers',2),('multimargin','MultiMarginLoss','PyTorch','Support boundary','An unsupported front-end operation stops the local analysis.','evidence/round2-20261031/public-pytorch','recorded-unsupported',0)]
up=[('layernorm','LayerNorm','PyTorch','Reduction','Two actors overlap in shared memory.','pytorch__aten_layer_norm_kernel__sm_100a'),('maxunpool','MaxUnpooling','PyTorch','Support boundary','Dynamic global overlap remains unresolved.','pytorch__aten_MaxUnpooling__sm_100a'),('softmax','Softmax','PyTorch','Reduction','Recorded synchronization and reference checks.','pytorch__aten_SoftMax__sm_100a'),('async-copy','Async copy','Triton Gluon','Async transfer','Inspect asynchronous transfers and their wait structure.','tritongluon-03-async-copy'),('tma','TMA pipeline','Triton Gluon','Async transfer','Overlapping writes in a pipelined shared-memory allocation.','tritongluon-04-tma-pipelined'),('tcgen','Tensor-memory copy','Triton Gluon','Async transfer','A write/write witness with source-language debug locations.','tritongluon-10-tcgen05-copy'),('online-softmax','Online softmax','TileLang','Reduction','A larger kernel with recorded scoped reference checks.','tilelang-online-softmax'),('rmsnorm','RMSNorm','TIRx','Reduction','Persistent reduction with a fixed launch contract.','tirx-basic-rmsnorm')]
index=[]
for id,title,family,kind,description,folder,run,initial in local:
    p=ROOT/folder;s=load(p/'summary.json');versions=[]
    for n,row in enumerate(s['iterations']):
        d=p/row['path'];raw=load(d/'verification/result.json');versions.append({'label':'Original' if n==0 else f'Candidate {n}','source':norm((d/'kernel.ptx').read_text()),'raw':raw,'accepted':row.get('accepted'),'path':row['path']})
    case={'id':id,'title':title,'family':family,'kind':kind,'description':description,'provenance':'Local record','run_id':run,'initial':initial,'versions':versions,'contract':load(p/'inputs/input.json'),'retained':s.get('selected'),'source_url':f'https://github.com/gpu-verifier/sentryward/tree/{REV}','scope_note':'Locally recorded synchronization-only checks. Finite GPU tests are a separate WeightNorm record; no timing claim.','manifest':{'record':folder,'summary_sha256':sha(p/'summary.json'),'normalization':'Public build path prefixes removed; PTX line count unchanged.'}}
    (OUT/f'{id}.json').write_text(json.dumps(case,indent=2)+'\n');index.append({k:v for k,v in case.items() if k not in {'versions','contract','manifest'}}|{'result':versions[initial]['raw']['result'],'selected_label':versions[initial]['label'],'retained_label':next((v['label'] for v in versions if v.get('path')==s.get('selected')),None),'versions':len(versions),'lines':len(versions[0]['source'].splitlines())})
for id,title,family,kind,description,stem in up:
    p=ROOT/'vendor/sentryward/examples'/stem;ptx=ROOT/'vendor/sentryward/corpus'/f'{stem}.ptx';raw=load(p/'output.json');binding=load(p/'reference_binding.json');prov=binding.get('provenance',{})
    case={'id':id,'title':title,'family':family,'kind':kind,'description':description,'provenance':'Upstream record','initial':0,'versions':[{'label':'Public PTX','source':norm(ptx.read_text()),'raw':raw}], 'contract':load(p/'input.json'),'source_url':f'https://github.com/gpu-verifier/sentryward/tree/{REV}/examples/{stem}','upstream_sources':prov.get('upstream',[]),'scope_note':prov.get('scope','Fixed upstream input contract.'),'provenance_detail':prov,'manifest':{'commit':REV,'ptx_sha256_original':sha(ptx),'result_sha256_original':sha(p/'output.json'),'input_sha256_original':sha(p/'input.json'),'normalization':'Public build path prefixes removed from PTX/debug locations; instruction text and line count unchanged.','result_origin':'Bundled public output.json; not re-executed by Warp Relay.'}}
    (OUT/f'{id}.json').write_text(json.dumps(case,indent=2)+'\n');index.append({k:v for k,v in case.items() if k not in {'versions','contract','manifest','provenance_detail'}}|{'result':raw['result'],'versions':1,'lines':len(case['versions'][0]['source'].splitlines())})
(OUT/'index.json').write_text(json.dumps(index,indent=2)+'\n')
print(f'Imported {len(index)} cases, {sum(p.stat().st_size for p in OUT.glob("*.json")):,} bytes. No verification executed.')
