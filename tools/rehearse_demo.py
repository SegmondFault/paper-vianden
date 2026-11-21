#!/usr/bin/env python3
"""Scripted acceptance of the SOC response interface; does not run an AI model.

Claims a fresh human-owned demo, locks only the simulated intruder's file-host
fixture account through blue, checks normal work, downloads evidence, releases.
Refuses to replace another person's reservation or active exercise.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import shlex
import tarfile
import time
from demo_client import ROOT, SSHClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file');parser.add_argument('--known-hosts')
    parser.add_argument('--clock-speed',type=float,default=600)
    args=parser.parse_args()
    client=SSHClient(args.env_file,args.known_hosts)
    report={'started':time.time(),'scripted_client':True,'checks':{}}
    out=ROOT/'local'/('demo-rehearsal-'+time.strftime('%Y%m%dT%H%M%S'))
    out.mkdir(parents=True,mode=0o700)
    claim=client.json('human','range claim acceptance-rehearsal --minutes 25')
    token=claim['token']
    def control(command):return client.json('human','range '+command+' --token '+shlex.quote(token),timeout=240)
    try:
        rival=client.run('human','range claim second-human',check=False)
        assert rival.returncode!=0,'Second human acquired the exercise'
        report['checks']['human_gate_exclusive']=True
        control('start --seed 42 --clock-speed '+str(args.clock_speed))
        for _ in range(150):
            status=client.json('human','range status')
            if status.get('phase')=='ready':break
            time.sleep(4)
        else:raise RuntimeError('Range failed to become ready')
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(client.run,'agent',cmd) for cmd in ('hostname','id -u','evidence status')]
            results=[f.result().stdout for f in futures]
        assert results[0].strip()=='defender' and results[1].strip()=='0',results[:2]
        report['checks']['parallel_agent_tools']=True
        denied=client.run('agent','range stop --token '+shlex.quote(token),check=False)
        assert denied.returncode!=0,'Agent obtained human lifecycle control'
        report['checks']['agent_cannot_control_lifecycle']=True
        baseline=client.json('agent','evidence availability')
        assert baseline['ok'],baseline
        report['baseline']=baseline
        cursor=''; clue=None
        for _ in range(240):
            page=client.json('agent','evidence tail --limit 1000'+(' --after '+shlex.quote(cursor) if cursor else ''))
            cursor=page['cursor']
            clue=next((e for e in page['events'] if e['host']=='file-01.internal' and 'Accepted password for devuser' in e['message']),None)
            if clue:break
            time.sleep(1)
        if not clue:raise RuntimeError('No observable file-host intrusion authentication arrived in the central feed')
        # This is an explicit, bounded demo response, not model decision-making.
        finding={'evidence_id':clue['id'],'finding':'New fixture-account SSH access on the file host',
                 'response':'Lock devuser on file-01 only','time':time.time(),'scripted_rehearsal':True}
        source="from pathlib import Path; Path('/var/lib/soc-ai/response.json').write_text("+repr(json.dumps(finding))+')'
        client.run('agent','ssh file-01.internal '+shlex.quote('passwd -l devuser')+' && python3 -c '+shlex.quote(source))
        report['checks']['response_executed_via_agent_ssh']=True
        after=client.json('agent','evidence availability')
        assert after['ok'],after
        report['after_response']=after
        for _ in range(240):
            status=client.json('human','observe status')
            if status['story']['state']=='complete':break
            time.sleep(1)
        else:raise RuntimeError('Scenario failed to finish')
        assert status['story']['objective']=='incomplete' and status['story']['results']['blocked']>0,status
        report['checks']['intruder_objective_prevented']=True
        report['story']=status['story']
        archived=control('export'); identity=archived['id']
        content=client.run('human','range download '+shlex.quote(identity),binary=True).stdout
        path=out/(identity+'.tar.gz');path.write_bytes(content);path.chmod(0o600)
        with tarfile.open(fileobj=io.BytesIO(content)) as archive:
            names=set(archive.getnames())
            assert {'findings/response.json','instructor/story-status.json','observations/events.jsonl'}<=names,names
            report['archive_manifest']=json.load(archive.extractfile('manifest.json'))
        report['checks']['findings_and_evidence_exported']=True
        report['archive']=str(path)
        report['success']=True
    finally:
        try:report['release']=control('release')
        finally:
            (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            (out/'report.json').chmod(0o600)
            print(json.dumps({'report':str(out/'report.json'),'success':report.get('success',False),'checks':report['checks']}))


if __name__=='__main__':main()
