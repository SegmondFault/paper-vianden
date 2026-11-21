#!/usr/bin/env python3
"""Reject private documents and credentials before committing or pushing.

This checks Git objects, including force-added files. It complements provenance
review; it cannot determine whether arbitrary unlabelled prose is confidential.
Public upstream submodules remain separate repositories with their own history.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_EXTENSIONS = set('.doc .docx .xls .xlsx .ppt .pptx .pdf .pcap .pcapng .zip .7z .zst .img .raw .vmem .vmdk .qcow2 .pem .key'.split())
PRIVATE_DIRS = {'local', 'private', 'imports', 'evidence', 'datasets', 'state', 'runs'}
PATTERNS = [
    ('private key', re.compile(rb'(?m)^-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----\s*$')),
    ('GitHub credential', re.compile(rb'\b(?:gh[opusr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b')),
    ('classified material', re.compile(rb'(?im)^\s*(?:(?:classification|handling)\s*:\s*)?TLP[\s:-]*(?:AMBER(?:\+STRICT)?|RED)\b')),
]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT)]+list(args))


def check(entries):
    problems = []
    seen = set()
    for mode, kind, oid, name in entries:
        if kind != 'blob' or (oid, name) in seen:
            continue
        seen.add((oid, name))
        path = Path(name)
        if (path.suffix.lower() in BLOCKED_EXTENSIONS or PRIVATE_DIRS.intersection(path.parts)
                or path.parts[0] == 'notes'):
            problems.append((name, 'private document/data path'))
        if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example'):
            problems.append((name, 'environment credentials file'))
        data = git('cat-file', 'blob', oid)
        for reason, pattern in PATTERNS:
            if pattern.search(data):
                problems.append((name, reason))
    return problems, len(seen)


def staged():
    for record in git('ls-files', '--stage', '-z').split(b'\0'):
        if record:
            metadata, name = record.split(b'\t', 1)
            mode, oid, stage = metadata.decode().split()
            yield mode, 'commit' if mode == '160000' else 'blob', oid, name.decode()


def history():
    for revision in git('rev-list', '--all').decode().splitlines():
        for record in git('ls-tree', '-rz', revision).split(b'\0'):
            if record:
                metadata, name = record.split(b'\t', 1)
                mode, kind, oid = metadata.decode().split()
                yield mode, kind, oid, name.decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Check every version reachable from local refs')
    args = parser.parse_args()
    problems, count = check(history() if args.history else staged())
    if problems:
        for name, reason in sorted(set(problems)):
            print(f'BLOCKED: {name}: {reason}', file=sys.stderr)
        print('Private material must stay outside the public Git history. No matching contents are printed.', file=sys.stderr)
        return 1
    print(f'Public-source check passed ({count} file versions).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
