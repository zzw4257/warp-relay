"""Offline audit and source-context acquisition for an already completed review."""
import argparse,json,hashlib,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from warp_relay.diagnosis import validate_recorded_packet,parse_response,CASES,REVIEWS
from warp_relay.investigation import acquire_context
from warp_relay.core import write_json,digest

def audit(directory,out,install=True):
 directory=Path(directory);out=Path(out);out.mkdir(parents=True,exist_ok=False)
 read=lambda name:json.loads((directory/name).read_text())
 review=read('review.json');p=validate_recorded_packet(review['packet']);receipt=read('model-receipt.json');request=read('model-request.json');response=read('model-response.json')
 assert digest(json.dumps(request).encode())==receipt['request_sha256']
 assert request['model']==receipt['requested_model']
 assert response['model']==receipt['response_model']==review['model']['model']
 assert response.get('id')==receipt.get('response_id') and response.get('usage')==receipt.get('usage')
 assert parse_response(response,p)==review['model']['diagnosis']
 assert json.loads(request['messages'][1]['content'])['packet']==p
 context=acquire_context(p,review['model']['diagnosis'],set())
 validate_recorded_packet({**p,'facts':p['facts']+context})
 facts={f['id']:f for f in p['facts']};lines=json.loads((CASES/(p['case_id']+'.json')).read_text())['versions'][p['version']]['source'].splitlines()
 # Explicit review of the actual TMA response, not a generic prose-quality score.
 assert p['case_id']=='tma' and p['version']==0
 assert facts['race:0:relationship']['value']['region']['offset']==49152
 assert all(facts['race:0:'+side]['value']['mode']=='write' and facts['race:0:'+side]['value']['bytes']==4 for side in ['first','second'])
 assert facts['race:0:first']['mapping']['lines']==[348,402,510,613]
 assert 'add.s32' in lines[401] and all('stmatrix.' in lines[n-1] for n in [348,510,613])
 record={'schema':'warp-relay.review-audit/v1','reviewed_at':datetime.now(timezone.utc).isoformat(),'reviewer':'Codex offline source and record review',
  'case_id':p['case_id'],'version':p['version'],'source_sha256':p['source_sha256'],'diagnosis_sha256':digest(json.dumps(review['model']['diagnosis'],sort_keys=True)),
  'response_sha256':digest((directory/'model-response.json').read_bytes()),'integrity_checks':['Frozen source and verifier identity','Request hash and exact input packet','Response model, ID and usage agree with receipt','Parsed response matches stored diagnosis','Every typed citation and mapped location revalidated'],
  'supported_observations':['Two modeled 4-byte writes overlap shared offset 49152; the verifier reports no proven required ordering.','Both accesses map to four PTX debug-region starts, not exact conflicting instructions.','L402 is address arithmetic; L348, L510 and L613 begin stmatrix regions.','Nearby wait_group and bar.sync are present, but their presence alone does not establish ordering between the witnessed accesses.','Representative election is enabled and triggered; the result remains assumption-dependent.'],
  'comparison':{'access_coverage':'Both fixed rules and Meta cite 2/2 accesses.','mapping_limits':'Both acknowledge 2/2 ambiguous mappings.','added_context':'Meta combines overlap, instruction classes and nearby synchronization into a focused source-inspection question.','win_claim':False,'limitation':'One visible case, no held-out comparison or measured investigation-time improvement.'},
  'remaining':['Exact conflicting PTX instruction is unresolved.','No code edit, repair or second model round was executed.','No numerical equivalence or GPU performance conclusion follows.'],
  'follow_up':{'action':'inspect_debug_regions','executed':'Read actual immutable source context locally','regions':[f['mapping']['lines'][0] for f in context],'source_lines':sum(len(f['value']['lines']) for f in context),'context':context,'additional_model_calls':0,'next_model_step':'Not authorized or executed'}}
 for name in ['packet.json','model-request.json','model-response.json','model-receipt.json','review.json']:
  (out/name).write_bytes((directory/name).read_bytes())
 write_json(out/'audit.json',record)
 if install:write_json(REVIEWS/f"{p['case_id']}-{p['version']}-audit.json",record)
 print(json.dumps({'out':str(out),'regions':record['follow_up']['regions'],'source_lines':record['follow_up']['source_lines'],'additional_calls':0}))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('--out',required=True);parser.add_argument('--no-install',action='store_true',help='Check into a new directory without replacing the installed audit');args=parser.parse_args();audit(args.directory,args.out,install=not args.no_install)
