#!/usr/bin/env python3
"""Configure role-bound SSH portals on an already installed Debian range.

Administrator-only, opt-in SSH reload; preserves account passwords and keys.
No ports, Docker configuration, firewall rules or unrelated users are changed.
"""
import argparse
import grp
import json
import math
import os
from pathlib import Path
import pwd
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '# BEGIN PAPER VIANDEN WORKSTATION PORTALS'
END = '# END PAPER VIANDEN WORKSTATION PORTALS'
WRAPPER = Path('/usr/local/libexec/paper-vianden-ssh')
SSH_CONFIG = Path('/etc/ssh/sshd_config')


def account_name(value):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}', value):
        raise ValueError('Invalid account name')
    return value


def ssh_block(accounts):
    names = ','.join(account_name(name) for name in sorted(accounts))
    if not names:
        raise ValueError('At least one portal account is required')
    return f'''{BEGIN}
Match User {names}
    ForceCommand {WRAPPER}
    DisableForwarding yes
    PermitTTY yes
    MaxSessions 16
    PermitUserRC no
    PasswordAuthentication yes
    KbdInteractiveAuthentication no
{END}
'''


def replace_block(original, block):
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('Ambiguous existing managed SSH block')
    if BEGIN in original:
        before, rest = original.split(BEGIN, 1)
        _, after = rest.split(END, 1)
        if after.strip():
            raise ValueError('Managed SSH block must remain at EOF')
        original = before
    return original.rstrip()+'\n\n'+block


def owner_unit(seed, speed, lease_seconds):
    return f'''[Unit]
Description=Paper Vianden managed workstation owner

[Service]
Type=simple
ExecStart=/usr/bin/python3 -I /opt/paper-vianden/current/pv.py serve --seed {seed} --clock-speed {speed}
RuntimeMaxSec={lease_seconds}
TimeoutStopSec=180
KillMode=mixed
Restart=no
StandardOutput=journal
StandardError=journal
'''


def atomic(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.paper-', delete=False) as pending:
        temp = Path(pending.name)
        pending.write(content)
        os.fchmod(pending.fileno(), mode)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blue-account', required=True)
    parser.add_argument('--white-account')
    parser.add_argument('--seed', type=int, default=20260112)
    parser.add_argument('--clock-speed', type=float, default=1)
    parser.add_argument('--lease-hours', type=float, default=26)
    parser.add_argument('--max-sessions', type=int, default=16)
    parser.add_argument('--configure-ssh', action='store_true', required=True,
                        help='Explicitly authorize scoped sshd config change/reload')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Administrator privileges required')
    if not 0 <= args.seed <= 2**32-1 or not 1 <= args.clock_speed <= 3600 or not 0 < args.lease_hours <= 168:
        raise SystemExit('Seed, speed or lease is out of bounds')
    if not math.isfinite(args.lease_hours):
        raise SystemExit('Lease must be finite')
    if not 1 <= args.max_sessions <= 32:
        raise SystemExit('Use 1..32 concurrent workstation sessions')
    for path in (ROOT, ROOT/'pv.py', ROOT/'tools', ROOT/'runtime'):
        info = path.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise SystemExit('Run this from the root-owned installed release')
    if Path('/usr/local/bin/paper-vianden').resolve() != ROOT/'pv.py':
        raise SystemExit('Install/select this release before configuring portals')
    accounts = {}
    for name, role in ((args.blue_account, 'blue'), (args.white_account, 'white')):
        if not name:
            continue
        account_name(name)
        user = pwd.getpwnam(name)
        groups = {grp.getgrgid(user.pw_gid).gr_name} | {g.gr_name for g in grp.getgrall() if name in g.gr_mem}
        if user.pw_uid < 1000 or {'sudo', 'admin', 'docker', 'lxd', 'incus-admin'} & groups:
            raise SystemExit('Portal accounts must be existing unprivileged users')
        if name in accounts:
            raise SystemExit('Use different accounts for blue and white')
        accounts[name] = {'uid': user.pw_uid, 'role': role}
    subprocess.run(['/usr/sbin/sshd', '-t'], check=True)
    original = SSH_CONFIG.read_text()
    configured = replace_block(original, ssh_block(accounts))
    config = Path('/etc/paper-vianden')
    config.mkdir(mode=0o755, exist_ok=True)
    info = config.lstat()
    if config.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
        raise SystemExit('Unsafe portal configuration directory')
    atomic(config/'portals.json', json.dumps({'accounts': accounts,'max_sessions':args.max_sessions,
           'lease_minutes':max(1,round(args.lease_hours*60))}, indent=2)+'\n', 0o600)
    atomic(WRAPPER, '''#!/bin/sh
# Fixed role comes from root-owned UID policy, never client arguments.
exec /usr/bin/sudo -n /usr/local/bin/paper-vianden portal "--exec=${SSH_ORIGINAL_COMMAND-}"
''', 0o755)
    rule = ', '.join(accounts)+' ALL=(root) NOPASSWD: /usr/local/bin/paper-vianden portal --exec=*\n'
    candidate = config/'portal-sudoers.candidate'
    atomic(candidate, rule, 0o440)
    subprocess.run(['/usr/sbin/visudo', '-cf', str(candidate)], check=True)
    atomic(Path('/etc/sudoers.d/paper-vianden-portals'), rule, 0o440)
    candidate.unlink()
    atomic(Path('/etc/systemd/system/paper-vianden-owner.service'),
           owner_unit(args.seed, args.clock_speed, round(args.lease_hours*3600)), 0o644)
    # Protect host-side source too, not only workstation bind mounts.
    ROOT.chmod(0o700)
    if not (config/'sshd_config.before-portals').exists():
        atomic(config/'sshd_config.before-portals', original, 0o600)
    atomic(SSH_CONFIG, configured, 0o644)
    try:
        subprocess.run(['/usr/sbin/sshd', '-t'], check=True)
        subprocess.run(['/usr/bin/systemctl', 'daemon-reload'], check=True)
        subprocess.run(['/usr/bin/systemctl', 'reload', 'ssh'], check=True)
    except BaseException:
        atomic(SSH_CONFIG, original, 0o644)
        subprocess.run(['/usr/bin/systemctl', 'reload', 'ssh'], check=False)
        raise
    # Custom shell cannot source user-controlled bashrc before ForceCommand.
    for name in accounts:
        subprocess.run(['/usr/sbin/usermod', '--shell', str(WRAPPER), name], check=True)
        home = Path(pwd.getpwnam(name).pw_dir)
        home.chmod(0o700)
        if not home.is_symlink():
            path = home/'.hushlogin'
            if not path.exists():
                # Atomic replacement, never follow a user-controlled destination link.
                atomic(path, '', 0o644)
    print('Configured role-bound SSH portals. Passwords and keys were not changed.')
    print('Human range claim/start controls the exercise; agent logins only join it.')
    print('No boot enabling, independent runs, idle renewal or read-only SSH forwarding is provided.')


if __name__ == '__main__':
    main()
