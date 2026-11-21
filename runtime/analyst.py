#!/usr/bin/env python3
"""Minimal analyst workspace: alerts, searchable logs, cases and handovers."""
import argparse
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

URL = 'http://telemetry.management:8088'
TOKEN = Path('/run/analyst/token')


def request(path, data=None):
    headers = {'Authorization': 'Bearer '+TOKEN.read_text().strip()}
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(URL+path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as response: return json.load(response)
    except urllib.error.HTTPError as error:
        try: detail=json.load(error).get('error',str(error))
        except (ValueError,AttributeError): detail=str(error)
        raise ValueError(detail) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inbox'); sub.add_parser('cases'); sub.add_parser('audit'); sub.add_parser('assets')
    logs = sub.add_parser('logs')
    for key in ('query', 'host', 'source', 'since', 'until'): logs.add_argument('--'+key, default='')
    logs.add_argument('--limit', type=int, default=100)
    case = sub.add_parser('case'); case.add_argument('id')
    create = sub.add_parser('open'); create.add_argument('title'); create.add_argument('--alert')
    for name in ('note', 'status', 'handover'):
        action = sub.add_parser(name); action.add_argument('case'); action.add_argument('--version', type=int, required=True)
        if name == 'note': action.add_argument('text'); action.add_argument('--event')
        elif name == 'status': action.add_argument('status', choices=('open','investigating','resolved','false-positive','escalated'))
        else:
            for key in ('summary','actions','next-steps'): action.add_argument('--'+key, required=True)
    firewall = sub.add_parser('firewall'); firewall.add_argument('action', choices=('status','block','unblock'))
    firewall.add_argument('--ip'); firewall.add_argument('--reason', default='')
    args = vars(parser.parse_args()); command = args.pop('command')
    if command in ('inbox','cases','audit','assets'): result = request('/analyst/'+command)
    elif command == 'logs': result = request('/analyst/logs?'+urllib.parse.urlencode(args))
    elif command == 'case': result = request('/analyst/case?'+urllib.parse.urlencode(args))
    else: result = request('/analyst/'+command, args)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError) as error: raise SystemExit(str(error))
