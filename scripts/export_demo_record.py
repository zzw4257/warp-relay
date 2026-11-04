"""Export the existing public static record for the shared native UI demo."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from warp_relay.core import feedback
base=ROOT/'evidence/round4-20261031/weightnorm-cpu'
summary=json.loads((base/'summary.json').read_text())
rows=[]
for row in summary['iterations']:
 step=base/row['path']
 rows.append({**row,'source':(step/'kernel.ptx').read_text(),
              'diff':(step/'change.diff').read_text() if (step/'change.diff').exists() else '',
              'verification':feedback(json.loads((step/'verification/result.json').read_text()))})
summary={key:summary[key] for key in ('name','selected','provider','objective','stop_reason','iterations')}
record={'job':{'id':'recorded-weightnorm','name':summary['name'],'state':'completed','phase':'finished','recorded':True},
        'summary':summary,'contract':json.loads((base/'inputs/input.json').read_text()),'rounds':rows}
(ROOT/'ui/src/weightnorm-record.json').write_text(json.dumps(record,indent=2)+'\n')
print('Updated the public WeightNorm static record; no verifier or model call.')
