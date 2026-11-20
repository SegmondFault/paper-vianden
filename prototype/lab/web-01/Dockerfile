FROM vulncastle-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    php-fpm \
    php-mysql \
    php-xml \
    php-curl \
    && rm -rf /var/lib/apt/lists/*

# Vulnerable PHP app
COPY app/ /var/www/html/
COPY config/nginx.conf /etc/nginx/sites-available/default

# Intentional misconfigurations
RUN chmod -R 777 /var/www/html/uploads \
    && echo "sysadmin ALL=(ALL) NOPASSWD: /usr/bin/find" >> /etc/sudoers

# Cron job with world-writable script (privesc vector)
RUN echo '#!/bin/bash\ntar czf /backups/www-backup.tar.gz /var/www/html/' > /opt/backup.sh \
    && chmod 777 /opt/backup.sh \
    && mkdir -p /backups \
    && echo "*/5 * * * * root /opt/backup.sh" >> /etc/crontab

COPY config/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80

CMD ["/start.sh"]
