FROM vulncastle-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    socat \
    iptables \
    proxychains4 \
    && rm -rf /var/lib/apt/lists/*

# This machine is dual-homed (DMZ + Internal)
# socat installed for pivoting exercises

# Weak SSH config + authorized_keys writable
RUN mkdir -p /home/sysadmin/.ssh \
    && chmod 777 /home/sysadmin/.ssh \
    && echo "sysadmin ALL=(ALL) NOPASSWD: /usr/bin/socat" >> /etc/sudoers

# SUID binary for privilege escalation
RUN cp /usr/bin/python3 /usr/local/bin/python3-suid \
    && chmod u+s /usr/local/bin/python3-suid

COPY config/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
