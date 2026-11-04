import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from warp_relay.diagnosis import packet,baseline,validate_diagnosis,evaluate,review,parse_response

class DiagnosisTests(unittest.TestCase):
 def test_real_debug_mapping_is_not_exact_instruction(self):
  p=packet('tma');access=[x for x in p['facts'] if x['kind']=='access'];self.assertTrue(any(x['mapping']['lines']==[348,402,510,613] for x in access));self.assertTrue(all(x['mapping']['kind']=='debug_region' for x in access))
  p=packet('tcgen');a=next(x for x in p['facts'] if x['kind']=='access');self.assertEqual(a['mapping']['kind'],'debug_region');self.assertIn(1091,a['mapping']['lines'])
 def test_true_access_coordinates(self):
  p=packet('weightnorm');a=[x for x in p['facts'] if x['kind']=='access'];self.assertEqual([x['mapping']['lines'] for x in a],[[126],[136]])
 def test_all_real_cases_have_valid_baseline(self):
  cases=json.loads(Path('warp_relay/cases/index.json').read_text())
  for c in cases:
   with self.subTest(case=c['id']):p=packet(c['id']);self.assertTrue(evaluate(baseline(p),p)['typed_citations_valid'])
 def test_unsupported_not_promoted_to_race(self):
  p=packet('maxunpool');d=baseline(p);self.assertEqual(d['assessment'],'inconclusive');self.assertTrue(evaluate(d,p)['inconclusive_preserved']);d['assessment']='sync_conflict'
  with self.assertRaises(ValueError):validate_diagnosis(d,p)
 def test_unknown_citation_rejected(self):
  p=packet('weightnorm');d=baseline(p);d['findings'][0]['citations']=['invented']
  with self.assertRaises(ValueError):validate_diagnosis(d,p)
 def test_exact_claim_from_debug_region_rejected(self):
  p=packet('tcgen');d=baseline(p);d['findings'][0]['locations'][0]['kind']='instruction'
  with self.assertRaises(ValueError):validate_diagnosis(d,p)
 def test_invented_line_and_malformed_reference_rejected(self):
  p=packet('weightnorm')
  for value in [99999,True]:
   d=baseline(p);d['findings'][0]['locations'][0]['ptx_line']=value
   with self.assertRaises(ValueError):validate_diagnosis(d,p)
  d=baseline(p);d['findings'][0]['locations'][0]['evidence_id']={}
  with self.assertRaises(ValueError):validate_diagnosis(d,p)
 def test_execution_claims_rejected(self):
  p=packet('weightnorm');d=baseline(p)
  for value in [True,0]:
   d['claims']['performance_gain']=value
   with self.assertRaises(ValueError):validate_diagnosis(d,p)
 def test_truncated_response_rejected(self):
  with self.assertRaises(ValueError):parse_response({'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},packet('tma'))
 def test_default_review_never_calls_network(self):
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',side_effect=AssertionError('Network forbidden')):
   r=review('tma',Path(t)/'review');self.assertEqual(r['model']['status'],'not_run');self.assertEqual(r['receipt']['calls_attempted'],0);self.assertTrue((Path(t)/'review/model-request.json').is_file())
 def test_missing_authorization_and_key_stop_before_network(self):
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',side_effect=AssertionError('Network forbidden')),patch.dict('os.environ',{},clear=True):
   for i,authorized in enumerate([False,True]):
    r=review('tma',Path(t)/str(i),model='test-model',allow_call=True,credits_authorized=authorized);self.assertEqual(r['model']['status'],'blocked');self.assertEqual(r['receipt']['calls_attempted'],0)
 def test_path_and_version_are_bounded(self):
  for case,version in [('../private',None),('tma',-1),('tma',99),('tma',True)]:
   with self.assertRaises(ValueError):packet(case,version)

class InvestigationTests(unittest.TestCase):
 def test_context_is_real_bounded_and_deduplicated(self):
  from warp_relay.investigation import acquire_context
  p=packet('tma');d=baseline(p);seen=set();facts=acquire_context(p,d,seen)
  self.assertGreater(len(facts),1);self.assertLessEqual(sum(len(f['value']['lines']) for f in facts),240)
  self.assertEqual(acquire_context(p,d,seen),[])
  source=json.loads(Path('warp_relay/cases/tma.json').read_text())['versions'][0]['source'].splitlines()
  for f in facts:
   for line in f['value']['lines']:self.assertEqual(line['text'],source[line['line']-1])
 def test_no_fake_rounds_without_model(self):
  from warp_relay.investigation import investigate
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',side_effect=AssertionError('Network forbidden')):
   r=investigate('tma',Path(t)/'investigation',rounds=3)
   self.assertEqual(len(r['rounds']),1);self.assertEqual(r['model_calls_attempted'],0);self.assertEqual(r['stop_reason'],'not_run')
 def test_round_budget_checked_before_writing(self):
  from warp_relay.investigation import investigate
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'review'
   with self.assertRaises(ValueError):investigate('tma',out,rounds=99)
   self.assertFalse(out.exists())

class ReviewTransportTests(unittest.TestCase):
 """Synthetic transport fixtures only; never copied into the demonstration data."""
 def test_timeout_is_uncertain_and_never_retried(self):
  from unittest.mock import Mock
  opener=Mock();opener.open.side_effect=TimeoutError()
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',return_value=opener),patch.dict('os.environ',{'MODEL_API_KEY':'unit-test-token'}):
   r=review('tma',Path(t)/'review',model='test-model',allow_call=True,credits_authorized=True)
   self.assertEqual(r['model']['status'],'uncertain');self.assertEqual(opener.open.call_count,1);self.assertEqual(r['receipt']['calls_attempted'],1)
 def test_malformed_received_response_is_rejected(self):
  import io
  from unittest.mock import Mock
  opener=Mock();opener.open.return_value=io.BytesIO(b'{broken')
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',return_value=opener),patch.dict('os.environ',{'MODEL_API_KEY':'unit-test-token'}):
   r=review('tma',Path(t)/'review',model='test-model',allow_call=True,credits_authorized=True)
   self.assertEqual(r['model']['status'],'rejected');self.assertEqual(r['receipt']['outcome'],'received');self.assertEqual(opener.open.call_count,1)
 def test_context_budget_stops_before_files_or_request(self):
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',side_effect=AssertionError('Network forbidden')):
   out=Path(t)/'review'
   with self.assertRaises(ValueError):review('tma',out,context=[{'text':'x'*100001}])
   self.assertFalse(out.exists())
 def test_baseline_combines_same_inspection_without_losing_evidence(self):
  d=baseline(packet('tma'));steps=[s for s in d['next_steps'] if s['action']=='inspect_debug_regions']
  self.assertEqual(len(steps),1);self.assertEqual(len(steps[0]['citations']),2)
 def test_import_revalidates_source_request_and_response(self):
  import io
  from unittest.mock import Mock
  from warp_relay.diagnosis import import_review,saved_review
  from warp_relay.investigation import acquire_context
  p=packet('tma');context=acquire_context(p,baseline(p),set());p['facts'].extend(context)
  raw={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(baseline(p))}}],'model':'test-model'}
  opener=Mock();opener.open.return_value=io.BytesIO(json.dumps(raw).encode())
  with tempfile.TemporaryDirectory() as t,patch('urllib.request.build_opener',return_value=opener),patch.dict('os.environ',{'MODEL_API_KEY':'unit-test-token'}),patch('warp_relay.diagnosis.REVIEWS',Path(t)/'installed'):
   out=Path(t)/'review';r=review('tma',out,model='test-model',allow_call=True,credits_authorized=True,context=context)
   self.assertEqual(r['model']['status'],'received_validated');destination=import_review(out)
   self.assertEqual(saved_review('tma')['model']['status'],'received_validated')
   with self.assertRaises(ValueError):import_review(out)
   destination.unlink()
   # A well-formed diagnosis does not legitimize a mismatched provider receipt.
   original=json.loads((out/'model-response.json').read_text())
   for field,value in [('model','different-model'),('id','different-response'),('usage',{'total_tokens':999})]:
    forged={**original,field:value};(out/'model-response.json').write_text(json.dumps(forged))
    with self.assertRaises(ValueError):import_review(out)
    self.assertFalse(destination.exists())
   (out/'model-response.json').write_text(json.dumps(original))
   r['packet']['facts'][-1]['value']['lines'][0]['text']='forged source';(out/'review.json').write_text(json.dumps(r))
   with self.assertRaises(ValueError):import_review(out)
   self.assertFalse(destination.exists())
