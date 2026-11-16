#!/usr/bin/env python3
"""Register one inbound PBX call with OIM and pass its UUID to the dialplan."""

import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid


CONFIG_PATH = '/etc/oim/pbx-bridge.env'
OIM_ENDPOINT = 'http://127.0.0.1:8787/api/pbx/bridge-calls'


def read_secret():
    try:
        with open(CONFIG_PATH, encoding='utf-8') as config:
            for line in config:
                name, separator, value = line.partition('=')
                if separator and name.strip() == 'OIM_PBX_SHARED_SECRET':
                    return value.strip()
    except OSError:
        return ''
    return ''


def set_variable(name, value):
    if not re.fullmatch(r'[A-Z0-9_]+', name) or not re.fullmatch(r'[A-Za-z0-9-]*', value):
        return
    sys.stdout.write(f'SET VARIABLE {name} {value}\n')
    sys.stdout.flush()
    sys.stdin.readline()


def main():
    # Consume the AGI environment block before sending any AGI commands.
    while True:
        line = sys.stdin.readline()
        if not line or line in ('\n', '\r\n'):
            break
    called = sys.argv[1] if len(sys.argv) > 1 else ''
    caller = sys.argv[2] if len(sys.argv) > 2 else ''
    secret = read_secret()
    call_id = str(uuid.uuid4())
    if not secret or not called or len(called) > 100 or len(caller) > 100:
        set_variable('OIM_BRIDGE_ERROR', '1')
        return
    body = json.dumps({'call_id': call_id, 'called_number': called, 'caller': caller}).encode()
    request = urllib.request.Request(OIM_ENDPOINT, data=body, headers={
        'Content-Type': 'application/json',
        'X-OIM-PBX-Secret': secret,
    }, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            result = json.loads(response.read(8192))
        if not result.get('ok') or result.get('call_id') != call_id:
            raise ValueError('registration failed')
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
        set_variable('OIM_BRIDGE_ERROR', '1')
        return
    set_variable('OIM_BRIDGE_UUID', call_id)
    set_variable('OIM_BRIDGE_ERROR', '0')


if __name__ == '__main__':
    main()
