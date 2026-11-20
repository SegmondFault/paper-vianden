#!/bin/bash
set -euo pipefail
mkdir -p /run/sshd /root/.ssh
chmod 700 /root/.ssh
if [ -s /run/blue-team.pub ]; then
    install -m 600 /run/blue-team.pub /root/.ssh/authorized_keys
fi
ssh-keygen -A >/dev/null
touch /var/log/auth.log
/usr/sbin/sshd -E /var/log/auth.log
cron
tail -n 0 -F /var/log/auth.log >&2 &
exec "$@"
