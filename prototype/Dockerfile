# One build graph shares Linux/tooling layers across the target images.
FROM ubuntu:22.04 AS linux-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates net-tools iputils-ping iproute2 dnsutils cron curl \
    vim-tiny netcat-openbsd sudo openssh-server openssh-client python3 procps tcpdump \
    && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_* \
    && mkdir -p /run/sshd
COPY scripts/node-init.sh /usr/local/bin/node-init
RUN chmod +x /usr/local/bin/node-init

FROM linux-base AS target-base
# These weak accounts are part of the upstream training environment.
RUN useradd -m -s /bin/bash sysadmin && echo 'sysadmin:admin123' | chpasswd \
    && useradd -m -s /bin/bash devuser && echo 'devuser:devuser2024' | chpasswd \
    && (id -u backup >/dev/null 2>&1 || useradd -m -s /bin/bash backup) \
    && usermod -d /home/backup -s /bin/bash backup \
    && mkdir -p /home/backup && chown backup:backup /home/backup \
    && echo 'backup:backup' | chpasswd \
    && useradd -m -s /bin/bash deploy && echo 'deploy:deploy!' | chpasswd \
    && printf 'PermitRootLogin prohibit-password\nPasswordAuthentication yes\nLogLevel VERBOSE\n' > /etc/ssh/sshd_config.d/00-range.conf
ENTRYPOINT ["/usr/local/bin/node-init"]

FROM target-base AS web
RUN apt-get update && apt-get install -y --no-install-recommends nginx php-fpm php-mysql php-xml php-curl \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's@^listen = .*@listen = /run/php/php-fpm.sock@; s/^pm = .*/pm = ondemand/; s/^pm.max_children = .*/pm.max_children = 2/' /etc/php/8.1/fpm/pool.d/www.conf \
    && sed -i 's/^worker_processes .*/worker_processes 1;/' /etc/nginx/nginx.conf \
    && ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log
COPY lab/web-01/app/ /var/www/html/
COPY lab/web-01/config/nginx.conf /etc/nginx/sites-available/default
RUN chmod -R 777 /var/www/html/uploads \
    && echo 'sysadmin ALL=(ALL) NOPASSWD: /usr/bin/find' >> /etc/sudoers \
    && printf '#!/bin/bash\ntar czf /backups/www-backup.tar.gz /var/www/html/\n' > /opt/backup.sh \
    && chmod 777 /opt/backup.sh && mkdir -p /backups \
    && echo '*/5 * * * * root /opt/backup.sh' >> /etc/crontab
CMD ["bash", "-ec", "mkdir -p /run/php; php-fpm8.1 -D; exec nginx -g 'daemon off;'"]

FROM target-base AS gateway
RUN apt-get update && apt-get install -y --no-install-recommends socat iptables proxychains4 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/sysadmin/.ssh && chmod 777 /home/sysadmin/.ssh \
    && echo 'sysadmin ALL=(ALL) NOPASSWD: /usr/bin/socat' >> /etc/sudoers \
    && cp /usr/bin/python3 /usr/local/bin/python3-suid && chmod u+s /usr/local/bin/python3-suid
CMD ["tail", "-f", "/dev/null"]

FROM target-base AS fileserver
RUN apt-get update && apt-get install -y --no-install-recommends samba \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /srv/share/public /srv/share/confidential /srv/share/backups \
    && chmod 777 /srv/share/public && chmod 755 /srv/share/confidential /srv/share/backups \
    && printf 'Budget Report Q4 2024\nTotal Revenue: $4.2M\nNet Profit: $1.1M\n' > /srv/share/confidential/budget_q4.txt \
    && printf 'sysadmin:admin123\ndevuser:devuser2024\nbackup:backup\ndeploy:deploy!\n' > /srv/share/confidential/passwords.txt \
    && printf 'FAKE-KEY-FOR-TRAINING-PURPOSES-ONLY\n' > /srv/share/confidential/id_rsa_deploy \
    && echo 'Welcome to ACME Corp file share!' > /srv/share/public/welcome.txt \
    && printf 'FileShare#2024\nFileShare#2024\n' | smbpasswd -a -s sysadmin
COPY lab/file-01/config/smb.conf /etc/samba/smb.conf
CMD ["bash", "-ec", "nmbd -D; exec smbd --foreground --no-process-group --debug-stdout"]

FROM mariadb:10.11 AS database
ENV MYSQL_ROOT_PASSWORD=S3cretDB!2024 MYSQL_DATABASE=acme_corp MYSQL_USER=app_user MYSQL_PASSWORD=S3cretDB!2024
COPY lab/db-01/sql/init.sql /docker-entrypoint-initdb.d/

FROM target-base AS webmail
COPY lab/mail-01/config/webmail.py /opt/webmail/app.py
ENV SMTP_USER=admin SMTP_PASS=MailP@ss2024 SECRET_KEY=super-secret-key-do-not-share
RUN echo 'devuser ALL=(ALL) NOPASSWD: /usr/bin/python3' >> /etc/sudoers
CMD ["python3", "-u", "/opt/webmail/app.py"]

FROM target-base AS api
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/api
COPY lab/app-01/app/ /opt/api/
RUN npm install --omit=dev
CMD ["node", "server.js"]

FROM target-base AS admin
RUN apt-get update && apt-get install -y --no-install-recommends redis-server \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's/^bind .*/bind 0.0.0.0/; s/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf \
    && printf '#!/bin/bash\necho "Health check: $(date)" >> /var/log/health.log\n' > /opt/healthcheck.sh \
    && chmod 777 /opt/healthcheck.sh \
    && echo '* * * * * root /opt/healthcheck.sh' >> /etc/crontab
COPY lab/admin-01/app/admin_panel.py /opt/admin/app.py
CMD ["bash", "-ec", "redis-server /etc/redis/redis.conf --maxmemory 32mb --maxmemory-policy allkeys-lru --daemonize yes; exec python3 -u /opt/admin/app.py"]

FROM linux-base AS workstation
RUN apt-get update && apt-get install -y --no-install-recommends tcpdump jq smbclient mariadb-client \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.ssh \
    && printf 'PermitRootLogin prohibit-password\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n' > /etc/ssh/sshd_config.d/00-range.conf \
    && printf 'Host *.dmz *.internal\n    User root\n    IdentityFile /root/.ssh/id_ed25519\n    StrictHostKeyChecking accept-new\n' > /root/.ssh/config
COPY scripts/workstation-init.sh /usr/local/bin/workstation-init
RUN chmod +x /usr/local/bin/workstation-init
ENTRYPOINT ["/usr/local/bin/workstation-init"]

FROM linux-base AS entry
RUN apt-get update && apt-get install -y --no-install-recommends socat && rm -rf /var/lib/apt/lists/*
USER 65534:65534
CMD ["socat", "TCP-LISTEN:10222,fork,reuseaddr", "TCP:defender:22"]
