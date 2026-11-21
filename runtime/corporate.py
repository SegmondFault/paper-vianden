"""Private inner-network firewall and bounded, audited containment control.

This module runs inside the network-none system container, never on the VPS.
"""
from datetime import datetime, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading

ROOT = Path('/opt/paper-vianden')
CONFIG = Path('/run/corporate')
SUBNETS = {'management':'172.28.10.0/24','dmz':'172.28.20.0/24','internal':'172.28.30.0/24'}
ZONES = {
    'defender': ['management'], 'telemetry':['management'], 'white':['management'],
    'entry':['entry','management'], 'vpn-gw-01':['dmz','internal'],
    'red':['dmz'], 'scenario-runner':['dmz'], 'scenario-sink':['dmz'],
    'green':['internal'], 'activity':['internal'], 'dvwa':['dmz'],
}
NAMES = {'defender':'blue', 'activity':'users-01', 'scenario-runner':'attacker-01',
         'snmp':'router', 'vpn-gw-01':'vpn-gw-01'}


def command(*args, **kwargs):
    return subprocess.check_output(list(args), text=True, **kwargs)


def guard():
    # Sysbox's outer container has network=none: loopback and our inner bridges,
    # no physical interfaces and no external default route. Refuse host use.
    interfaces = {name for _,name in socket.if_nameindex()}
    if any(not (name=='lo' or name=='docker0' or name.startswith(('br-','veth'))) for name in interfaces):
        raise RuntimeError('Corporate controls require the private network-none range namespace')
    if command('ip','-4','route','show','default').strip():
        raise RuntimeError('Unexpected external route in private range namespace')
    if os.geteuid() != 0: raise RuntimeError('Inner owner required')


def prepare(compose):
    """Create an inner-only Compose overlay with predictable inventory and routes."""
    guard(); CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    cfg=json.loads(command(*compose,'config','--format','json',cwd=ROOT))
    hosts={}; inventory=[]; assignments={}
    counters={key:10 for key in SUBNETS}
    for name, service in sorted(cfg['services'].items()):
        zones=ZONES.get(name,list(service.get('networks',{})))
        assignments[name]={}
        for zone in zones:
            if zone not in SUBNETS: continue
            counters[zone]+=1
            ip=SUBNETS[zone].rsplit('.',1)[0]+'.'+str(counters[zone])
            assignments[name][zone]=ip
            hosts[(NAMES.get(name,name))+'.'+zone]=ip
        inventory.append({'host':NAMES.get(name,name),'service':name,'zones':zones,'addresses':assignments[name]})
    # Preserve aliases used by the storyline while routing across the firewall.
    hosts['scenario-sink.internal']=assignments['scenario-sink']['dmz']
    lines=['# Generated only inside the disposable network-none system container.', 'services:']
    for name, addresses in assignments.items():
        lines += ['  '+name+':', '    networks: !override']
        for zone,ip in addresses.items():
            aliases=[host for host,address in hosts.items() if address==ip]
            lines += ['      '+zone+':', '        ipv4_address: '+ip, '        aliases: '+json.dumps(aliases)]
        if name=='entry': lines += ['      entry: {}']
        lines += ['    extra_hosts: '+json.dumps(hosts)]
        if name=='telemetry': lines += ['    volumes:', '      - /run/corporate:/run/corporate:ro']
    lines += ['  ids:', '    image: paper-vianden/ids:local',
        '    platform: linux/amd64', '    init: true', '    restart: "no"',
        '    network_mode: host', '    entrypoint: [python3, /opt/ids/ids.py]',
        '    read_only: true', '    cap_drop: [ALL]', '    cap_add: [NET_RAW, NET_ADMIN]',
        '    security_opt: [no-new-privileges:true]', '    mem_limit: 384m', '    memswap_limit: 384m',
        '    cpus: 0.5', '    pids_limit: 64', '    tmpfs: ["/tmp:rw,nosuid,nodev,size=16m"]',
        '    volumes:', '      - /run/corporate:/run/corporate:ro',
        '      - ../runtime/ids.py:/opt/ids/ids.py:ro', '      - ../runtime/ids.rules:/opt/ids/ids.rules:ro',
        '      - ids-evidence:/var/log/security',
        '    healthcheck:', '      test: [CMD, python3, -c, "from pathlib import Path; assert Path(\'/var/log/security/eve.json\').exists()"]',
        '      interval: 5s', '      timeout: 3s', '      retries: 18',
        '    logging: {driver: json-file, options: {max-size: 2m, max-file: "2"}}',
        'networks:']
    for zone,subnet in SUBNETS.items():
        lines += ['  '+zone+':', '    internal: false', '    driver_opts: {com.docker.network.bridge.enable_ip_masquerade: "false"}', '    ipam: {config: [{subnet: '+subnet+'}]}']
    overlay=ROOT/'prototype/corporate.generated.yaml'; overlay.write_text('\n'.join(lines)+'\n')
    (CONFIG/'assets.json').write_text(json.dumps(inventory)+'\n')
    return assignments, overlay


