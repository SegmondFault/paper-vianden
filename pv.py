#!/usr/bin/python3 -I
"""Paper Vianden: one explicit, offline, disposable Sysbox session."""
import argparse
import contextlib
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import pty
import pwd
import select
import shlex
import re
import termios
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'runtime'))
from demo_control import Controller, session_slot
RUNTIME = Path('/run/paper-vianden')
STORE = Path('/var/lib/paper-vianden')
MOUNT = RUNTIME/'session'
SOCKET = RUNTIME/'docker.sock'
DOCKER = ['/usr/bin/docker', '--host', 'unix://'+str(SOCKET)]
ENV = {'PATH': str(ROOT/'runtime/bin')+':/usr/sbin:/usr/bin:/sbin:/bin',
       'HOME': '/root', 'DOCKER_HOST': 'unix://'+str(SOCKET),
       'DOCKER_TMPDIR': str(MOUNT/'tmp')}
OWNER_UNIT = 'paper-vianden-owner.service'
PORTAL_CONFIG = Path('/etc/paper-vianden/portals.json')
INNER = ['docker', 'compose', '-p', 'paper-vianden', '--profile', 'extended',
         '-f', '/opt/paper-vianden/prototype/docker-compose.yml',
         '-f', '/opt/paper-vianden/compose.yaml']


def command(args, **kwargs):
    return subprocess.run(args, env=ENV, check=True, **kwargs)


def die_with_parent():
    # Linux removes helpers when the foreground owner is forcibly terminated.
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0)


