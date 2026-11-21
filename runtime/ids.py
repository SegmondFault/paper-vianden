"""Run passive IDS only in the namespace explicitly prepared by the inner owner."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def configuration(settings):
    return {
        'vars': {'address-groups': {'HOME_NET': '['+','.join(settings['subnets'])+']', 'EXTERNAL_NET': 'any'},
                 'port-groups': {'HTTP_PORTS': '80,3000,8025,8080,3333'}},
        'af-packet': [{'interface': name, 'threads': 1, 'cluster-id': 90+i,
                       'cluster-type': 'cluster_flow', 'defrag': True, 'use-mmap': True,
                       'tpacket-v3': True, 'ring-size': 1024} for i,name in enumerate(settings['interfaces'])],
        'default-rule-path': '/opt/ids', 'rule-files': ['ids.rules'],
        'classification-file': '/etc/suricata/classification.config',
        'reference-config-file': '/etc/suricata/reference.config',
        'default-log-dir': '/var/log/security',
        'outputs': [{'eve-log': {'enabled': True, 'filetype': 'regular', 'filename': 'eve.json',
                   'types': ['alert', {'dns': {'enabled': True}}, 'http', 'tls']}},
                    {'stats': {'enabled': False}}],
        'stats': {'enabled': False}, 'flow': {'memcap': '16mb', 'hash-size': 4096, 'prealloc': 500},
        'stream': {'memcap': '16mb', 'reassembly': {'memcap': '32mb', 'depth': '256kb'}},
        'host': {'memcap': '4mb', 'hash-size': 1024, 'prealloc': 100},
        'detect': {'profile': 'low'}, 'logging': {'outputs': [{'console': {'enabled': True}}]},
    }


def main():
    settings = json.loads(Path('/run/corporate/ids.json').read_text())
    if os.readlink('/proc/self/ns/net') != settings['namespace']:
        raise SystemExit('Refusing IDS capture outside the prepared private range namespace')
    if not all(Path('/sys/class/net', name).is_dir() and name.startswith('br-') for name in settings['interfaces']):
        raise SystemExit('Missing private range bridges')
    config = configuration(settings)
    # JSON is a YAML subset understood by libyaml; include the Suricata YAML header.
    path = Path('/tmp/suricata.yaml'); path.write_text('%YAML 1.1\n---\n'+json.dumps(config))
    subprocess.run(['suricata', '-T', '-c', str(path)], check=True)
    child = subprocess.Popen(['suricata', '-c', str(path), '--af-packet', '--runmode', 'workers'])
    def stop(*_): child.terminate()
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    try:
        while child.poll() is None:
            output = Path('/var/log/security/eve.json')
            if output.exists() and output.stat().st_size > 4*2**20:
                for index in (2,1):
                    source=Path(str(output)+'.'+str(index))
                    if source.exists(): source.replace(str(output)+'.'+str(index+1))
                output.replace(str(output)+'.1'); child.send_signal(signal.SIGHUP)
            time.sleep(1)
    finally:
        if child.poll() is None: child.terminate()
        child.wait(timeout=15)
    raise SystemExit(child.returncode)


if __name__ == '__main__': main()
