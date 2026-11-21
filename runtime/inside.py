#!/usr/bin/env python3
"""Start the prepared, network-disconnected inner range. No downloads/builds."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/opt/paper-vianden')
COMPOSE = ['docker', 'compose', '-p', 'paper-vianden', '--profile', 'extended',
           '-f', str(ROOT/'prototype/docker-compose.yml'), '-f', str(ROOT/'compose.yaml')]


def run(args, **kw):
    return subprocess.run(args, cwd=ROOT, check=True, **kw)


def main():
    daemon = subprocess.Popen(['dockerd', '--host=unix:///var/run/docker.sock',
                               '--storage-driver=overlay2'], stdout=open('/tmp/dockerd.log', 'w'),
                              stderr=subprocess.STDOUT)
    try:
        for _ in range(120):
            if daemon.poll() is not None:
                raise RuntimeError(Path('/tmp/dockerd.log').read_text()[-5000:])
            if subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError('Inner Docker did not become ready')
        print('Loading offline target images...', flush=True)
        run(['docker', 'load', '-i', '/library/targets.tar.gz'], stdout=subprocess.DEVNULL)
        # Docker's archive format does not retain repository digest references.
        # Restore a stable local alias from the pinned image's config identity.
        for alias, source in json.loads((ROOT/'runtime/image-sources.json').read_text()).items():
            run(['docker', 'tag', source['config_id'], alias])
        run(['python3', str(ROOT/'prototype/range'), 'init'])
        print('Starting the seeded service network...', flush=True)
        run(COMPOSE+['up', '-d', '--no-build', '--pull', 'never', '--wait',
                     '--wait-timeout', '180', '--scale', 'activity=0', '--scale', 'scenario-runner=0'])
        run(COMPOSE+['exec', '-T', 'defender', 'python3',
                     '/opt/paper-vianden/runtime/initialise.py'])
        run(COMPOSE+['exec', '-T', 'defender', 'python3',
                     '/opt/paper-vianden/runtime/check.py'])
        # Keep the target config editable by defenders; enable real SMB auth logs.
        configure_samba = ("from pathlib import Path; p=Path('/etc/samba/smb.conf'); "
                           "p.write_text(p.read_text().replace('[global]', "
                           "'[global]\\n   log level = 1 auth_audit:3', 1))")
        run(COMPOSE+['exec', '-T', 'file-01', 'python3', '-c', configure_samba])
        run(COMPOSE+['exec', '-T', 'file-01', 'smbcontrol', 'all', 'reload-config'])
        print('Starting simulated users and the intrusion storyline...', flush=True)
        run(COMPOSE+['up', '-d', '--no-build', '--pull', 'never', '--no-deps',
                     '--scale', 'activity=1', '--scale', 'scenario-runner=1',
                     '--wait', '--wait-timeout', '120', 'activity', 'scenario-runner'])
        run(COMPOSE+['exec', '-T', 'defender', 'python3',
                     '/opt/paper-vianden/runtime/check.py', '--activity-only'])
        run(COMPOSE+['exec', '-T', 'scenario-runner', 'python3',
                     '/opt/paper-vianden/runtime/scenario_runner.py', '--check'])
        Path('/tmp/paper-vianden-ready').write_text('ready\n')
        print(json.dumps({'event': 'ready', 'services': 25}), flush=True)
        while daemon.poll() is None:
            time.sleep(1)
        raise RuntimeError('Inner Docker stopped unexpectedly')
    except BaseException:
        failed = subprocess.run(COMPOSE+['ps', '-a', '--status', 'exited', '--services'],
                                cwd=ROOT, text=True, stdout=subprocess.PIPE)
        for service in failed.stdout.split():
            subprocess.run(COMPOSE+['logs', '--no-color', '--tail', '50', service], cwd=ROOT)
        raise
    finally:
        if daemon.poll() is None:
            daemon.terminate()
            try:
                daemon.wait(timeout=15)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait()


if __name__ == '__main__':
    main()
