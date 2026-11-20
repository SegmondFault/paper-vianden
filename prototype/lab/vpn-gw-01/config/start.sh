#!/bin/bash
/usr/sbin/sshd
service cron start
tail -f /dev/null
