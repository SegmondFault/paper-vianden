#!/bin/bash
/usr/sbin/sshd
redis-server /etc/redis/redis.conf --daemonize yes
cd /opt/admin && python3 app.py &
service cron start
tail -f /dev/null
