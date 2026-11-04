"""Prepare only reviewed public artifacts for the explicitly authorized GPU run."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_INPUT_SHA = '66dd6502a0e8e24600fc203e574bfeef8f7fe02d1d48dc603765444412ad45c1'
PUBLIC_PTX_SHA = '0fa57a8625c2f74ffad1684891484cbddc22e3f01372aaa2881334509ed75288'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(run, out):
    from warp_relay.core import check_candidate
    summary = json.loads((run / 'summary.json').read_text())
    config_path = run / 'inputs/input.json'
    assert sha(config_path) == PUBLIC_INPUT_SHA, 'The public input must remain byte-identical'
    baseline = run / '000-baseline/kernel.ptx'
    assert sha(baseline) == PUBLIC_PTX_SHA, 'The original public PTX must remain byte-identical'
    selected = run / summary['selected'] / 'kernel.ptx'
    rows = {row['path']: row for row in summary['iterations']}
    assert rows[summary['selected']]['accepted'] and summary['selected'] != '000-baseline'
    negative_row = next(row for row in summary['iterations'] if row['result'] == 'potential_race' and not row['accepted'])
    negative = run / negative_row['path'] / 'kernel.ptx'
    out.mkdir(parents=True, exist_ok=False)
    manifest = {
        'schema': 'warp-relay.gpu-bundle/v1',
        'sentryward_revision': summary['verifier']['revision'],
        'input_sha256': PUBLIC_INPUT_SHA,
        'entry': json.loads(config_path.read_text())['entry'],
        'scope': 'Unchanged public WeightNorm 2x1024 BF16, grid=2 block=256 dynamic shared=1024; synchronization is separate from numerical testing and performance.',
        'variants': {}, 'files': {},
        'tolerances_fixed_before_run': {'norm_rtol': 2e-6, 'norm_atol': 1e-7, 'output_bf16_max_ulp': 1},
        'reference': 'Independent CPU long-double row sum of squares, square root and scaling, BF16 nearest-even output; compare NaN class for zero norms.',
        'cases': '32 deterministic finite random cases and seven structured cases; 3 launches each; 39 cases / 117 launches per variant.',
        'candidate_scope': 'Only removal of original PTX line 167, skipped at the fixed block size. Static barrier count reduction, no expected executed-instruction reduction.'
    }
    for name, source, row in [('baseline', baseline, rows['000-baseline']), ('selected', selected, rows[summary['selected']]), ('counterexample', negative, negative_row)]:
        check_candidate(baseline.read_text(), source.read_text())
        assert sha(source) == row['kernel_sha256']
        shutil.copyfile(source, out / f'{name}.ptx')
        manifest['variants'][name] = {'file': f'{name}.ptx', 'sha256': sha(source), 'synchronization_result': row['result'], 'accepted_by_sync_gate': row['accepted'], 'source_round': row['path']}
    shutil.copyfile(config_path, out / 'input.json')
    for name in ('weightnorm_runner.cpp', 'run_validation.py'):
        shutil.copyfile(ROOT / 'gpu' / name, out / name)
    for name in ('SentryWard-Apache-2.0.txt', 'PyTorch-LICENSE.txt'):
        shutil.copyfile(ROOT / 'licenses' / name, out / name)
    for path in out.iterdir(): manifest['files'][path.name] = sha(path)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    prepare(args.run, args.out)
