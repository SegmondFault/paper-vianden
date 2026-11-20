FROM vulncastle-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Redis with no authentication (intentional misconfiguration)
RUN sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf \
    && sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf

# Admin panel (Python)
COPY app/admin_panel.py /opt/admin/app.py

# Writable cron job (privilege escalation)
RUN echo '#!/bin/bash\necho "Health check: $(date)" >> /var/log/health.log' > /opt/healthcheck.sh \
    && chmod 777 /opt/healthcheck.sh \
    && echo "* * * * * root /opt/healthcheck.sh" >> /etc/crontab

COPY app/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 6379 8080

CMD ["/start.sh"]
