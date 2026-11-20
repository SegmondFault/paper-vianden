FROM vulncastle-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/api
COPY app/ /opt/api/

RUN cd /opt/api && npm install

# API runs as root (misconfiguration)
# SSRF and IDOR vulnerabilities in the API

COPY app/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 3000

CMD ["/start.sh"]
