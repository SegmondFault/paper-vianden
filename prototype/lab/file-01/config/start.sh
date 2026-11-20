#!/bin/bash
/usr/sbin/sshd
service smbd start
service nmbd start
service cron start
tail -f /dev/null
