#!/bin/bash
/usr/sbin/sshd
cd /opt/webmail && python3 app.py &
service cron start
tail -f /dev/null