class Firewall:
    def __init__(self, assignments, compose):
        guard(); self.assignments=assignments; self.lock=threading.RLock(); self.blocked=set()
        self.token=secrets.token_hex(32)
        cfg=json.loads(command(*compose,'config','--format','json',cwd=ROOT))
        self.bridges={zone:'br-'+json.loads(command('docker','network','inspect',cfg['networks'][zone]['name']))[0]['Id'][:12] for zone in SUBNETS}
        self.apply()
        interfaces=[self.bridges['dmz'],self.bridges['internal']]
        (CONFIG/'ids.json').write_text(json.dumps({'namespace':os.readlink('/proc/self/ns/net'),
            'interfaces':interfaces,'subnets':list(SUBNETS.values())}))
        url='http://172.28.10.1:8090/firewall'
        (CONFIG/'control.json').write_text(json.dumps({'url':url,'token':self.token}))
        self.telemetry=assignments['telemetry']['management']
        volume=json.loads(command('docker','volume','inspect',cfg['volumes']['firewall-evidence']['name']))[0]
        self.journal=Path(volume['Mountpoint'])/'actions.jsonl'
        self.server=ThreadingHTTPServer(('172.28.10.1',8090),self.handler())
        self.server.daemon_threads=True
        threading.Thread(target=self.server.serve_forever,daemon=True).start()

    def ipt(self,*args): return command('iptables','-w','5',*args)

    def chain(self,name):
        subprocess.run(['iptables','-w','5','-N',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.ipt('-F',name)

    def apply(self):
        # Only our inner namespace, own chains, no host sysctls/modules/rules.
        self.chain('PV-POLICY'); self.chain('PV-BLOCK'); self.chain('PV-INPUT')
        self.ipt('-A','PV-POLICY','-j','PV-BLOCK')
        self.ipt('-A','PV-POLICY','-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT')
        for name in ('defender','telemetry'):
            self.ipt('-A','PV-POLICY','-s',self.assignments[name]['management'],'-j','ACCEPT')
        # One intentional public application -> database dependency.
        self.ipt('-A','PV-POLICY','-s',self.assignments['dvwa']['dmz'],'-d',self.assignments['db-01']['internal'],
                 '-p','tcp','--dport','3306','-j','ACCEPT')
        # Employee egress to public lab web, mail, FTP and mock DNS only.
        for proto,ports in [('tcp','21,22,80,1025,3000,8025,8080,30000:30009'),('udp','1053')]:
            self.ipt('-A','PV-POLICY','-s',SUBNETS['internal'],'-d',SUBNETS['dmz'],
                     '-p',proto,'-m','multiport','--dports',ports,'-j','ACCEPT')
        for source in SUBNETS.values():
            for dest in SUBNETS.values():
                if source!=dest: self.ipt('-A','PV-POLICY','-s',source,'-d',dest,'-j','DROP')
        self.ipt('-A','PV-POLICY','-j','RETURN')
        # Accept explicit cross-bridge routes before Docker's isolation chains.
        self.ipt('-I','DOCKER-USER','1','-j','PV-POLICY')
        for zone in ('dmz','internal'):
            self.ipt('-A','PV-INPUT','-s',SUBNETS[zone],'-j','DROP')
        self.ipt('-A','PV-INPUT','-j','RETURN'); self.ipt('-I','INPUT','1','-j','PV-INPUT')

    def act(self,data):
        with self.lock:
            action=data.get('action')
            if action=='status':
                return {'blocked':sorted(self.blocked),'policy':self.ipt('-L','PV-POLICY','-n','-v','-x'),
                        'containment':self.ipt('-L','PV-BLOCK','-n','-v','-x'),'ids':'passive; no inline IPS'}
            if action not in ('block','unblock'): raise ValueError('Unknown firewall action')
            ip=str(ipaddress.IPv4Address(data.get('ip')))
            permitted={value for name,zones in self.assignments.items() if name not in ('defender','telemetry','white','entry') for value in zones.values()}
            if ip not in permitted: raise ValueError('Choose a workload address from analyst assets')
            reason=data.get('reason','')
            if not isinstance(reason,str) or not 1<=len(reason.strip())<=1000: raise ValueError('A reason is required')
            if action=='block' and ip not in self.blocked:
                # Drop established traffic too, both directions.
                self.ipt('-A','PV-BLOCK','-s',ip,'-j','DROP'); self.ipt('-A','PV-BLOCK','-d',ip,'-j','DROP'); self.blocked.add(ip)
            elif action=='unblock' and ip in self.blocked:
                self.ipt('-D','PV-BLOCK','-s',ip,'-j','DROP'); self.ipt('-D','PV-BLOCK','-d',ip,'-j','DROP'); self.blocked.remove(ip)
            result={'time':datetime.now(timezone.utc).isoformat(),'action':action,'ip':ip,'reason':reason,'blocked':sorted(self.blocked)}
            # Bounded journal independent of the analyst API audit.
            if self.journal.exists() and self.journal.stat().st_size>2*2**20:
                self.journal.replace(str(self.journal)+'.1')
            with self.journal.open('a') as log: log.write(json.dumps(result)+'\n')
            return result

    def handler(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_POST(self):
                if self.path!='/firewall' or self.client_address[0]!=owner.telemetry or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+owner.token):
                    self.send_error(403); return
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 1<=size<=4096: raise ValueError('Invalid body size')
                    result=owner.act(json.loads(self.rfile.read(size))); code=200
                except (ValueError,TypeError) as error: result={'error':str(error)}; code=400
                body=json.dumps(result).encode(); self.send_response(code)
                self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        return Handler
