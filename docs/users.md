# User guide

## What is available now

The prototype is a Linux service network with a portal, SSH gateway, database,
file shares, simulated webmail, API, admin panel and Redis. An SSH management
workstation can administer both target segments. Model hosting and agent
development are outside this project.

The final disposable-session command is not available yet. The commands below
operate the prototype directly on your selected Docker engine. Use a dedicated
local lab engine; deployment on a shared server awaits the Sysbox envelope.

## Local prototype

Requirements: Python 3.9+, OpenSSH tools, Docker with Linux containers and Compose
v2.20+. From the prototype directory:

```sh
./range init
./range config
./range up
./range check
./range login
```

The default starts all seven targets. A reduced troubleshooting set is available
with --minimal. The entry is key-only SSH on 127.0.0.1:12222. Target ports are not
published on the host. For a different port, set BLUE_PORT before invocation.

Inside the management workstation:

```sh
ssh web-01.dmz
ssh vpn-gw-01.internal
ssh file-01.internal
smbclient //file-01.internal/public -N
mariadb -h db-01.internal -u root -p
```

All target records, accounts and credentials are training fixtures. Their
details are in prototype/UPSTREAM.md and the service source.

## Evidence, reset and stop

```sh
./range collect
./range reset
./range down --volumes
```

collect saves logs and container/configuration records under the local runs
directory. reset first saves those records, removes this project's containers
and volumes, then recreates seeded targets from the existing images. It retains
access keys. down --volumes saves records and removes the running project and
its data volumes. Cached images, local keys and saved records remain.

There is no automatic startup or restart policy. Once explicitly started, this
prototype remains running until stopped; exiting the SSH workstation alone does
not destroy it. Automatic end-of-session destruction is planned for the envelope.

## Team access

Each person uses their own public SSH key. Append allowed public keys to
prototype/state/authorized_keys and apply them on a running prototype:

```sh
./range exec defender install -m 600 /run/entry.pub /root/.ssh/authorized_keys
```

The service named defender is an ordinary management workstation, not an agent.
Its administrative key is for the lab targets. Separate offensive participant
access remains to be integrated; that role should not receive the administrator
key. Reset currently affects everyone sharing that instance.

Keep private keys, real datasets and external API credentials out of targets.
This repository contains no server login credentials.
