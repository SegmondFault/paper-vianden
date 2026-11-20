#!/bin/bash
service php*-fpm start
service cron start
/usr/sbin/sshd
nginx -g "daemon off;"
