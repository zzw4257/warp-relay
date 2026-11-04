import json
import tempfile
import unittest
from pathlib import Path

from gpu.prepare_bundle import prepare
from gpu.run_validation import numerical_pass, sanitizer_pass, summarize_timings
from warp_relay.runner import ROOT


class RuntimeEvidenceTests(unittest.TestCase):
    def test_partial_or_failed_numerical_run_does_not_pass(self):
        receipt={'exit_code':0,'timeout':False}
        payload=b'{"kind":"correctness_summary","passed":true,"cases":39}\n'
        self.assertTrue(numerical_pass(receipt,payload))
        self.assertFalse(numerical_pass({**receipt,'timeout':True},payload))
        self.assertFalse(numerical_pass({**receipt,'exit_code':2},payload))
        self.assertFalse(numerical_pass(receipt,payload.replace(b'39',b'1')))
        self.assertFalse(numerical_pass(receipt,payload+payload))
        self.assertFalse(numerical_pass(receipt,b''))

    def test_timing_summary_requires_all_finite_pairs(self):
        rows=[{'kind':'timing_pair','sample':i,'baseline_us':4,'candidate_us':4} for i in range(31)]
        self.assertEqual(summarize_timings(rows)['paired_ratio_median'],1)
        with self.assertRaises(ValueError): summarize_timings(rows[:-1])
        for invalid in [0,-1,float('inf'),float('nan')]:
            altered=[dict(row) for row in rows]; altered[0]['candidate_us']=invalid
            with self.assertRaises(ValueError): summarize_timings(altered)

    def test_sanitizer_formats_require_zero_findings_and_target_execution(self):
        receipt={'exit_code':0,'timeout':False}
        output=b'{"kind":"correctness_summary","passed":true,"cases":1}\n'
        race='========= RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)\n'
        memory='========= ERROR SUMMARY: 0 errors\n'
        self.assertTrue(sanitizer_pass('racecheck',receipt,race,output))
        self.assertTrue(sanitizer_pass('memcheck',receipt,memory,output))
        self.assertFalse(sanitizer_pass('racecheck',receipt,memory,output))
        self.assertFalse(sanitizer_pass('racecheck',receipt,race,b''))
        self.assertFalse(sanitizer_pass('racecheck',{**receipt,'exit_code':3},race,output))
        self.assertFalse(sanitizer_pass('racecheck',receipt,race.replace('0 errors','1 error'),output))

    def test_bundle_contract_rejects_modified_input_before_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); run=root/'run'; (run/'inputs').mkdir(parents=True)
            (run/'summary.json').write_text('{}')
            (run/'inputs/input.json').write_text('{}')
            with self.assertRaisesRegex(AssertionError,'byte-identical'):
                prepare(run,root/'staging')
            self.assertFalse((root/'staging').exists())


if __name__=='__main__':
    unittest.main()
