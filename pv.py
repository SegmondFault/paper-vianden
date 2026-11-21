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
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
RUNTIME = Path('/run/paper-vianden')
STORE = Path('/var/lib/paper-vianden')
MOUNT = RUNTIME/'session'
SOCKET = RUNTIME/'docker.sock'
DOCKER = ['/usr/bin/docker', '--host', 'unix://'+str(SOCKET)]
ENV = {'PATH': str(ROOT/'runtime/bin')+':/usr/sbin:/usr/bin:/sbin:/bin',
       'HOME': '/root', 'DOCKER_HOST': 'unix://'+str(SOCKET),
       'DOCKER_TMPDIR': str(MOUNT/'tmp')}
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


def join(role, name=None):
    trusted_install()
    if name is None:
        if subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet',
                           'paper-vianden-session.service']).returncode:
            raise RuntimeError('No active range. An owner must explicitly start one first.')
        if not (RUNTIME/'active.json').exists():
            raise RuntimeError('The range is starting; wait for the owner to report readiness.')
        active = json.loads((RUNTIME/'active.json').read_text())
        name = active['name']
        if not name.startswith('paper-vianden-') or not name.removeprefix('paper-vianden-').isalnum():
            raise RuntimeError('Invalid session identity')
    if role == 'control':
        command(DOCKER+['exec', '-it', name, 'bash'])
    else:
        service = 'defender' if role == 'blue' else 'red'
        command(DOCKER+['exec', '-it', name]+INNER+['exec', service, 'bash'])


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
            raise RuntimeError('A range session is already active.')
        argv = ['/usr/bin/unshare', '--mount', '--propagation', 'private', '--',
                '/usr/bin/python3', '-I', str(ROOT/'pv.py'), '_session',
                'run', '--role', args.role]
        if args.check:
            argv.append('--check')
        properties = ['--property=Delegate=yes', '--property=KillMode=mixed',
                      '--property=MemoryHigh=5G', '--property=MemoryMax=7G',
                      '--property=MemorySwapMax=0',
                      '--property=CPUQuota=400%', '--property=TasksMax=4096',
                      '--property=TimeoutStopSec=45']
        own_group = next(line.split('::', 1)[1].strip() for line in
                         Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
        unit = own_group.rsplit('/', 1)[-1]
        if unit.endswith('.scope'):
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
    for name in ['envelope.tar.gz', 'targets.tar.gz']:
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
    try:
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
                        '--mount', 'type=bind,src='+str(library/'targets.tar.gz')+',dst=/library/targets.tar.gz,readonly',
                        'paper-vianden/envelope:local'], stdout=subprocess.DEVNULL)
        container_created = True
        command(DOCKER+['start', name], stdout=subprocess.DEVNULL)
        follower = subprocess.Popen(DOCKER+['logs', '--follow', name], env=ENV,
                                    preexec_fn=die_with_parent)
        (RUNTIME/'active.json').write_text(json.dumps({'name': name, 'pid': os.getpid(),
                                                      'source': manifest.get('source_revision')}))
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
        print('Paper Vianden ready. Exit the shell to destroy this session.', flush=True)
        if args.check:
            command(DOCKER+['exec', name]+INNER+['exec', '-T', 'defender', 'python3',
                    '/opt/paper-vianden/runtime/check.py'])
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


def main():
    inner = len(sys.argv) > 1 and sys.argv[1] == '_session'
    if inner:
        sys.argv.pop(1)
        if os.geteuid() != 0 or os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
            raise RuntimeError('A private mount namespace is required.')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run', help='Start one foreground session; destroy it on exit')
    run.add_argument('--role', choices=['blue', 'red'], default='blue')
    run.add_argument('--check', action='store_true', help='Check services then destroy the session')
    attach = sub.add_parser('join', help='Join the active session; never starts a range')
    attach.add_argument('--role', choices=['blue', 'red', 'control'], default='blue')
    sub.add_parser('status', help='Show session state without starting anything')
    sub.add_parser('stop', help='Stop only the active Paper Vianden session')
    args = parser.parse_args()
    if args.command == 'status':
        active = RUNTIME/'active.json'
        running = subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet',
                                  'paper-vianden-session.service']).returncode == 0
        print(active.read_text() if running and active.exists() else ('Starting' if running else 'Stopped'))
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
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    for sig in [signal.SIGHUP, signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, interrupted)
    if inner:
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
