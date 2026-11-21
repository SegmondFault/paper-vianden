#!/usr/bin/env python3
"""Small SSH adapter for an external SOC architecture. Credentials stay local."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


class SSHClient:
    def __init__(self,env_file=None,known_hosts=None):
        self.values={}
        path=Path(env_file or ROOT/'.env')
        if path.exists():
            for line in path.read_text().splitlines():
                words=shlex.split(line,comments=True)
                if words:
                    key,value=words[0].split('=',1);self.values[key]=value
        self.values.update({k:v for k,v in os.environ.items() if k.startswith('VIANDEN_')})
        self.known_hosts=Path(known_hosts or ROOT/'local/known_hosts').resolve()
        if not self.known_hosts.is_file():raise RuntimeError('Supply a pinned known_hosts file')

    def run(self,role,command,timeout=90,check=True,binary=False,input=None):
        if role not in ('human','agent','admin'):raise ValueError('Unknown role')
        prefix='VIANDEN_'+role.upper()
        user=self.values[prefix+'_USER']; host=self.values['VIANDEN_HOST']
        password=self.values.get(prefix+'_PASSWORD')
        with tempfile.TemporaryDirectory(prefix='vianden-ssh-') as tmp:
            env=dict(os.environ)
            auth=[]
            if password:
                helper=Path(tmp)/'askpass'
                helper.write_text('#!'+sys.executable+'\nimport os\nprint(os.environ["PV_SSH_PASSWORD"])\n')
                helper.chmod(0o700)
                env.update(SSH_ASKPASS=str(helper),SSH_ASKPASS_REQUIRE='force',DISPLAY=':0',PV_SSH_PASSWORD=password)
                auth=['-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','NumberOfPasswordPrompts=1']
            else:auth=['-o','BatchMode=yes']
            argv=['ssh','-F','/dev/null','-T','-o','StrictHostKeyChecking=yes',
                  '-o','UserKnownHostsFile='+str(self.known_hosts),'-o','GlobalKnownHostsFile=/dev/null',
                  '-o','ClearAllForwardings=yes','-o','ConnectTimeout=10']+auth+[user+'@'+host,command]
            io={'stdin':subprocess.DEVNULL} if input is None else {'input':input}
            process=subprocess.run(argv,env=env,capture_output=True,**io,
                                   text=not binary,timeout=timeout,start_new_session=True)
            if check and process.returncode:
                error=process.stderr.decode(errors='replace') if binary else process.stderr
                if password:error=error.replace(password,'[redacted]')
                raise RuntimeError('SSH tool failed: '+error[-1500:])
            return process

    def json(self,role,command,timeout=90):
        return json.loads(self.run(role,command,timeout).stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=('human','agent'));parser.add_argument('command')
    parser.add_argument('--env-file');parser.add_argument('--known-hosts');parser.add_argument('--binary',action='store_true')
    args=parser.parse_args();client=SSHClient(args.env_file,args.known_hosts)
    result=client.run(args.role,args.command,binary=args.binary)
    if args.binary:sys.stdout.buffer.write(result.stdout)
    else:print(result.stdout,end='')


if __name__=='__main__':main()