def capture(args):
    return command(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def unit_loaded():
    return capture(['/usr/bin/systemctl', 'show', '--property=LoadState', '--value',
                    'paper-vianden-session.service']) != 'not-found'


def save_session(info):
    pending = RUNTIME/'active.tmp'
    pending.write_text(json.dumps(info)+'\n')
    pending.replace(RUNTIME/'active.json')


def wait_for(test, processes, seconds=90):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('A session helper stopped; inspect the session log before cleanup.')
        if test():
            return
        time.sleep(.5)
    raise RuntimeError('Session startup timed out')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def trusted_install():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('This prepared range currently requires Linux amd64.')
    if os.geteuid() != 0:
        raise RuntimeError('Use the administrator-installed sudo command.')
    # A sudo caller may not choose executable/configuration inputs through env.
    for path in [ROOT, ROOT/'pv.py', ROOT/'runtime', ROOT/'runtime/bin', STORE]:
        info = path.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError('Administrator-owned, non-writable installation required: '+str(path))
    for name in ['sysbox-mgr', 'sysbox-fs', 'sysbox-runc', 'fusermount3']:
        path = ROOT/'runtime/bin'/name
        info = path.stat()
        if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError('Untrusted runtime binary: '+str(path))


def join_argv(role, name, execute=None, tty=True):
    flags = ['-i']+(['-t'] if tty else [])
    shell = ['bash'] if execute is None else ['bash', '-lc', execute]
    if role == 'control':
        return DOCKER+['exec']+flags+[name]+shell
    service = {'blue':'defender','red':'red','white':'white','green':'green'}[role]
    return DOCKER+['exec']+flags+[name]+INNER+['exec']+([] if tty else ['-T'])+[service]+shell


def portal_role(config, uid, username):
    record = config.get('accounts', {}).get(username, {})
    if record.get('uid') != uid or record.get('role') not in ('blue','white','red','green'):
        raise RuntimeError('This account has no workstation portal permission')
    return record['role']


def managed_running():
    return unit_loaded() or capture(['/usr/bin/systemctl','show','--property=ActiveState','--value',OWNER_UNIT]) in (
        'active','activating','deactivating')


def archive_directory():
    directory = STORE/'evidence'
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if directory.is_symlink() or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError('Unsafe evidence archive directory')
    return directory


def archive_list():
    return {'archives': [{'id':p.stem.removesuffix('.tar'), 'bytes':p.stat().st_size,
                          'created':p.stat().st_mtime} for p in sorted(archive_directory().glob('*.tar.gz'))[-100:]]}


def archive_download(identity):
    if not re.fullmatch(r'paper-vianden-[a-f0-9]{12}-[a-f0-9]{8}',identity):
        raise RuntimeError('Invalid archive identifier')
    path=archive_directory()/(identity+'.tar.gz')
    if path.is_symlink() or not path.is_file() or path.stat().st_size>64*2**20:
        raise RuntimeError('Archive unavailable or too large')
    return path.read_bytes()


def archive_session(info):
    name=info['name']
    if not re.fullmatch(r'paper-vianden-[a-f0-9]{12}',name): raise RuntimeError('Invalid session identity')
    # Flush the collector before taking the white snapshot. Earlier releases
    # have no collector; their original journals can still be exported.
    subprocess.run(DOCKER+['exec',name]+INNER+['exec','-T','telemetry','python3',
                   '/usr/local/bin/evidence','flush'],env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=40)
    identity=name+'-'+uuid.uuid4().hex[:8]
    path=archive_directory()/(identity+'.tar.gz')
    # The fixed exporter reads root-owned agent findings even with umask 077.
    # Ordinary human white sessions remain UID 65534 and read-only.
    argv=DOCKER+['exec',name]+INNER+['exec','-T','--user','0','white','python3','-c',(ROOT/'runtime/export_evidence.py').read_text()]
    with path.open('xb') as target:
        path.chmod(0o600)
        process=subprocess.Popen(argv,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        count=0
        try:
            while True:
                data=process.stdout.read(65536)
                if not data: break
                count+=len(data)
                if count>64*2**20: raise RuntimeError('Evidence archive exceeded its bound')
                target.write(data)
            if process.wait(timeout=30) or count<32: raise RuntimeError('Evidence export failed')
        except BaseException:
            process.kill(); process.wait(); path.unlink(missing_ok=True); raise
    (RUNTIME/'last-export.json').write_text(json.dumps({'id':identity,'bytes':count,'source':info.get('source')}))
    return {'id':identity,'bytes':count}


def archive_current():
    active=RUNTIME/'active.json'
    if not active.exists(): return {'state':'stopped','archives':archive_list()['archives']}
    info=json.loads(active.read_text())
    if info.get('state')!='ready': return {'state':info.get('state','starting')}
    return archive_session(info)


def human_control(words,uid,username,config):
    def stop():
        command(['/usr/bin/systemctl','stop',OWNER_UNIT])
        if unit_loaded(): command(['/usr/bin/systemctl','stop','paper-vianden-session.service'])
    controller=Controller(RUNTIME,managed_running,
        lambda:command(['/usr/bin/systemctl','start','--no-block',OWNER_UNIT]), stop,
        archive_current,archive_list,archive_download,maximum=config.get('lease_minutes',1560))
    result=controller.execute(words,uid,username)
    if words and words[0]=='status' and isinstance(result,dict):
        active=RUNTIME/'active.json'
        result['phase']=json.loads(active.read_text()).get('state') if active.exists() else 'stopped'
        preset=RUNTIME/'demo-run.json'
        result['modes']=json.loads(preset.read_text()) if preset.exists() else {}
    if isinstance(result,bytes): sys.stdout.buffer.write(result)
    else: print(json.dumps(result),flush=True)


def portal(execute=None):
    trusted_install()
    for path in (PORTAL_CONFIG.parent, PORTAL_CONFIG):
        info = path.lstat()
        if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError('Untrusted portal configuration')
    uid = int(os.environ.get('SUDO_UID', '-1'))
    if uid <= 0:
        raise RuntimeError('Portal requires an authenticated sudo caller')
    config=json.loads(PORTAL_CONFIG.read_text())
    username=pwd.getpwuid(uid).pw_name
    role = portal_role(config, uid, username)
    words=shlex.split(execute or '')
    if words and words[0]=='range':
        if role!='white': raise RuntimeError('Exercise controls belong to the human account')
        human_control(words[1:],uid,username,config)
        return
    with session_slot(RUNTIME,uid,config.get('max_sessions',16)):
        portal_connect(role, execute)


def portal_connect(role, execute=None):
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    lease=RUNTIME/'demo-lease.json'
    if not lease.exists() or json.loads(lease.read_text()).get('expires',0)<=time.time():
        raise RuntimeError('No human-owned demo is available. Ask the human to use range claim and range start.')
    if not managed_running():
        raise RuntimeError('The demo is reserved but stopped. Its human owner must use range start.')
    for attempt in range(900):
        active = RUNTIME/'active.json'
        if active.exists() and json.loads(active.read_text()).get('state') == 'ready':
            if role=='green' and json.loads(active.read_text()).get('normal_traffic')!='llm':
                raise RuntimeError('Green LLM access requires the human to select --normal-traffic llm for this run')
            if role=='red' and json.loads(active.read_text()).get('attacker')!='llm':
                raise RuntimeError('Red LLM access requires the human to select --attacker llm for this run')
            join(role, execute=execute or None)
            return
        if attempt > 5 and capture(['/usr/bin/systemctl', 'show', '--property=ActiveState',
                                    '--value', OWNER_UNIT]) in ('failed', 'inactive'):
            raise RuntimeError('Workstation startup failed; contact the administrator')
        if attempt % 30 == 0:
            print('Preparing workstation; please wait...', file=sys.stderr, flush=True)
        time.sleep(1)
    raise RuntimeError('Workstation startup timed out')


def serve(args):
    """Keep a private owner terminal alive independently of participant SSH."""
    trusted_install()
    preset=RUNTIME/'demo-run.json'
    if preset.exists():
        data=json.loads(preset.read_text())
        args.seed=scenario_seed(str(data['seed']))
        args.clock_speed=scenario_speed(str(data['clock_speed']))
        args.attacker=data.get('attacker','scripted')
        args.normal_traffic=data.get('normal_traffic','scripted')
    master, slave = pty.openpty()
    process = None
    def terminal():
        os.setsid()
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
    try:
        process = subprocess.Popen(['/usr/bin/python3', '-I', str(ROOT/'pv.py'), 'run',
            '--seed',str(args.seed),'--clock-speed',str(args.clock_speed),
            '--attacker',args.attacker,'--normal-traffic',args.normal_traffic],
            stdin=slave, stdout=slave, stderr=slave, env=ENV, preexec_fn=terminal)
        os.close(slave)
        slave = None
        while process.poll() is None:
            lease=RUNTIME/'demo-lease.json'
            if preset.exists() and (not lease.exists() or json.loads(lease.read_text()).get('expires',0)<=time.time()):
                print('Human demo lease expired; exporting evidence and stopping.',flush=True)
                break
            readable, _, _ = select.select([master], [], [], 1)
            if readable:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
        if process.poll() is None:
            subprocess.run(['/usr/bin/systemctl','stop','paper-vianden-session.service'],env=ENV)
        code = process.wait(timeout=100)
        if code:
            raise RuntimeError('Managed workstation owner exited with status '+str(code))
    finally:
        subprocess.run(['/usr/bin/systemctl', 'stop', 'paper-vianden-session.service'], env=ENV)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        os.close(master)
        if slave is not None:
            os.close(slave)


def join(role, name=None, execute=None):
    trusted_install()
    if name is None:
        if subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet',
                           'paper-vianden-session.service']).returncode:
            raise RuntimeError('No active range. An owner must explicitly start one first.')
        if not (RUNTIME/'active.json').exists():
            raise RuntimeError('The range is starting; wait for the owner to report readiness.')
        active = json.loads((RUNTIME/'active.json').read_text())
        if active.get('state') != 'ready':
            raise RuntimeError('The shared range is '+active.get('state', 'starting')+
                               '; wait for the owner before joining.')
        name = active['name']
        if not name.startswith('paper-vianden-') or not name.removeprefix('paper-vianden-').isalnum():
            raise RuntimeError('Invalid session identity')
    command(join_argv(role, name, execute, sys.stdin.isatty() and sys.stdout.isatty()))


