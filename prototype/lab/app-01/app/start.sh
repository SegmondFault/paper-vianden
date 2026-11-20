#!/bin/bash
/usr/sbin/sshd
cd /opt/api && node server.js &
service cron start
tail -f /dev/null
