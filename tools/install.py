#!/usr/bin/env python3
"""Install a prepared release and restricted account, without starting services.

Administrator action only. Does not run package maintainer scripts, apt, global
Docker reconfiguration, service restarts, sysctl changes or boot-time enabling.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tarfile
import tempfile


def run(*args):
    subprocess.run(args, check=True)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--public-key', type=Path, required=True)
    parser.add_argument('--account', default='range-user')
    args = parser.parse_args()
    if os.geteuid() != 0: raise SystemExit('Administrator privileges required.')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}', args.account): raise SystemExit('Invalid account name')
    for tool in ['docker', 'dockerd', 'containerd', 'mkfs.ext4', 'mount', 'unshare', 'systemd-run', 'visudo', 'dpkg-deb']:
        if not shutil.which(tool): raise SystemExit('Required existing tool missing: '+tool)
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'paper-vianden-session.service']).returncode == 0:
        raise SystemExit('Stop the current range before updating its release.')
    bundle = args.bundle.resolve(); manifest = json.loads((bundle/'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if Path(name).name != name or sha(bundle/name) != expected:
            raise SystemExit('Bundle checksum mismatch')
    public = args.public_key.read_text().strip()
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?', public):
        raise SystemExit('Expected one Ed25519 public key')
    prefix = Path('/opt/paper-vianden'); store = Path('/var/lib/paper-vianden')
    prefix.mkdir(mode=0o755, exist_ok=True); store.mkdir(mode=0o700, exist_ok=True)
    for path in [prefix, store]:
        info = path.lstat()
        if path.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise SystemExit('Unsafe installation directory')
    record = store/'operator.json'
    new_operator = False
    try:
        operator = pwd.getpwnam(args.account)
        if not record.exists() or json.loads(record.read_text())['account'] != args.account:
            raise SystemExit('Account already exists and is not managed by this installation.')
    except KeyError:
        run('useradd', '--create-home', '--user-group', '--shell', '/bin/bash', args.account)
        operator = pwd.getpwnam(args.account)
        new_operator = True
    try:
        pwd.getpwnam('sysbox')
    except KeyError:
        run('useradd', '--no-create-home', '--user-group', '--shell', '/usr/sbin/nologin', 'sysbox')
    release = prefix/('release-'+manifest['files']['source.tar.gz'][:12])
    if not release.exists():
        release.mkdir(mode=0o755)
        with tarfile.open(bundle/'source.tar.gz') as archive:
            for member in archive.getmembers():
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise SystemExit('Unsafe source archive entry')
            archive.extractall(release)
        for base, dirs, files in os.walk(release):
            os.chmod(base, 0o755)
            for name in files: os.chmod(Path(base)/name, 0o644)
        runtime = release/'runtime/bin'; runtime.mkdir(mode=0o755, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='paper-runtime-') as temp:
            run('dpkg-deb', '--extract', str(bundle/'sysbox.deb'), temp)
            for name in ['sysbox-mgr', 'sysbox-fs', 'sysbox-runc']:
                shutil.copyfile(Path(temp)/'usr/bin'/name, runtime/name)
                (runtime/name).chmod(0o755)
            shutil.copyfile(Path(temp)/'usr/share/doc/sysbox-ce/copyright', runtime/'COPYRIGHT')
        with tempfile.TemporaryDirectory(prefix='paper-fuse-') as temp:
            run('dpkg-deb', '--extract', str(bundle/'fuse3.deb'), temp)
            shutil.copyfile(Path(temp)/'bin/fusermount3', runtime/'fusermount3')
            (runtime/'fusermount3').chmod(0o755)
            shutil.copyfile(Path(temp)/'usr/share/doc/fuse3/copyright', runtime/'FUSE_COPYRIGHT')
        (release/'pv.py').chmod(0o755)
    # Archives preserve the builder's numeric UID when extracted by root.
    # Never carry that identity into a privileged deployed release.
    for base, dirs, files in os.walk(release):
        os.chown(base, 0, 0)
        for name in files:
            os.chown(Path(base)/name, 0, 0)
    library = store/'library'; library.mkdir(mode=0o755, exist_ok=True)
    for name in ['envelope.tar.gz', 'targets.tar.gz', 'manifest.json']:
        shutil.copyfile(bundle/name, library/name)
        (library/name).chmod(0o644)
    current = prefix/'current'; pending = prefix/'next'
    pending.unlink(missing_ok=True); pending.symlink_to(release.name, target_is_directory=True)
    pending.replace(current)
    launcher = Path('/usr/local/bin/paper-vianden')
    if launcher.exists() and not launcher.is_symlink(): raise SystemExit('Launcher path is occupied')
    launcher.unlink(missing_ok=True); launcher.symlink_to(current/'pv.py')
    home = Path(operator.pw_dir)
    if new_operator:
        ssh = home/'.ssh'; ssh.mkdir(mode=0o700, exist_ok=True)
        authorized = ssh/'authorized_keys'; authorized.write_text(public+'\n'); authorized.chmod(0o600)
        os.chown(ssh, operator.pw_uid, operator.pw_gid); os.chown(authorized, operator.pw_uid, operator.pw_gid)
    # Existing SSH access is operator-managed. Updates must not remove teammates.
    for name in ['start-range', 'join-range', 'stop-range', 'range-status']:
        with tempfile.NamedTemporaryFile(dir=home, prefix='.range-script-', delete=False) as staged:
            pending_script = Path(staged.name)
            with (release/'scripts'/name).open('rb') as source:
                shutil.copyfileobj(source, staged)
            os.fchmod(staged.fileno(), 0o755)
        try:
            # Replace a user-controlled destination link rather than following it.
            pending_script.replace(home/name)
        finally:
            pending_script.unlink(missing_ok=True)
    rule = args.account+' ALL=(root) NOPASSWD: '+', '.join('/usr/local/bin/paper-vianden '+command for command in
               ['run', 'run --role red', 'run --check', 'run --clock-speed *', 'join', 'join --role red',
                'join --role control', 'stop', 'status'])+'\n'
    with tempfile.NamedTemporaryFile(mode='w', prefix='paper-sudo-', delete=False) as temp:
        temp.write(rule); candidate = Path(temp.name)
    try:
        run('visudo', '-cf', str(candidate))
        sudoers = Path('/etc/sudoers.d/paper-vianden'); shutil.copyfile(candidate, sudoers); sudoers.chmod(0o440)
    finally:
        candidate.unlink()
    record.write_text(json.dumps({'account': args.account, 'uid': operator.pw_uid,
                                  'source_revision': manifest['source_revision']})+'\n')
    record.chmod(0o600)
    print('Installed the release and restricted scripts. Range remains stopped.')


if __name__ == '__main__':
    main()
