#!/usr/bin/env python3
"""Prepare an amd64 offline library on a development Docker engine."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SYSBOX_URL = 'https://github.com/nestybox/sysbox/releases/download/v0.7.1/sysbox-ce_0.7.1.linux_amd64.deb'
SYSBOX_SHA = '9d6d5484f980d0a17f86c492c1262015c2afb66280bdb97215b79fde6a0261c5'
FUSE_URL = 'https://deb.debian.org/debian/pool/main/f/fuse3/fuse3_3.14.0-4_amd64.deb'
FUSE_SHA = '63b97d9b9acf9e8346ba59e87aa36a47205f05050808f8e9087dca603fd07ab8'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', default='default')
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    subprocess.run(['python3', str(ROOT/'tools/check_public_tree.py')], check=True)
    sub = ROOT/'upstream/ethical-hacking-docker-labs'
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD:upstream/ethical-hacking-docker-labs'], cwd=ROOT).strip()
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=sub).strip()
    if actual != expected or subprocess.check_output(['git', 'status', '--porcelain'], cwd=sub):
        raise SystemExit('Use the clean, pinned upstream dependency.')
    out = ROOT/'artifacts'
    out.mkdir(exist_ok=True)
    env = dict(os.environ, DOCKER_DEFAULT_PLATFORM='linux/amd64', COMPOSE_PARALLEL_LIMIT='2')
    docker = ['docker', '--context', args.context]
    compose = docker+['compose', '-p', 'paper-vianden', '--profile', 'extended',
                      '-f', 'prototype/docker-compose.yml', '-f', 'compose.yaml']
    def run(argv, **kw):
        return subprocess.run(argv, cwd=ROOT, env=env, check=True, **kw)
    if not args.skip_build:
        for target, tag in [('target-base', 'target-base'), ('workstation', 'workstation-base')]:
            run(docker+['build', '--platform=linux/amd64', '--target', target,
                        '-t', 'paper-vianden/'+tag+':local', 'prototype'])
        run(compose+['build'])
    cfg = json.loads(run(compose+['config', '--format', 'json'], capture_output=True, text=True).stdout)
    external = [name for name, service in cfg['services'].items()
                if not service['image'].startswith('paper-vianden/')]
    run(compose+['pull']+external)
    run(docker+['build', '--platform=linux/amd64', '-f', 'Dockerfile.envelope',
                '-t', 'paper-vianden/envelope:local', '.'])
    images = sorted({service['image'] for service in cfg['services'].values()})
    for filename, selected in [('targets.tar.gz', images), ('envelope.tar.gz', ['paper-vianden/envelope:local'])]:
        print('Saving', filename, flush=True)
        with gzip.open(out/filename, 'wb', compresslevel=1) as dest:
            child = subprocess.Popen(docker+['save']+selected, cwd=ROOT, env=env, stdout=subprocess.PIPE)
            shutil.copyfileobj(child.stdout, dest, length=1024*1024)
            if child.wait():
                raise RuntimeError('Image export failed')
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).split(b'\0')
    with tarfile.open(out/'source.tar.gz', 'w:gz') as archive:
        for raw in files:
            if raw:
                name = raw.decode(); path = ROOT/name
                if path.is_file(): archive.add(path, arcname=name, recursive=False)
        for raw in subprocess.check_output(['git', 'ls-files', '-z'], cwd=sub).split(b'\0'):
            if raw:
                path = sub/raw.decode()
                if path.is_file(): archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    package = out/'sysbox.deb'
    if not package.exists():
        with urllib.request.urlopen(SYSBOX_URL) as source, package.open('wb') as dest:
            shutil.copyfileobj(source, dest)
    if sha(package) != SYSBOX_SHA:
        raise RuntimeError('Sysbox checksum mismatch')
    fuse = out/'fuse3.deb'
    if not fuse.exists():
        with urllib.request.urlopen(FUSE_URL) as source, fuse.open('wb') as dest:
            shutil.copyfileobj(source, dest)
    if sha(fuse) != FUSE_SHA:
        raise RuntimeError('FUSE helper checksum mismatch')
    manifest = {'architecture': 'amd64', 'services': len(cfg['services']),
                'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'images': images, 'files': {name: sha(out/name) for name in
                    ['targets.tar.gz', 'envelope.tar.gz', 'source.tar.gz', 'sysbox.deb', 'fuse3.deb']}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Prepared offline library under artifacts/. No range was started.')


if __name__ == '__main__':
    main()
