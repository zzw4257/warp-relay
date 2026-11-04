import argparse
import contextlib
import io
import os
import unittest
from unittest.mock import patch

import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('meta_review_local',Path(__file__).resolve().parents[1]/'scripts/meta_review_local.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
run=module.run


class LocalSecretTests(unittest.TestCase):
    def test_cancel_before_key_or_request(self):
        answers=iter(['team-model','no'])
        def fail(*a,**k): self.fail('Should not request key or network')
        with contextlib.redirect_stdout(io.StringIO()),patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True):
            self.assertIsNone(run(argparse.Namespace(case='tma',version=None),ask=lambda _:next(answers),hidden=fail,request=fail))

    def test_pipes_refused_before_prompt(self):
        with patch('sys.stdin.isatty',return_value=False),self.assertRaises(ValueError):
            run(argparse.Namespace(case='tma',version=None))

    def test_process_local_secret_is_never_exported_or_echoed(self):
        secret='synthetic-test-value-only';answers=iter(['team-model','USE EXISTING CREDITS']);output=io.StringIO();calls=[]
        before=dict(os.environ)
        def request(*a,**k):
            self.assertEqual(k['api_key'],secret);self.assertEqual(dict(os.environ),before);calls.append(a)
            return {'model':{'status':'received_validated'},'receipt':{'calls_attempted':1}}
        with contextlib.redirect_stdout(output),patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True):
            run(argparse.Namespace(case='tma',version=None),ask=lambda _:next(answers),hidden=lambda _:secret,request=request)
        self.assertEqual(len(calls),1);self.assertNotIn(secret,output.getvalue());self.assertEqual(dict(os.environ),before)

