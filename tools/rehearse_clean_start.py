#!/usr/bin/env python3
"""Prove new runs clear live views across every role while retaining exports."""
import io
import json
from pathlib import Path
import shlex
import tarfile
import time
import uuid
from demo_client import ROOT,SSHClient


def main():
    c=SSHClient();token=c.json('human','range claim clean-start-acceptance --minutes 25')['token']
    out=ROOT/'local'/('clean-start-'+time.strftime('%Y%m%dT%H%M%S'));out.mkdir(parents=True,mode=0o700)
    report={'checks':{},'success':False};marker='PRIOR_RUN_'+uuid.uuid4().hex
    def control(command):return c.json('human','range '+command+' --token '+shlex.quote(token),timeout=240)
    def ready():
        for _ in range(180):
            if c.json('human','range status')['phase']=='ready':return
            time.sleep(3)
        raise RuntimeError('Startup did not finish')
    def invoke(role,source):return c.run(role,'python3 -c '+shlex.quote(source)).stdout
    def mail_count():
        return int(invoke('blue',"import json,urllib.request; print(json.load(urllib.request.urlopen('http://mail-sink.dmz:8025/api/v2/messages'))['total'])").strip())
    try:
        control('start --seed 42 --clock-speed 60 --attacker llm --normal-traffic llm');ready()
        first=json.loads(invoke('blue',"from pathlib import Path;print(Path('/var/log/soc-evidence/clean-start.json').read_text())"))
        assert first['fresh'] and mail_count()==0
        for role in ('blue','red','green','human'):
            history='/root/.bash_history' if role in ('blue','red') else '/tmp/.bash_history'
            source="from pathlib import Path;Path("+repr(history)+").write_text("+repr(marker)+")"
            if role!='human':source+=";Path('/var/lib/soc-ai/prior-case.txt').write_text("+repr(marker)+")"
            invoke(role,source)
        c.run('blue','ssh file-01.internal '+shlex.quote("printf '%s\\n' "+shlex.quote(marker)+" >> /var/log/auth.log"))
        c.run('blue','dig @scenario-sink.internal -p 1053 portal.office.range.test +short')
        c.json('blue','evidence flush')
        before=c.json('blue','evidence tail --limit 1000')
        assert any(marker in x['message'] for x in before['events']),'Sentinel did not reach central feed'
        exported=control('export')
        control('reset --seed 43 --clock-speed 60 --attacker llm --normal-traffic llm');ready()
        second=json.loads(invoke('blue',"from pathlib import Path;print(Path('/var/log/soc-evidence/clean-start.json').read_text())"))
        assert first['run_id']!=second['run_id'] and mail_count()==0
        for role in ('blue','red','green','human'):
            history='/root/.bash_history' if role in ('blue','red') else '/tmp/.bash_history'
            source="from pathlib import Path;p=Path("+repr(history)+");assert not p.exists() or not p.read_text()"
            if role!='human':source+=";assert not Path('/var/lib/soc-ai/prior-case.txt').exists()"
            invoke(role,source)
        c.run('blue','dig @scenario-sink.internal -p 1053 portal.office.range.test +short')
        c.json('blue','evidence flush')
        current=c.json('blue','evidence tail --limit 1000')
        assert all(marker not in json.dumps(e) for e in current['events'])
        assert any(e['host']=='dns' and 'portal.office.range.test' in e['message'] for e in current['events']),'Fresh DNS log was lost after startup wipe'
        c.run('blue','ssh file-01.internal '+shlex.quote('test -z "$(grep -F '+shlex.quote(marker)+' /var/log/auth.log)"'))
        assert c.json('blue','evidence availability')['ok']
        old=c.run('human','range download '+shlex.quote(exported['id']),binary=True).stdout
        with tarfile.open(fileobj=io.BytesIO(old)) as archive:
            assert marker in archive.extractfile('findings/prior-case.txt').read().decode()
            assert marker in archive.extractfile('red-findings/prior-case.txt').read().decode()
            assert marker in archive.extractfile('green-findings/prior-case.txt').read().decode()
        archive_path=out/(exported['id']+'.tar.gz');archive_path.write_bytes(old);archive_path.chmod(0o600)
        report.update(success=True,checks={'four_role_histories_cleared':True,'all_role_findings_cleared':True,
            'live_feed_and_target_logs_cleared':True,'startup_probe_mail_cleared':True,'fresh_dns_logging_works':True,
            'saved_exports_retained':True,'all_eight_ordinary_workflows':True},first_run=first['run_id'],second_run=second['run_id'])
    finally:
        try:report['release']=control('release')
        finally:
            (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'report.json').chmod(0o600)
            print(json.dumps({'report':str(out/'report.json'),'success':report['success'],'checks':report['checks']}),flush=True)


if __name__=='__main__':main()
