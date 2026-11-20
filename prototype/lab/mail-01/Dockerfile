FROM vulncastle-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Vulnerable webmail app (Python Flask)
COPY config/webmail.py /opt/webmail/app.py
COPY config/start.sh /start.sh
RUN chmod +x /start.sh

# Leaked credentials in environment
ENV SMTP_USER=admin
ENV SMTP_PASS=MailP@ss2024
ENV SECRET_KEY=super-secret-key-do-not-share

# Weak sudo config
RUN echo "devuser ALL=(ALL) NOPASSWD: /usr/bin/python3" >> /etc/sudoers

EXPOSE 25 8025

CMD ["/start.sh"]