def session(args):
    trusted_install()
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    info = RUNTIME.lstat()
    if info.st_uid != 0 or info.st_mode & 0o077 or RUNTIME.is_symlink():
        raise RuntimeError('Unsafe runtime directory')
    with (RUNTIME/'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('A shared range is already active. Use join-range to join it.')
        if unit_loaded():
            raise RuntimeError('The shared range is starting, running or stopping. '
                               'Join it when ready, or wait until range-status says Stopped.')
        # A killed owner can leave bookkeeping, but cannot create a second unit.
        (RUNTIME/'active.json').unlink(missing_ok=True)
        argv = ['/usr/bin/unshare', '--mount', '--propagation', 'private', '--',
                '/usr/bin/python3', '-I', str(ROOT/'pv.py'), '_session',
                'run','--role',args.role,'--clock-speed',str(args.clock_speed),'--seed',str(args.seed),
                '--attacker',args.attacker,'--normal-traffic',args.normal_traffic]
        if args.check:
            argv.append('--check')
        properties = ['--property=Delegate=yes', '--property=KillMode=mixed',
                      '--property=MemoryHigh=5G', '--property=MemoryMax=7G',
                      '--property=MemorySwapMax=0',
                      '--property=CPUQuota=400%', '--property=TasksMax=4096',
                      '--property=TimeoutStopSec=120']
        own_group = next(line.split('::', 1)[1].strip() for line in
                         Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
        unit = own_group.rsplit('/', 1)[-1]
        if unit.endswith('.scope') or unit == OWNER_UNIT:
            properties.append('--property=BindsTo='+unit)
        service = ['/usr/bin/systemd-run', '--quiet', '--collect', '--wait',
                   '--unit=paper-vianden-session', '--service-type=exec',
                   '--pipe' if args.check else '--pty'] + properties + argv
        child = subprocess.Popen(service, env=ENV, preexec_fn=die_with_parent)
        try:
            code = child.wait()
        finally:
            if child.poll() is None:
                subprocess.run(['/usr/bin/systemctl', 'stop', 'paper-vianden-session.service'], env=ENV)
                child.wait(timeout=60)
        if code == 130:
            raise KeyboardInterrupt
        if code:
            raise subprocess.CalledProcessError(code, service)


def run_session(args):
    library = STORE/'library'
    manifest = json.loads((library/'manifest.json').read_text())
    for name in ['envelope.tar.gz', 'targets.tar.gz']+(['addons.tar.gz'] if 'addons.tar.gz' in manifest['files'] else []):
        if sha256(library/name) != manifest['files'][name]:
            raise RuntimeError('Image library checksum mismatch: '+name)
    for name in ['sysbox-mgr', 'sysbox-fs']:
        if subprocess.run(['/usr/bin/pgrep', '-x', name], stdout=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError('An existing Sysbox instance is running; it will not be changed.')
    if MOUNT.is_mount():
        raise RuntimeError('A previous session mount needs administrator recovery.')
    if shutil.disk_usage(STORE).free < 34*2**30:
        raise RuntimeError('At least 34 GiB of free space is required for the bounded session disk.')
    name = 'paper-vianden-'+uuid.uuid4().hex[:12]
    disk = STORE/(name+'.ext4')
    processes = []
    logfiles = []
    mounted = False
    failure = None
    container_created = False
    follower = None
    session_info = {'name': name, 'pid': os.getpid(),
                    'source':manifest.get('source_revision'),'state':'starting',
                    'attacker':args.attacker,'normal_traffic':args.normal_traffic}
    try:
        save_session(session_info)
        group = next(line.split('::', 1)[1].strip() for line in
                     Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
        parent = Path('/sys/fs/cgroup')/group.lstrip('/')
        manager = parent/'manager'
        manager.mkdir(exist_ok=True)
        for pid in (parent/'cgroup.procs').read_text().split():
            (manager/'cgroup.procs').write_text(pid)
        controllers = (parent/'cgroup.controllers').read_text().split()
        (parent/'cgroup.subtree_control').write_text(' '.join('+'+x for x in controllers
                                                           if x in {'cpu', 'memory', 'pids', 'io'}))
        with disk.open('xb') as data:
            data.truncate(32*2**30)
        command(['/usr/sbin/mkfs.ext4', '-q', '-F', '-m', '0', str(disk)])
        MOUNT.mkdir(mode=0o700, exist_ok=True)
        command(['/usr/bin/mount', '-o', 'loop,nodev', str(disk), str(MOUNT)])
        mounted = True
        # The loop device holds the file open. Namespace teardown frees it even
        # after a forced owner exit; no named session disk remains on the host.
        disk.unlink()
        socket_dir = MOUNT/'sysbox-private'
        socket_dir.mkdir(mode=0o700, exist_ok=True)
        Path('/run/sysbox').mkdir(mode=0o755, exist_ok=True)
        command(['/usr/bin/mount', '--bind', str(socket_dir), '/run/sysbox'])
        (MOUNT/'tmp').mkdir()
        for directory in ['exec', 'containerd-state']:
            path = RUNTIME/directory
            if path.exists():
                shutil.rmtree(path)
        for filename in ['docker.sock', 'docker.pid', 'containerd.sock', 'containerd.sock.ttrpc']:
            (RUNTIME/filename).unlink(missing_ok=True)
        config = RUNTIME/'daemon.json'
        config.write_text('{}\n')
        def launch(label, argv):
            log = (MOUNT/(label+'.log')).open('w')
            logfiles.append(log)
            process = subprocess.Popen(argv, env=ENV, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, preexec_fn=die_with_parent)
            processes.append(process)
            return process
        # Debian's dockerd may discover the system containerd automatically.
        # Explicitly use a new containerd in this same private mount namespace.
        containerd_config = RUNTIME/'containerd.toml'
        containerd_config.write_text('version = 2\ndisabled_plugins = ["io.containerd.grpc.v1.cri"]\n')
        launch('containerd', ['/usr/bin/containerd', '--config='+str(containerd_config),
                             '--root='+str(MOUNT/'containerd'),
                             '--state='+str(RUNTIME/'containerd-state'),
                             '--address='+str(RUNTIME/'containerd.sock')])
        wait_for(lambda: (RUNTIME/'containerd.sock').exists(), processes)
        launch('docker', ['/usr/sbin/dockerd', '--config-file='+str(config),
                         '--host=unix://'+str(SOCKET), '--group=root',
                         '--data-root='+str(MOUNT/'docker'),
                         '--exec-root='+str(RUNTIME/'exec'), '--pidfile='+str(RUNTIME/'docker.pid'),
                         '--containerd='+str(RUNTIME/'containerd.sock'),
                         '--containerd-namespace=paper-vianden',
                         '--containerd-plugins-namespace=paper-vianden-plugins',
                         '--bridge=none', '--iptables=false',
                         '--ip-forward=false', '--ip-masq=false',
                         '--exec-opt=native.cgroupdriver=cgroupfs',
                         '--cgroup-parent='+group,
                         '--add-runtime=sysbox-runc='+str(ROOT/'runtime/bin/sysbox-runc')])
        wait_for(lambda: subprocess.run(DOCKER+['info'], env=ENV, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL).returncode == 0, processes)
        launch('sysbox-mgr', [str(ROOT/'runtime/bin/sysbox-mgr'), '--data-root',
                             str(MOUNT/'sysbox'), '--disable-inner-image-preload'])
        wait_for(lambda: Path('/run/sysbox/sysmgr.sock').exists(), processes)
        launch('sysbox-fs', [str(ROOT/'runtime/bin/sysbox-fs'), '--mountpoint', str(MOUNT/'sysboxfs')])
        wait_for(lambda: Path('/run/sysbox/sysfs.sock').exists(), processes)
        print('Loading the prepared offline range...', flush=True)
        command(DOCKER+['load', '-i', str(library/'envelope.tar.gz')], stdout=subprocess.DEVNULL)
        command(DOCKER+['create', '--name', name, '--runtime=sysbox-runc', '--network=none',
                        '--memory=6g', '--memory-swap=6g', '--cpus=4', '--pids-limit=2048',
                        '--label=io.paper-vianden.session=true',
                        '--env', 'PV_CLOCK_SPEED='+str(args.clock_speed),
                        '--env', 'PV_SEED='+str(args.seed),
                        '--env','PV_ATTACKER_MODE='+args.attacker,
                        '--env','PV_NORMAL_TRAFFIC='+args.normal_traffic,
                        '--mount', 'type=bind,src='+str(library/'targets.tar.gz')+',dst=/library/targets.tar.gz,readonly',
                        ]+(['--mount','type=bind,src='+str(library/'addons.tar.gz')+',dst=/library/addons.tar.gz,readonly'] if 'addons.tar.gz' in manifest['files'] else [])+
                       ['paper-vianden/envelope:local'], stdout=subprocess.DEVNULL)
        container_created = True
        command(DOCKER+['start', name], stdout=subprocess.DEVNULL)
        follower = subprocess.Popen(DOCKER+['logs', '--follow', name], env=ENV,
                                    preexec_fn=die_with_parent)
        def ready():
            r = subprocess.run(DOCKER+['exec', name, 'test', '-f', '/tmp/paper-vianden-ready'],
                               env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            state = capture(DOCKER+['inspect', '--format', '{{.State.Running}}', name])
            if state != 'true':
                detail = capture(DOCKER+['inspect', '--format', '{{json .State}}', name])
                logs = command(DOCKER+['logs', '--tail', '60', name], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
                raise RuntimeError('Envelope exited: '+detail+'\n'+logs)
            return r.returncode == 0
        wait_for(ready, processes, seconds=600)
        session_info['state'] = 'ready'
        save_session(session_info)
        print('Paper Vianden ready. Exit the shell to destroy this session.', flush=True)
        if args.check:
            command(DOCKER+['exec', name]+INNER+['exec', '-T', 'defender', 'python3',
                    '/opt/paper-vianden/runtime/check.py', '--activity'])
            command(DOCKER+['exec', name]+INNER+['exec', '-T', 'scenario-runner', 'python3',
                    '/opt/paper-vianden/runtime/scenario_runner.py', '--check'])
        else:
            join(args.role, name)
    except BaseException as error:
        failure = error
        if mounted and not isinstance(error, KeyboardInterrupt):
            for log in MOUNT.glob('*.log'):
                print('\n'+log.name+':\n'+log.read_text(errors='replace')[-3500:], file=sys.stderr)
        raise
    finally:
        # Ignore repeated terminal signals while destroying only this session.
        for sig in [signal.SIGHUP, signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, signal.SIG_IGN)
        session_info['state'] = 'stopping'
        save_session(session_info)
        if container_created:
            try:
                result=archive_session(session_info)
                print('Evidence preserved: '+result['id'],flush=True)
            except Exception as error:
                print('EVIDENCE EXPORT FAILED: '+str(error),file=sys.stderr,flush=True)
        cleanup_ok = True
        if container_created or (SOCKET.exists() and subprocess.run(
                DOCKER+['inspect', name], env=ENV, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL).returncode == 0):
            cleanup_ok = subprocess.run(DOCKER+['rm', '-f', '-v', name], env=ENV,
                                        stdout=subprocess.DEVNULL).returncode == 0
        if follower is not None:
            if follower.poll() is None:
                follower.terminate()
            follower.wait(timeout=10)
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logfiles:
            log.close()
        (RUNTIME/'active.json').unlink(missing_ok=True)
        subprocess.run(['/usr/bin/umount', '/run/sysbox'], env=ENV,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if mounted or MOUNT.is_mount():
            cleanup_ok = subprocess.run(['/usr/bin/umount', str(MOUNT)], env=ENV).returncode == 0 and cleanup_ok
        if cleanup_ok:
            disk.unlink(missing_ok=True)
            print('Session destroyed; its disk, containers, networks and temporary keys are gone.', flush=True)
        elif not failure:
            raise RuntimeError('Cleanup needs administrator attention; the session disk was retained.')


def scenario_seed(value):
    try:
        seed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('Seed must be an integer')
    if not 0 <= seed <= 2**32-1:
        raise argparse.ArgumentTypeError('Seed must be between 0 and 4294967295')
    return seed


def scenario_speed(value):
    speed = float(value)
    if not 1 <= speed <= 3600:
        raise argparse.ArgumentTypeError('Clock speed must be between 1 and 3600')
    return speed


def main():
    inner = len(sys.argv) > 1 and sys.argv[1] == '_session'
    if inner:
        sys.argv.pop(1)
        if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
            raise RuntimeError('A private mount namespace is required.')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run', help='Start one foreground session; destroy it on exit')
    run.add_argument('--role', choices=['blue','red','white','green'], default='blue')
    run.add_argument('--check', action='store_true', help='Check services then destroy the session')
    run.add_argument('--clock-speed', type=scenario_speed, default=1.0,
                     help='Scenario seconds per real second, 1–3600 (default: 1)')
    run.add_argument('--seed', type=scenario_seed, default=20260112,
                     help='Reproducible behaviour variant, unsigned 32-bit integer')
    run.add_argument('--attacker',choices=('scripted','llm'),default='scripted')
    run.add_argument('--normal-traffic',choices=('scripted','llm'),default='scripted')
    attach = sub.add_parser('join', help='Join the active session; never starts a range')
    attach.add_argument('--role',choices=['blue','red','white','green','control'],default='blue')
    portal_parser = sub.add_parser('portal', help='Account-bound SSH workstation portal')
    portal_parser.add_argument('--exec', dest='execute', default=None)
    managed = sub.add_parser('serve', help='Administrator-managed owner terminal')
    managed.add_argument('--seed', type=scenario_seed, default=20260112)
    managed.add_argument('--clock-speed', type=scenario_speed, default=1.0)
    managed.add_argument('--attacker',choices=('scripted','llm'),default='scripted')
    managed.add_argument('--normal-traffic',choices=('scripted','llm'),default='scripted')
    sub.add_parser('status', help='Show session state without starting anything')
    sub.add_parser('stop', help='Stop only the active Paper Vianden session')
    args = parser.parse_args()
    if args.command == 'status':
        active = RUNTIME/'active.json'
        if not unit_loaded():
            print('Stopped')
        else:
            unit_state = capture(['/usr/bin/systemctl', 'show', '--property=ActiveState',
                                  '--value', 'paper-vianden-session.service'])
            phase = json.loads(active.read_text()).get('state', 'starting') if active.exists() else 'starting'
            print('Stopping' if unit_state == 'deactivating' or phase == 'stopping'
                  else 'Running' if phase == 'ready' else 'Starting')
        return
    if args.command == 'stop':
        trusted_install()
        if capture(['/usr/bin/systemctl', 'show', '--property=LoadState', '--value',
                    'paper-vianden-session.service']) == 'not-found':
            print('Stopped')
            return
        command(['/usr/bin/systemctl', 'stop', 'paper-vianden-session.service'])
        return
    if args.command == 'join':
        join(args.role)
        return
    if args.command == 'portal':
        portal(args.execute)
        return
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    for sig in [signal.SIGHUP, signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, interrupted)
    if args.command == 'serve':
        serve(args)
    elif inner:
        trusted_install()
        run_session(args)
    else:
        session(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
