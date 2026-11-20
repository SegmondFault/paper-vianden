FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    net-tools \
    iputils-ping \
    iproute2 \
    dnsutils \
    cron \
    curl \
    wget \
    vim-tiny \
    ncat \
    sudo \
    openssh-server \
    python3 \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Create vulnerable users with weak passwords
RUN useradd -m -s /bin/bash sysadmin && echo "sysadmin:admin123" | chpasswd \
    && useradd -m -s /bin/bash devuser && echo "devuser:devuser2024" | chpasswd \
    && useradd -m -s /bin/bash backup  && echo "backup:backup"      | chpasswd \
    && useradd -m -s /bin/bash deploy  && echo "deploy:deploy!"     | chpasswd

# Setup SSH
RUN mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22
