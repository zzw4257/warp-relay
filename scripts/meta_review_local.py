#!/usr/bin/env python3
"""One diagnostic request, with a terminal-only, process-local secret.

Does not read stored credentials or modify the shell, Keychain or .env files.
The human enters the key directly into a no-echo TTY, never as a command argument.
"""
import argparse
import getpass
import json
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from warp_relay.diagnosis import META_ENDPOINT, packet, review


def run(args, *, ask=input, hidden=getpass.getpass, request=review):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('Run in your own interactive terminal. Piped secret input is not supported.')
    p = packet(args.case, args.version)
    print(f'Warp Relay · {p["case_id"]} / {p["version"]}\nDestination: {META_ENDPOINT}')
    print('One request only. Public kernel evidence; at most 4096 output tokens. No retry or automatic top-up.')
    print('The key stays in this Python process; it is not saved or passed to Codex. Close the process to discard it.')
    model = ask('Team-enabled Meta model ID: ').strip()
    if not re.fullmatch(r'[A-Za-z0-9._:/-]{1,100}', model):
        raise ValueError('Use the exact model ID enabled for your team.')
    print('This tool cannot verify your balance or enforce a dollar cap. Confirm available credits in Billing first.')
    if ask('Authorize this one request using existing credits? Type USE EXISTING CREDITS: ').strip() != 'USE EXISTING CREDITS':
        print('Cancelled. No key requested and no request sent.')
        return None
    # Fail closed rather than falling back to echoed input on an unsupported TTY.
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        key = hidden('New Meta API key (hidden; do not paste into chat): ').strip()
    if not key or any(c.isspace() for c in key):
        raise ValueError('Empty or malformed input. No request sent.')
    out = ROOT / 'runs' / ('meta-review-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    try:
        result = request(args.case, out, args.version, model, True, True, api_key=key)
    finally:
        # Python cannot promise physical zeroization of immutable strings.
        key = None
    status = result['model']['status']
    print(json.dumps({'status': status, 'calls_attempted': result['receipt']['calls_attempted'],
                      'record': str(out), 'automatic_retry': False}, indent=2))
    if status == 'received_validated':
        print('Response validated. Give Codex the record path above to inspect and import; never the key.')
    else:
        print('Stop here. The receipt records whether a request was attempted. Do not blindly retry.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', default='tma')
    parser.add_argument('--version', type=int)
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        # Do not echo user inputs or exception strings that might contain a secret.
        print('Stopped. No secret is saved. Inspect any request receipt before retrying.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
