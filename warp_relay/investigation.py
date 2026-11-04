"""Bounded feedback-driven inspection; the model and checker are never rewritten.

Each follow-up acquires real source context referenced by the previous validated
model diagnosis. Source/contract/verifier hashes remain frozen. No generated
shell, Python, PTX or network address is executed by this controller.
"""
import json
from pathlib import Path
from .core import digest,write_json
from .diagnosis import CASES,packet,review,INSTRUCTION
POLICY={'id':'evidence-investigation-v1','prompt_sha256':digest(INSTRUCTION),
        'editable':'diagnostic hypotheses and next inspections only',
        'frozen':['kernel','input contract','verifier','acceptance rule'],
        'maximum_rounds':3,'maximum_context_lines':240}


def acquire_context(p,diagnosis,seen):
    c=json.loads((CASES/(p['case_id']+'.json')).read_text());source=c['versions'][p['version']]['source'];lines=source.splitlines()
    if digest(source)!=p['source_sha256']:raise ValueError('Frozen source changed during investigation')
    facts={f['id']:f for f in p['facts']};added=[];used=0
    for step in diagnosis['next_steps']:
        if step['action'] not in {'inspect_source','inspect_debug_regions','inspect_lifecycle'}:continue
        for id in step['citations']:
            f=facts[id]
            for n in f.get('mapping',{}).get('lines',[]):
                start=max(1,n-10);end=min(len(lines),n+20);key=f'context:{start}:{end}'
                if key in seen or used+end-start+1>POLICY['maximum_context_lines']:continue
                seen.add(key);used+=end-start+1
                added.append({'id':key,'kind':'source_context','requested_by':id,'mapping':{'kind':'debug_region' if f['mapping']['kind']=='debug_region' else 'instruction','lines':[n]},
                              'value':{'source_sha256':p['source_sha256'],'start':start,'end':end,'lines':[{'line':i,'text':lines[i-1]} for i in range(start,end+1)]}})
    return added


def investigate(case_id,out,version=None,model=None,allow_call=False,credits_authorized=False,rounds=2):
    if type(rounds)is not int or not 1<=rounds<=3:raise ValueError('Use one to three investigation rounds')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);p=packet(case_id,version);context=[];seen=set();prior=None
    record={'schema':'warp-relay.investigation/v1','policy':POLICY,'case_id':case_id,'version':p['version'],
            'source_sha256':p['source_sha256'],'verifier_sha256':p['verifier_sha256'],'round_budget':rounds,
            'model_calls_attempted':0,'rounds':[],'stop_reason':'pending','claim':'iterative diagnostic refinement; not self-training or autonomous agent modification'}
    write_json(out/'policy.json',POLICY)
    for i in range(rounds):
        result=review(case_id,out/f'{i:03d}-review',version,model,allow_call,credits_authorized,context,prior)
        entry={'index':i,'path':f'{i:03d}-review','model_status':result['model']['status'],'request_sha256':result['receipt']['request_sha256'],
               'observed_context_facts':len(context),'new_context_facts':0,'decision':'stop'}
        record['model_calls_attempted']+=result['receipt']['calls_attempted'];record['rounds'].append(entry)
        if result['model']['status']!='received_validated':record['stop_reason']=result['model']['status'];break
        prior=result['model']['diagnosis'];additional=acquire_context(result['packet'],prior,seen);entry['new_context_facts']=len(additional)
        write_json(out/f'{i:03d}-review/acquired-context.json',additional)
        if not additional:record['stop_reason']='no_new_evidence';break
        if i+1==rounds:record['stop_reason']='round_budget';break
        context.extend(additional);entry['decision']='inspect_then_refine'
    write_json(out/'investigation.json',record);return record
