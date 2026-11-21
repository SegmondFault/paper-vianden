#!/usr/bin/env python3
"""Offline Docker integration rehearsal in a unique project; always tears it down.

Requires the prepared local images. Does not build, pull or touch other projects.
Run: python3 tests/smoke_simulation.py
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tempfile
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ('web-01', 'app-01', 'vpn-gw-01', 'file-01', 'db-01', 'ldap',
            'mail', 'mail-sink', 'ftp', 'scenario-sink', 'activity', 'scenario-runner', 'defender', 'white','telemetry')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-rosetta', action='store_true',
                        help='Report, but tolerate FTP/IMAP failures proven to be Rosetta errors')
    parser.add_argument('--containment',action='store_true',help='Contain file-host fixture access and verify ordinary work survives')
    args = parser.parse_args()
    project = 'pv-story-test-'+uuid.uuid4().hex[:10]
    with tempfile.TemporaryDirectory(prefix='pv-story-') as tmp:
        directory = Path(tmp)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(directory/'blue')], check=True)
        config = json.loads(subprocess.check_output(['docker', 'compose', '--profile', 'extended',
            '-f', str(ROOT/'prototype/docker-compose.yml'), '-f', str(ROOT/'compose.yaml'),
            'config', '--format', 'json'], cwd=ROOT))
        config.pop('name', None)
        config['services'] = {name: config['services'][name] for name in SERVICES}
        for resources in ('networks', 'volumes'):
            for resource in config.get(resources, {}).values():
                resource.pop('name', None)
        for service in config['services'].values():
            service.pop('build', None)
            service.pop('profiles', None)
            for volume in service.get('volumes', []):
                if volume.get('target') in ('/run/blue-team.pub', '/run/entry.pub'):
                    volume['source'] = str(directory/'blue.pub')
                elif volume.get('target') == '/root/.ssh/id_ed25519':
                    volume['source'] = str(directory/'blue')
        config['services']['activity']['environment']['PV_CLOCK_SPEED'] = '600' if args.containment else '3600'
        config['services']['activity']['environment']['PV_SEED'] = '42'
        path = directory/'compose.json'
        path.write_text(json.dumps(config))
        compose = ['docker', 'compose', '-p', project, '-f', str(path)]

        def run(*args, capture=False, check=True):
            return subprocess.run(compose+list(args), check=check, text=True,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None)

        def inside(service, source):
            return run('exec', '-T', service, 'python3', '-c', source, capture=True).stdout

        try:
            run('up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '180',
                '--scale', 'activity=0', '--scale', 'scenario-runner=0')
            # LDAP has no image healthcheck; wait for its bootstrap, not just PID 1.
            for _ in range(60):
                seeded = run('exec', '-T', 'ldap', 'ldapsearch', '-x', '-H', 'ldap://127.0.0.1',
                    '-b', 'dc=enum,dc=lab', '(uid=adminservice)', 'uid', capture=True, check=False)
                if 'uid: adminservice' in seeded.stdout:
                    break
                time.sleep(2)
            else:
                run('logs', '--no-color', '--tail', '60', 'ldap')
                raise RuntimeError('LDAP fixtures did not become anonymously readable')
            run('exec','-T','web-01','sh','-c',
                'rm -f /var/log/nginx/access.log /var/log/nginx/error.log; touch /var/log/nginx/access.log /var/log/nginx/error.log; nginx -s reopen')
            run('up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--wait', '--wait-timeout', '90',
                '--scale', 'activity=1', '--scale', 'scenario-runner=1', 'activity', 'scenario-runner')
            # Diagnostic protocol requests don't depend on the random employee mix.
            output = run('exec', '-T', 'activity', 'python3', '/opt/paper-vianden/runtime/activity.py',
                         '--once', 'all', capture=True, check=False).stdout
            diagnostics = [json.loads(line) for line in output.splitlines()]
            assert len(diagnostics) == 8, output
            emulation_failures = []
            for event in diagnostics:
                if event['result'] == 'ok':
                    continue
                target = {'mail': 'mail', 'ftp': 'ftp'}.get(event['activity'])
                logged = run('logs', '--no-color', target, capture=True) if target else None
                logs = (logged.stdout+logged.stderr) if logged else ''
                if args.allow_rosetta and target and 'rosetta error:' in logs+event.get('detail', ''):
                    emulation_failures.append(event['activity'])
                else:
                    raise AssertionError(event)
            contained=False
            for _ in range(120):
                state = json.loads(inside('scenario-runner',
                    "from pathlib import Path; print(Path('/var/log/range-instructor/story-status.json').read_text())"))
                if state['state'] == 'complete':
                    break
                if args.containment and not contained and 'lateral' in state['grants']:
                    # The same defender-side SSH command an external SOC tool uses.
                    run('exec','-T','defender','ssh','file-01.internal','passwd -l devuser')
                    inside('defender',"from pathlib import Path; Path('/var/lib/soc-ai/response.json').write_text('{\"action\":\"locked file-host fixture account\"}')")
                    contained=True
                time.sleep(2)
            else:
                raise RuntimeError('Story did not complete within 240 real seconds')
            assert state['objective'] == ('incomplete' if args.containment else 'complete'), state
            if args.containment:
                assert contained and state['results']['blocked']>0,state
                after=run('exec','-T','activity','python3','/opt/paper-vianden/runtime/activity.py','--once','all',capture=True,check=False).stdout
                after=list(map(json.loads,after.splitlines()))
                baseline={e['activity']:e['result'] for e in diagnostics}
                assert all(e['result']=='ok' or baseline[e['activity']]=='error' for e in after),after
            else: assert state['results']['error']==0,state
            assert state['events_processed'] == 47, state
            journal = inside('scenario-runner',
                "from pathlib import Path; print(Path('/var/log/range-instructor/story.jsonl').read_text())")
            events = [json.loads(line) for line in journal.splitlines() if line]
            assert len([event for event in events if event.get('activity') == 'dns-exfil']) == 32
            sink_journal = inside('scenario-sink',
                "from pathlib import Path; print(Path('/var/log/range-instructor/scenario-sink.jsonl').read_text())")
            dns = [event for event in map(json.loads, filter(str.strip, sink_journal.splitlines()))
                   if event['protocol'] == 'dns' and event['query'].endswith('.telemetry.range.test')]
            file_id = run('ps', '-q', 'file-01', capture=True).stdout.strip()
            file_networks = json.loads(subprocess.check_output(['docker', 'inspect', file_id]))[0]['NetworkSettings']['Networks']
            file_ips = {network['IPAddress'] for network in file_networks.values()}
            assert len(dns) == (0 if args.containment else 32) and all(event['source'] in file_ips for event in dns), dns
            assert state['seed'] == 42
            inside('defender', "from pathlib import Path; "
                "assert not Path('/opt/paper-vianden/runtime/scenario.py').exists(); "
                "assert not Path('/var/log/range-instructor').exists(); "
                "assert not Path('/var/log/simulated-users/story.jsonl').exists(); "
                "assert Path('/var/log/dns/queries.jsonl').is_file()")
            raw = inside('defender', "from pathlib import Path; print(Path('/var/log/dns/queries.jsonl').read_text())")
            observed = list(map(json.loads, filter(str.strip, raw.splitlines())))
            assert any(event['query'].endswith('.office.range.test') for event in observed)
            assert all(not {'activity', 'phase', 'scheduled_seconds', 'marker'} & event.keys() for event in observed)
            run('exec', '-T', 'white', 'python3', '/usr/local/bin/observe', '--check')
            observed_status = json.loads(run('exec', '-T', 'white', 'python3',
                '/usr/local/bin/observe', 'status', capture=True).stdout)
            assert observed_status['story']['objective'] == ('incomplete' if args.containment else 'complete')
            feed=json.loads(run('exec','-T','defender','python3','/usr/local/bin/evidence','tail','--limit','1000',capture=True).stdout)
            health=json.loads(run('exec','-T','defender','python3','/usr/local/bin/evidence','flush',capture=True).stdout)
            assert not health['errors'],health
            assert feed['events'] and all('phase' not in e for e in feed['events']),feed
            assert any('Accepted password for devuser' in e['message'] for e in feed['events']),feed
            exported=subprocess.run(compose+['exec','-T','--user','0','white','python3','-c',
                (ROOT/'runtime/export_evidence.py').read_text()],check=True,capture_output=True).stdout
            with tarfile.open(fileobj=io.BytesIO(exported)) as archive:
                assert 'observations/events.jsonl' in archive.getnames()
                if args.containment:assert 'findings/response.json' in archive.getnames()
            inside('white', "import os; from pathlib import Path; "
                "assert os.geteuid() == 65534; "
                "assert not Path('/var/run/docker.sock').exists(); "
                "assert not os.access('/root/.ssh/id_ed25519', os.R_OK); "
                "assert os.statvfs('/var/log/range-instructor').f_flag & os.ST_RDONLY")
            for service in ('vpn-gw-01', 'file-01'):
                auth = inside(service, "from pathlib import Path; print(Path('/var/log/auth.log').read_text())")
                assert 'Accepted password for devuser' in auth, service
            sql = run('exec', '-T', 'db-01', 'env', 'MYSQL_PWD=S3cretDB!2024', 'mariadb', '-u', 'root',
                '-N', '-e', "SELECT COUNT(*) FROM mysql.general_log WHERE argument LIKE '/* report_export */%'",
                capture=True).stdout.strip()
            assert int(sql) >= 1, sql
            print(json.dumps({'project': project, 'employee_protocols_ok': sum(event['result'] == 'ok' for event in diagnostics),
                'rosetta_failures': emulation_failures,
                'story_events': state['events_processed'], 'dns_chunks_from_file_host': len(dns),
                'objective': state['objective'], 'seed': state['seed'], 'containment':args.containment,
                'central_feed_events':len(feed['events']),
                'blue_answer_key_absent': True, 'mixed_raw_dns_log': True, 'white_read_only': True,
                'sql_query_logged': True, 'ssh_auth_logged': True}))
        except BaseException as error:
            if isinstance(error, subprocess.CalledProcessError):
                print(error.stdout or '', error.stderr or '')
            run('logs', '--no-color', '--tail', '80', 'activity', 'scenario-runner', 'scenario-sink')
            raise
        finally:
            run('down', '--volumes', '--remove-orphans', '--timeout', '10')
        remaining = subprocess.check_output(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project='+project], text=True)
        assert not remaining.strip(), 'Test containers remained after teardown'
        for resource in ('volume', 'network'):
            remaining = subprocess.check_output(['docker', resource, 'ls', '-q', '--filter', 'label=com.docker.compose.project='+project], text=True)
            assert not remaining.strip(), f'Test {resource} remained after teardown'
        print('Disposable test containers, volumes and networks removed.')


if __name__ == '__main__':
    main()
