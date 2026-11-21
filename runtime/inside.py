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


def clear_live_evidence():
    """Run once after readiness probes, before telemetry and scenario actors."""
    program=(ROOT/'runtime/reset_evidence.py').read_text()
    terminals=('defender','red','green','white','web-01','vpn-gw-01','file-01',
               'app-01','admin-01','mail-01','ftp','mail','badge','bof')
    for service in terminals:
        run(COMPOSE+['exec','-T','--user','0',service,'python3','-c',program])
    config=json.loads(subprocess.check_output(COMPOSE+['config','--format','json'],cwd=ROOT))
    names=('activity-journal','story-journal','dns-evidence','soc-evidence','green-journal',
           'agent-findings','red-findings','green-findings')
    argv=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--cap-add','DAC_OVERRIDE']
    for name in names:
        argv+=['--mount','type=volume,src='+config['volumes'][name]['name']+',dst=/evidence/'+name]
    run(argv+['--entrypoint','python3','paper-vianden/toolbox:local','-c',program,'--volumes'])
    run(COMPOSE+['exec','-T','db-01','env','MYSQL_PWD=S3cretDB!2024','mariadb','-u','root','-e',
                 'SET GLOBAL general_log=OFF; TRUNCATE TABLE mysql.general_log; SET GLOBAL general_log=ON'])
    run(COMPOSE+['exec','-T','defender','python3','-c',
                 "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://mail-sink.dmz:8025/api/v1/messages',method='DELETE'),timeout=5).read()"])


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
                     '--wait-timeout','180','--scale','activity=0','--scale','scenario-runner=0','--scale','telemetry=0'])
        run(COMPOSE+['exec', '-T', 'defender', 'python3',
                     '/opt/paper-vianden/runtime/initialise.py'])
        run(COMPOSE+['exec', '-T', 'defender', 'python3',
                     '/opt/paper-vianden/runtime/check.py'])
        # Preserve web stdout logs as readable files for the central sensor.
        run(COMPOSE+['exec','-T','web-01','sh','-c',
                     "rm -f /var/log/nginx/access.log /var/log/nginx/error.log; touch /var/log/nginx/access.log /var/log/nginx/error.log; nginx -s reopen"])
        # Keep the target config editable by defenders; enable real SMB auth logs.
        configure_samba = ("from pathlib import Path; p=Path('/etc/samba/smb.conf'); "
                           "p.write_text(p.read_text().replace('[global]', "
                           "'[global]\\n   log level = 1 auth_audit:3', 1))")
        run(COMPOSE+['exec', '-T', 'file-01', 'python3', '-c', configure_samba])
        run(COMPOSE+['exec', '-T', 'file-01', 'smbcontrol', 'all', 'reload-config'])
        print('Clearing live terminal evidence and startup probe logs...',flush=True)
        clear_live_evidence()
        run(COMPOSE+['up','-d','--no-build','--pull','never','--no-deps','--scale','telemetry=1',
                     '--wait','--wait-timeout','120','telemetry'])
        print('Starting simulated users and the intrusion storyline...', flush=True)
        run(COMPOSE+['up', '-d', '--no-build', '--pull', 'never', '--no-deps',
                     '--scale', 'activity=1', '--scale', 'scenario-runner=1',
                     '--wait', '--wait-timeout', '120', 'activity', 'scenario-runner'])
        run(COMPOSE+['exec', '-T', 'defender', 'python3',
                     '/opt/paper-vianden/runtime/check.py', '--activity-only'])
        run(COMPOSE+['exec', '-T', 'scenario-runner', 'python3',
                     '/opt/paper-vianden/runtime/scenario_runner.py', '--check'])
        Path('/tmp/paper-vianden-ready').write_text('ready\n')
        print(json.dumps({'event':'ready','services':28}),flush=True)
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
