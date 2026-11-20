FROM vulncastle-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    && rm -rf /var/lib/apt/lists/*

COPY config/smb.conf /etc/samba/smb.conf

# Create shared directories
RUN mkdir -p /srv/share/public /srv/share/confidential /srv/share/backups \
    && chmod 777 /srv/share/public \
    && chmod 755 /srv/share/confidential \
    && chmod 755 /srv/share/backups

# Add some interesting files
RUN echo "Budget Report Q4 2024\nTotal Revenue: $4.2M\nNet Profit: $1.1M" > /srv/share/confidential/budget_q4.txt \
    && echo "sysadmin:admin123\ndevuser:devuser2024\nbackup:backup\ndeploy:deploy!" > /srv/share/confidential/passwords.txt \
    && echo "-----BEGIN RSA PRIVATE KEY-----\nFAKE-KEY-FOR-TRAINING-PURPOSES-ONLY\n-----END RSA PRIVATE KEY-----" > /srv/share/confidential/id_rsa_deploy \
    && echo "Welcome to ACME Corp file share!" > /srv/share/public/welcome.txt

# Set Samba passwords
RUN (echo "FileShare#2024"; echo "FileShare#2024") | smbpasswd -a -s sysadmin

COPY config/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 139 445

CMD ["/start.sh"]
