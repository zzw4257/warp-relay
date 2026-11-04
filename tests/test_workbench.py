import hashlib
import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from warp_relay.core import RunCancelled, Verifier, run_process, write_json
from warp_relay.workbench import Jobs, Server, preset, safe_file, validate_submission
from warp_relay.providers import OfflineProvider
from warp_relay.runner import ROOT, run


def wait_until(test, timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if test(): return
        time.sleep(.02)
    raise AssertionError('Timed out waiting for actual worker state')


class InputBoundaryTests(unittest.TestCase):
    def test_atomic_json_is_always_parseable_during_concurrent_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'summary.json';write_json(path,{'version':0})
            def write_versions():
                for version in range(1,101):write_json(path,{'version':version,'payload':'a'*10000})
            writer=threading.Thread(target=write_versions);writer.start()
            while writer.is_alive():self.assertIn('version',json.loads(path.read_text()))
            writer.join();self.assertEqual(json.loads(path.read_text())['version'],100)

    def test_example_can_load_from_packaged_snapshot_without_vendor_checkout(self):
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            shutil.copytree(ROOT/'examples/pytorch_weightnorm',root/'examples/pytorch_weightnorm')
            target=root/'evidence/round4-20261031/weightnorm-cpu/inputs';target.mkdir(parents=True)
            original=ROOT/'evidence/round4-20261031/weightnorm-cpu/inputs/original.ptx'
            shutil.copyfile(original,target/'original.ptx')
            with patch('warp_relay.workbench.ROOT',root):
                self.assertEqual(preset('weightnorm')['kernel'],original.read_text())

    def test_invalid_inputs_do_not_become_paths_or_execution_options(self):
        value=preset('weightnorm')
        for extra in ['reference','reference_binding','command','provider','api_key','allow_model_call']:
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                validate_submission({**value,extra:'/private/secret'})
        for key,replacement in [('kernel','../../private/code.ptx'),('input','/private/input.json'),('iterations',True),('timeout',float('inf'))]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_submission({**value,key:replacement})
        bad=json.loads(json.dumps(value));bad['input']['launch']['grid_dim']=[1000000,1,1]
        with self.assertRaises(ValueError):validate_submission(bad)
        bad=json.loads(json.dumps(value));bad['input']['entry']='wrong_entry'
        with self.assertRaisesRegex(ValueError,'does not match'):validate_submission(bad)

    def test_artifact_traversal_and_symlink_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);base=root/'run';base.mkdir();(root/'outside').write_text('private')
            (base/'escape').symlink_to(root/'outside')
            for name in ['../outside','/etc/passwd','escape']:
                with self.subTest(name=name),self.assertRaises((ValueError,FileNotFoundError)):
                    safe_file(base,name)

    def test_cancellation_terminates_owned_descendant_group_and_keeps_output(self):
        cancel=threading.Event()
        timer=threading.Timer(.2,cancel.set);timer.start()
        code="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)']); print(p.pid,flush=True); time.sleep(20)"
        started=time.monotonic()
        try:
            with self.assertRaises(RunCancelled) as caught:
                run_process([sys.executable,'-c',code],10,cancel_event=cancel)
            self.assertGreater(int(caught.exception.stdout.strip()),0)
            self.assertLess(time.monotonic()-started,3)
        finally:timer.cancel()


class RealWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.jobs=Jobs(Path(self.temporary.name)/'jobs')
    def tearDown(self):
        self.jobs.close();self.temporary.cleanup()

    def test_second_state_owner_cannot_change_first_owners_live_evidence(self):
        key='b'*16;folder=self.jobs.root/key;folder.mkdir()
        write_json(folder/'job.json',{'id':key,'state':'running','phase':'verifying_baseline','name':'live','created_at':'2026-10-31T00:00:00+00:00'})
        before=(folder/'job.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'already open'):Jobs(self.jobs.root)
        self.assertEqual((folder/'job.json').read_bytes(),before)

    def test_cancel_at_provider_return_is_not_lost_as_exhaustion(self):
        cancel=threading.Event()
        class CancellingProvider(OfflineProvider):
            def propose(self,*args):cancel.set();return None
        out=Path(self.temporary.name)/'provider-cancel'
        result=run(ROOT/'examples/pytorch_weightnorm/runtime-task.json',out,CancellingProvider(),cancel_event=cancel)
        self.assertEqual(result['stop_reason'],'cancelled')
        self.assertEqual(result['selected'],'000-baseline')

    def test_cancel_at_verifier_return_cannot_commit_candidate(self):
        cancel=threading.Event();original=Verifier.run
        def return_with_cancel(verifier,kernel,*args):
            raw=original(verifier,kernel,*args)
            if '001-candidate' in kernel.parts:cancel.set()
            return raw
        out=Path(self.temporary.name)/'native-return-cancel'
        with patch.object(Verifier,'run',return_with_cancel):
            result=run(ROOT/'examples/neighbor_exchange/task.json',out,OfflineProvider(),cancel_event=cancel)
        self.assertEqual(result['stop_reason'],'cancelled')
        self.assertIsNone(result['selected'])
        self.assertTrue((out/'001-candidate/verification/result.json').is_file())

    def test_real_public_run_and_retry_keep_independent_evidence(self):
        job=self.jobs.submit(preset('weightnorm'));key=job['id']
        wait_until(lambda:self.jobs.items[key]['state']=='completed')
        view=self.jobs.view(key)
        self.assertEqual([r['result'] for r in view['rounds']],['race_free','potential_race','potential_race','potential_race','race_free'])
        self.assertEqual(view['summary']['selected'],'004-candidate')
        self.assertFalse(view['summary']['model_executed']);self.assertFalse(view['summary']['gpu_executed'])
        self.assertTrue(view['rounds'][4]['verification']['assumption_dependent'])
        self.assertTrue(any(e['phase']=='verifying_candidate' for e in view['job']['events']))
        old=(self.jobs.root/key/'run/summary.json').read_bytes()
        before=(self.jobs.root/key/'job.json').read_bytes()
        retry=self.jobs.retry(key)
        self.assertNotEqual(retry['id'],key);self.assertEqual(retry['retry_of'],key)
        wait_until(lambda:self.jobs.items[retry['id']]['state']=='completed')
        self.assertEqual(old,(self.jobs.root/key/'run/summary.json').read_bytes())
        self.assertEqual(before,(self.jobs.root/key/'job.json').read_bytes())

    def test_real_unsupported_is_completed_and_inconclusive_without_selection(self):
        job=self.jobs.submit(preset('unsupported'));key=job['id']
        wait_until(lambda:self.jobs.items[key]['state']=='completed')
        view=self.jobs.view(key)
        self.assertEqual(view['job']['outcome'],'inconclusive')
        self.assertEqual(view['rounds'][0]['result'],'unsupported')
        self.assertIsNone(view['summary']['selected'])

    def test_cancel_real_native_analysis_and_continue_queue(self):
        value=preset('weightnorm');value['input']['launch']['grid_dim']=[64,1,1]
        value['input']['launch']['block_dim']=[1024,1,1]
        value['input']['launch']['dynamic_shared_bytes']=4096
        key=self.jobs.submit(value)['id']
        wait_until(lambda:self.jobs.items[key]['phase']=='verifying_baseline')
        self.jobs.cancel(key)
        wait_until(lambda:self.jobs.items[key]['state']=='cancelled')
        self.assertIsNone(self.jobs.view(key)['summary']['selected'])
        next_key=self.jobs.submit(preset('repair'))['id']
        wait_until(lambda:self.jobs.items[next_key]['state']=='completed')
        self.assertEqual(self.jobs.view(next_key)['summary']['selected'],'001-candidate')
        self.assertIn('proposed repair',self.jobs.view(next_key)['rounds'][1]['reason'])

    def test_restart_marks_abandoned_job_interrupted_without_rerun(self):
        key='a'*16;folder=self.jobs.root/key;folder.mkdir()
        write_json(folder/'job.json',{'id':key,'state':'running','phase':'verifying_baseline','name':'abandoned','created_at':'2026-10-31T00:00:00+00:00'})
        self.jobs.close();self.jobs=Jobs(self.jobs.root)
        self.assertEqual(self.jobs.items[key]['state'],'interrupted')
        self.assertFalse((folder/'run').exists())

    def test_cancel_after_baseline_preserves_last_accepted_artifact(self):
        event=threading.Event()
        def checkpoint(value):
            if value['phase']=='baseline_verified':event.set()
        out=Path(self.temporary.name)/'partial'
        summary=run(ROOT/'examples/pytorch_weightnorm/runtime-task.json',out,OfflineProvider(),cancel_event=event,on_event=checkpoint)
        self.assertEqual(summary['stop_reason'],'cancelled')
        self.assertEqual(summary['selected'],'000-baseline')
        self.assertEqual((out/'selected.ptx').read_bytes(),(out/'inputs/original.ptx').read_bytes())

    def test_orchestration_failure_is_visible_and_retryable(self):
        with patch('warp_relay.workbench.run',side_effect=OSError('test-only injected worker failure')):
            key=self.jobs.submit(preset('repair'))['id']
            wait_until(lambda:self.jobs.items[key]['state']=='failed')
        self.assertIn('test-only injected worker failure',self.jobs.view(key)['job']['error'])
        retry=self.jobs.retry(key)['id']
        wait_until(lambda:self.jobs.items[retry]['state']=='completed')

    def test_http_rejects_cross_origin_unknown_actions_and_bad_payloads(self):
        server=Server(('127.0.0.1',0),self.jobs)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        def request(path,payload,origin=None,host=None):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            headers={'Content-Type':'application/json','X-Warp-Request':'1'}
            if origin:headers['Origin']=origin
            if host:headers['Host']=host
            conn.request('POST',path,json.dumps(payload),headers);response=conn.getresponse();data=response.read();conn.close()
            return response.status,json.loads(data)
        try:
            origin=f'http://127.0.0.1:{server.server_port}'
            self.assertEqual(request('/api/jobs',preset('repair'),'https://evil.example')[0],403)
            self.assertEqual(request('/api/jobs',preset('repair'),origin,'evil.example')[0],403)
            self.assertEqual(request('/api/jobs',{**preset('repair'),'command':'echo bad'},origin)[0],400)
            self.assertEqual(len(self.jobs.items),0)
            self.assertEqual(request('/api/validate',preset('repair'),origin)[0],200)
        finally:server.shutdown();server.server_close();worker.join()
