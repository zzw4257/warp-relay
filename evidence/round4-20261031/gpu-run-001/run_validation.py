"""Run a fixed, hash-checked public PTX bundle under an external GPU allocation.

No network, credentials, package installation, arbitrary references or shell calls.
Invoke using the site's existing cmu-gpu run wrapper and --allow-gpu.
"""
import argparse
import hashlib
import json
import os
import platform
import signal
import statistics
import subprocess
import time
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def execute(arguments, out, name, timeout=60):
    started=time.time()
    process=subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out=False
    try:
        stdout,stderr=process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out=True
        os.killpg(process.pid, signal.SIGKILL)
        stdout,stderr=process.communicate()
    (out/(name+'.stdout')).write_bytes(stdout)
    (out/(name+'.stderr')).write_bytes(stderr)
    receipt={'arguments':arguments,'exit_code':process.returncode,'timeout':timed_out,'elapsed_seconds':time.time()-started}
    (out/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt,stdout

def numerical_pass(receipt, output):
    rows=[json.loads(line) for line in output.splitlines() if line.startswith(b'{')]
    summaries=[r for r in rows if r.get('kind')=='correctness_summary']
    return receipt['exit_code']==0 and not receipt['timeout'] and len(summaries)==1 and summaries[0]['passed'] and summaries[0]['cases']==39

def summarize_timings(rows):
    pairs=[r for r in rows if r.get('kind')=='timing_pair']
    if len(pairs)!=31 or [p['sample'] for p in pairs]!=list(range(31)):
        raise ValueError('Expected all 31 paired timing samples')
    for p in pairs:
        if not all(isinstance(p[k],(float,int)) and 0<p[k]<1e6 for k in ('baseline_us','candidate_us')):
            raise ValueError('Invalid timing value')
    return {'samples':31,'baseline_median_us':statistics.median(p['baseline_us'] for p in pairs),
            'selected_median_us':statistics.median(p['candidate_us'] for p in pairs),
            'paired_ratio_median':statistics.median(p['baseline_us']/p['candidate_us'] for p in pairs),
            'baseline_range_us':[min(p['baseline_us'] for p in pairs),max(p['baseline_us'] for p in pairs)],
            'selected_range_us':[min(p['candidate_us'] for p in pairs),max(p['candidate_us'] for p in pairs)]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--allow-gpu', action='store_true')
    parser.add_argument('--sanitizer', required=True)
    args=parser.parse_args()
    if not args.allow_gpu: parser.error('GPU execution requires --allow-gpu and an existing authorized allocation')
    if not os.environ.get('CMU_GPU_CLAIM_ID') or not os.environ.get('CUDA_VISIBLE_DEVICES'):
        parser.error('Use the existing cmu-gpu run wrapper; an active allocation is required')
    manifest=json.loads(Path('manifest.json').read_text())
    for name,expected in manifest['files'].items():
        if Path(name).name!=name or sha(Path(name))!=expected: raise ValueError('Bundle hash mismatch: '+name)
    out=args.out
    if out.is_absolute(): parser.error('Use a relative output path to keep evidence portable')
    out.mkdir(parents=True,exist_ok=False)
    summary={'schema':'warp-relay.gpu-run/v1','manifest_sha256':sha(Path('manifest.json')),
             'runner_sha256':sha(Path('runner')),'harness_sha256':sha(Path('weightnorm_runner.cpp')),
             'python':platform.python_version(),'physical_gpu':os.environ['CUDA_VISIBLE_DEVICES'],
             'numerical_tests':{},'sanitizers':{},'benchmark':[],
             'model_executed':False,'formal_equivalence':'not_requested',
             'performance_claim':'measurement_only; selected deletion is not executed under this fixed launch; no general speedup claim',
             'limitations':['Finite numerical tests, not a universal equivalence proof','One B200 and one fixed public shape','Hot-cache CUDA graph replay, 100 nodes per sample, 31 alternating pairs per trial','Shared server; clocks not locked; no other process was stopped']}
    try:
        execute(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu,clocks.sm,temperature.gpu,power.draw','--format=csv'],out,'gpu-before',10)
        receipt,_=execute(['./runner','self-test'],out,'host-self-test',10)
        if receipt['exit_code']: raise RuntimeError('Host reference self-test failed')
        for name in ('baseline','selected','counterexample'):
            variant=manifest['variants'][name]
            command=['./runner','check',variant['file'],manifest['entry'],variant['file']]
            receipt,stdout=execute(command,out,name+'-numerical')
            summary['numerical_tests'][name]={'passed':numerical_pass(receipt,stdout),'receipt':name+'-numerical.receipt.json','sync_gate':variant['synchronization_result']}
        # All variants are measured for memory safety; rejected candidates remain rejected
        # even if their sampled outputs happen to match the reference.
        for tool in ('memcheck','racecheck'):
            for name in ('baseline','selected','counterexample'):
                variant=manifest['variants'][name]; stem=name+'-'+tool
                command=[args.sanitizer,'--tool',tool,'--error-exitcode','3','--log-file',str(out/(stem+'.log'))]
                if tool=='racecheck': command+=['--racecheck-report','analysis']
                command+=['./runner','quick',variant['file'],manifest['entry'],variant['file']]
                receipt,_=execute(command,out,stem,90)
                log=(out/(stem+'.log')).read_text() if (out/(stem+'.log')).exists() else ''
                summary['sanitizers'][stem]={'exit_code':receipt['exit_code'],'timeout':receipt['timeout'],'log':stem+'.log',
                                            'passed':receipt['exit_code']==0 and not receipt['timeout'] and 'ERROR SUMMARY: 0 errors' in log}
        valid=all(summary['numerical_tests'][n]['passed'] for n in ('baseline','selected'))
        valid &= all(summary['sanitizers'][n+'-'+t]['passed'] for n in ('baseline','selected') for t in ('memcheck','racecheck'))
        if valid:
            for trial in range(3):
                command=['./runner','benchmark',manifest['variants']['baseline']['file'],manifest['entry'],manifest['variants']['selected']['file']]
                receipt,stdout=execute(command,out,'benchmark-'+str(trial))
                if receipt['exit_code'] or receipt['timeout']: raise RuntimeError('Benchmark incomplete')
                summary['benchmark'].append(summarize_timings([json.loads(line) for line in stdout.splitlines() if line.startswith(b'{')]))
        else: summary['benchmark_status']='blocked_by_runtime_validation'
        summary['status']='completed' if valid else 'runtime_validation_failed'
    except Exception as exc:
        summary['status']='blocked'; summary['error']=str(exc)
    finally:
        execute(['nvidia-smi','--query-gpu=index,name,memory.used,utilization.gpu,clocks.sm,temperature.gpu,power.draw','--format=csv'],out,'gpu-after',10)
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return 0 if summary['status']=='completed' else 2

if __name__=='__main__':
    raise SystemExit(main())
