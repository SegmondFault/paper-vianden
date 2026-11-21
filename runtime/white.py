#!/usr/bin/env python3
"""Read-only white-team view; never mounted in the blue workstation."""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import time

ROOTS = (Path('/var/log/range-instructor'), Path('/var/log/simulated-users'), Path('/var/log/dns'))
FILES = {'story': ROOTS[0]/'story.jsonl', 'activity': ROOTS[1]/'activity.jsonl',
         'dns':ROOTS[2]/'queries.jsonl','markers':ROOTS[0]/'scenario-sink.jsonl',
         'green':Path('/var/log/green-users/activity.jsonl')}


def load(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {'state': 'waiting'}


def status():
    return {'access': 'read-only', 'employees': load(ROOTS[1]/'status.json'),
            'story': load(ROOTS[0]/'story-status.json')}


def tail(path, count):
    try:
        with path.open() as source:
            return list(deque(source, maxlen=count))
    except FileNotFoundError:
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('view',nargs='?',choices=('status','story','activity','dns','markers','green','snapshot'),default='status')
    parser.add_argument('--tail', type=int, default=20)
    parser.add_argument('--watch', action='store_true', help='Refresh every two seconds; Ctrl-C to leave')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.tail <= 1000:
        parser.error('--tail must be between 1 and 1000')
    if args.check:
        if any(not path.is_dir() or not os.statvfs(path).f_flag & os.ST_RDONLY for path in ROOTS):
            raise SystemExit('Observation journals must be mounted read-only')
        print('White workstation is read-only and ready.')
        return
    while True:
        if args.view == 'status':
            print(json.dumps(status(), indent=2), flush=True)
        elif args.view == 'snapshot':
            print(json.dumps({'status': status(), 'journals': {
                name: [json.loads(line) for line in tail(path, args.tail) if line.strip()]
                for name, path in FILES.items()}}, indent=2), flush=True)
        else:
            print(''.join(tail(FILES[args.view], args.tail)), end='', flush=True)
        if not args.watch:
            return
        time.sleep(2)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
