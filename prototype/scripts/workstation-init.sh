#!/bin/bash
set -euo pipefail
test -s /run/entry.pub
mkdir -p /run/sshd /root/.ssh
chmod 700 /root/.ssh
install -m 600 /run/entry.pub /root/.ssh/authorized_keys
ssh-keygen -A >/dev/null
exec /usr/sbin/sshd -D -e
