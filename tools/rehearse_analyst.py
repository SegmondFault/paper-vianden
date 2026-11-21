#!/usr/bin/env python3
"""Native, human-gated acceptance of analyst workflow and corporate controls.

Uses scripted clients to test interfaces; does not evaluate a real LLM.
"""
import io
import json
import shlex
import tarfile
import time
from demo_client import ROOT,SSHClient


def main():
    client=SSHClient();token=client.json('human','range claim analyst-acceptance --minutes 30')['token']
    out=ROOT/'local'/('analyst-rehearsal-'+time.strftime('%Y%m%dT%H%M%S'));out.mkdir(mode=0o700,parents=True)
    report={'success':False,'checks':{}}
    def control(command):return client.json('human','range '+command+' --token '+shlex.quote(token),timeout=240)
    def ready():
        started=time.monotonic()
        for _ in range(150):
            state=client.json('human','range status')
            if state['phase']=='ready':return
            if state['phase']=='stopped' and time.monotonic()-started>15: raise RuntimeError('Range startup stopped; inspect the owner journal')
            time.sleep(3)
        raise RuntimeError('Range did not become ready')
    def py(role,source):return client.run(role,'python3 -c '+shlex.quote(source)).stdout
    def web(role,success):
        code="import urllib.request; urllib.request.urlopen('http://web-01.dmz/?q=union%20select',timeout=3).read(128)"
        result=client.run(role,'python3 -c '+shlex.quote(code),check=False)
        assert (result.returncode==0)==success,result.stderr
    try:
        control('start --seed 42 --clock-speed 60 --attacker llm --normal-traffic llm');ready()
        assert client.json('blue','analyst inbox')==[]
        assert client.json('blue','analyst cases')==[]
        assert client.json('blue','evidence availability')['ok']
        assets=client.json('blue','analyst assets')
        red=next(x['addresses']['dmz'] for x in assets if x['service']=='red')
        telemetry=next(x['addresses']['management'] for x in assets if x['service']=='telemetry')
        file_ip=next(x['addresses']['internal'] for x in assets if x['service']=='file-01')
        report['checks']['all_eight_baseline_workflows']=True
        # Test actual network separation, not just an advertised topology.
        for ip,port in ((telemetry,8088),(file_ip,22)):
            code='import socket; socket.create_connection(('+repr(ip)+','+str(port)+'),timeout=2)'
            assert client.run('red','python3 -c '+shlex.quote(code),check=False).returncode!=0
        py('blue',"import urllib.request,urllib.error;\ntry: urllib.request.urlopen('http://telemetry.management:8088/analyst/inbox')\nexcept urllib.error.HTTPError as e: assert e.code==403\nelse: raise AssertionError('Unauthenticated API access')")
        report['checks']['dmz_to_lan_and_management_denied']=True
        report['checks']['workspace_auth_required']=True
        web('red',True)
        for _ in range(30):
            client.json('blue','evidence flush')
            inbox=client.json('blue','analyst inbox')
            alert=next((a for a in inbox if a['rule']=='ids:9000002'),None)
            if alert:break
            time.sleep(2)
        else:raise AssertionError('Real HTTP request did not produce a Suricata inbox alert')
        assert alert['evidence']['fields']['src_ip']==red
        logs=client.json('blue','analyst logs --source eve.json --query union')
        assert logs['matches']>0
        report['checks']['real_ids_alert_and_search']=True
        case=client.json('blue','analyst open "Investigate lab SQL request" --alert '+alert['id'])
        ident=case['id']
        note='analyst note '+ident+' "Observed source and network IDS evidence" --event '+alert['evidence']['id']+' --version 1'
        case=client.json('blue',note);assert case['version']==2
        assert client.run('blue',note,check=False).returncode!=0
        client.json('blue','analyst firewall block --ip '+red+' --reason '+shlex.quote('Contain observed source; case '+ident))
        web('red',False)
        assert client.json('blue','evidence availability')['ok']
        client.json('blue','analyst firewall unblock --ip '+red+' --reason '+shlex.quote('Restore source after verification; case '+ident))
        web('red',True)
        report['checks']['reversible_containment_and_eight_business_checks']=True
        case=client.json('blue','analyst handover '+ident+' --version 2 --summary "Network IDS request reviewed" --actions "Blocked source; verified eight workflows; restored source" --next-steps "Review application impact"')
        assert case['version']==3
        white=client.json('human','observe analyst');assert white['cases'][0]['id']==ident
        report['checks']['notes_version_conflict_and_white_handover']=True
        # Leave a block to prove a new run clears it.
        client.json('blue','analyst firewall block --ip '+red+' --reason "Reset acceptance sentinel"')
        before=py('blue',"from pathlib import Path; print(Path('/run/analyst/token').read_text().strip())").strip()
        saved=control('export')
        content=client.run('human','range download '+saved['id'],binary=True).stdout
        with tarfile.open(fileobj=io.BytesIO(content)) as archive:
            names=archive.getnames()
            assert 'observations/analyst/workspace.json' in names
            assert 'observations/analyst/'+ident+'-handover.md' in names
            assert 'ids/eve.json' in names and 'firewall/actions.jsonl' in names
            assert not any('token' in name for name in names)
        path=out/(saved['id']+'.tar.gz');path.write_bytes(content);path.chmod(0o600)
        report['checks']['workspace_ids_and_firewall_export']=True
        control('reset --seed 43 --clock-speed 60 --attacker llm --normal-traffic llm');ready()
        assert client.json('blue','analyst cases')==[] and client.json('blue','analyst inbox')==[]
        assert client.json('blue','analyst firewall status')['blocked']==[]
        assert before!=py('blue',"from pathlib import Path; print(Path('/run/analyst/token').read_text().strip())").strip()
        web('red',True)
        assert client.json('blue','evidence availability')['ok']
        old=client.run('human','range download '+saved['id'],binary=True).stdout
        assert old==content
        report['checks']['reset_clears_workspace_blocks_and_token_preserves_export']=True
        report['success']=True
    finally:
        try:report['release']=control('release')
        finally:
            (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({'report':str(out/'report.json'),'success':report['success'],'checks':report['checks']}),flush=True)


if __name__=='__main__':main()
