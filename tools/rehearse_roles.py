#!/usr/bin/env python3
"""Basic native checks of human mode selection and external team SSH roles."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import shlex
import tarfile
import time
from demo_client import ROOT, SSHClient


def main():
    c=SSHClient();report={'checks':{},'modes':[],'scripted_clients':True}
    out=ROOT/'local'/('role-rehearsal-'+time.strftime('%Y%m%dT%H%M%S'))
    out.mkdir(parents=True,mode=0o700)
    token=c.json('human','range claim role-mode-acceptance --minutes 35')['token']
    def control(command):return c.json('human','range '+command+' --token '+shlex.quote(token),timeout=240)
    def ready():
        for _ in range(180):
            s=c.json('human','range status')
            if s['phase']=='ready':return s
            time.sleep(3)
        raise RuntimeError('Startup did not finish')
    try:
        rival=c.run('human','range claim competing-person',check=False)
        assert rival.returncode!=0
        report['checks']['exclusive_human_ownership']=True
        for index,(attacker,normal) in enumerate((('scripted','scripted'),('llm','scripted'),('llm','llm'),('scripted','llm'))):
            action='start' if index==0 else 'reset'
            control(action+' --seed 42 --clock-speed 600 --attacker '+attacker+' --normal-traffic '+normal)
            state=ready();assert state['modes']['attacker']==attacker and state['modes']['normal_traffic']==normal,state
            with ThreadPoolExecutor(max_workers=3) as pool:
                jobs=[pool.submit(c.run,'blue',x) for x in ('hostname','id -u','evidence status')]
                responses=[j.result().stdout for j in jobs]
            assert responses[0].strip()=='defender' and responses[1].strip()=='0'
            assert json.loads(responses[2])['last_poll']>0
            # Every reset must replace the blue findings volume.
            assert c.run('blue','test ! -e /var/lib/soc-ai/reset-marker').returncode==0
            c.run('blue','touch /var/lib/soc-ai/reset-marker')
            ordinary=c.json('blue','evidence availability');assert ordinary['ok'],ordinary
            visible=c.json('human','observe status')
            if attacker=='llm':
                assert visible['story']['state']=='external' and visible['story']['events_processed']==0,visible
                assert c.run('red','hostname').stdout.strip()=='red'
                c.run('red',"umask 077; printf 'red role test\\n' > /var/lib/soc-ai/red-check.txt")
                assert c.run('red','test ! -e /root/.ssh/id_ed25519 && test ! -e /var/log/range-instructor && test ! -e /var/run/docker.sock').returncode==0
            else:
                assert c.run('red','hostname',check=False).returncode!=0
                assert visible['story']['state'] in ('running','complete'),visible
            if normal=='llm':
                assert visible['employees']['mode']=='external' and not visible['employees']['successes'],visible
                assert c.run('green','hostname').stdout.strip()=='green'
                assert c.run('green','id -u').stdout.strip()=='65534'
                result=c.json('green','green-work all');assert result['ok'],result
                c.run('green',"umask 077; printf 'green role test\\n' > /var/lib/soc-ai/green-check.txt")
                assert c.run('green','test ! -e /root/.ssh/id_ed25519 && test ! -e /var/log/range-instructor && test ! -e /var/run/docker.sock').returncode==0
                time.sleep(3)
                again=c.json('human','observe status')
                assert not again['employees']['successes'],again
                assert c.run('human','observe green --tail 5').stdout.strip()
            else:
                assert visible['employees']['mode']!='external'
                assert c.run('green','hostname',check=False).returncode!=0
            for role in ('blue',)+(('red',) if attacker=='llm' else ())+(('green',) if normal=='llm' else ()):
                assert c.run(role,'range stop --token '+shlex.quote(token),check=False).returncode!=0
            white=c.run('human',"id -u; grep '^CapEff' /proc/self/status").stdout
            assert white.splitlines()[0]=='65534' and '0000000000000000' in white,white
            exported=control('export');blob=c.run('human','range download '+shlex.quote(exported['id']),binary=True).stdout
            with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
                names=set(archive.getnames());manifest=json.load(archive.extractfile('manifest.json'))
                assert 'findings/reset-marker' in names and not manifest['omitted'],manifest
                if attacker=='llm':assert 'red-findings/red-check.txt' in names,names
                if normal=='llm':assert 'green-findings/green-check.txt' in names and 'green/activity.jsonl' in names,names
            archive_path=out/(exported['id']+'.tar.gz');archive_path.write_bytes(blob);archive_path.chmod(0o600)
            report['modes'].append({'attacker':attacker,'normal_traffic':normal,'all_eight_ordinary_workflows':True,'archive':str(archive_path),'export_omissions':manifest['omitted']})
            print('Passed mode:',attacker,normal,flush=True)
        report['checks'].update(parallel_blue_tools=True,reset_clears_findings=True,role_mode_gates=True,agents_cannot_control_lifecycle=True,white_unprivileged=True,private_role_findings_exported=True)
        report['success']=True
    finally:
        try:report['release']=control('release')
        finally:
            (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'report.json').chmod(0o600)
            print(json.dumps({'report':str(out/'report.json'),'success':report.get('success',False),'checks':report['checks']}),flush=True)
    for role in ('blue','red','green'):
        assert c.run(role,'hostname',check=False).returncode!=0,'Login restarted a stopped exercise'
    state=c.json('human','range status');assert not state['running'] and not state['lease_active'],state
    print('All roles stopped; logins did not restart the exercise.',flush=True)


if __name__=='__main__':main()
