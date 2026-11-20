# User guide

## Available today

The local prototype is a Linux service network with seven targets, a management
workstation and an SSH relay. It can be started, inspected, modified and reset.
The Sysbox envelope and automatic session destruction are still planned. These
instructions use a dedicated local Docker engine, not the shared VPS.

## Get the source and check requirements

Use Linux, macOS with Docker Desktop, or WSL2 with a Linux Docker engine. Native
PowerShell launchers retained under prototype/ are upstream reference material.

```sh
git clone --recurse-submodules https://github.com/SegmondFault/paper-vianden.git
cd paper-vianden/prototype
python3 --version
docker version
docker compose version
ssh -V
```

Requirements: Python 3.9+, Git, OpenSSH tools and Docker Compose v2.20+. Check that
Docker is running and that its current context is your intended lab engine:

```sh
docker context show
```

The launcher uses that context unless RANGE_DOCKER_CONTEXT is set. For example,
export RANGE_DOCKER_CONTEXT=desktop-linux to choose an existing Docker Desktop
context. Do not select a shared production engine for this unencapsulated prototype.

## Build once, then start explicitly

```sh
./range init
./range config
./range build
./range up --no-build
./range check
./range status
./range login
```

init creates lab-only access keys under state/. config starts nothing and should
report nine services, 2016 MiB of summed RAM ceilings and 3.85 CPU ceilings. build
needs registry/package access on a cold cache; its resource use is outside those
runtime limits. up --no-build uses existing images without building or pulling.
It waits for healthy services. check prints PASS for normal connectivity and
administration checks, then login opens a shell on the management workstation.
A successful fresh build is not needed again until the source changes.

The prototype stays running after you leave that shell. Stop it using the command
in the shutdown section. Nothing starts on boot, login or a schedule; automatic
end-of-session destruction is not available yet.

## Find the services

These endpoints are reachable from inside the management workstation. The only
host-published entry is key-only SSH on 127.0.0.1:12222. The target ports below are
not published on the host.

| Service | Endpoint | Training access |
| --- | --- | --- |
| Portal | http://web-01.dmz/ | No login required |
| SSH gateway | vpn-gw-01.internal:22 | sysadmin / admin123 |
| MariaDB | db-01.internal:3306 | root / S3cretDB!2024 |
| Samba | file-01.internal:445 | Public/backups shares allow guests; confidential share uses sysadmin / FileShare#2024 |
| HTTP webmail mock | http://mail-01.dmz:8025/ | admin / MailP@ss2024 |
| Node API | http://app-01.internal:3000/ | Unauthenticated training endpoints |
| Admin panel | http://admin-01.internal:8080/ | administrator / Admin!Panel99 |
| Redis | admin-01.internal:6379 | No authentication |

All listed passwords and records are synthetic fixtures. SMB and Linux SSH use
different passwords for sysadmin. The gateway provides SSH forwarding, not an
actual VPN. Webmail does not deliver SMTP, IMAP or POP3 mail.

From the workstation, try:

```sh
curl -fsS http://web-01.dmz/
ssh web-01.dmz hostname
ssh vpn-gw-01.internal hostname
smbclient //file-01.internal/public -N -c ls
mariadb --skip-ssl -h db-01.internal -u root -p
```

SSH from that workstation to supported lab hosts uses its lab administrator key.
At the SQL prompt, USE acme_corp; and SELECT COUNT(*) FROM customers; should show
five seed customers in a fresh range. The example disables client TLS for the
local training database; it is not a production database configuration.

The management service is named defender in Compose. It is a normal SSH
workstation, with no AI agent or model runtime.

## Open the portal in your browser

From another terminal on your local computer, in the prototype directory:

```sh
ssh -i state/entry -p 12222 -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -o UserKnownHostsFile=state/known_hosts -o StrictHostKeyChecking=accept-new -N -L 127.0.0.1:18080:web-01.dmz:80 root@127.0.0.1
```

Leave that terminal open and visit http://127.0.0.1:18080/. Ctrl-C closes only the
forwarding connection. It does not stop the range. Use another unused local port
if 18080 is occupied. Forward other services by substituting an endpoint from
the table above.

## Inspect activity

From the workstation you can inspect a target over SSH, for example:

```sh
ssh web-01.dmz 'tail -n 20 /var/log/auth.log'
```

From the host terminal:

```sh
./range stats
./range collect
```

collect writes timestamped folders under prototype/runs/, including services.log,
container metadata, resolved configuration and source revision/status. These
records remain after shutdown and are ignored by Git. Review them before sharing.
MariaDB queries are also recorded in mysql.general_log. Packet captures see the
interface on which you capture; there is no whole-network traffic mirror or
central live evidence feed yet. There is no background user-traffic generator.

## Reset or shut down

Run these in the host terminal, not inside a target/workstation shell:

```sh
./range reset
./range check
```

reset saves records, removes this project's containers and data volumes, and
recreates its seeded targets from existing images. It discards uploaded files,
changed configurations and database edits. Access keys and earlier records remain.
Reset affects everyone using that instance.

To finish:

```sh
./range down --volumes
./range status
```

status should show no containers for this project. Images, keys under state/ and
saved runs remain cached locally. No global Docker prune is performed. Plain
down retains data volumes; use down --volumes for the documented clean shutdown.

## Team access and separate instances

For management access, append each person's own public key to
prototype/state/authorized_keys and apply it on a running range:

```sh
./range exec defender install -m 600 /run/entry.pub /root/.ssh/authorized_keys
```

Do not distribute private entry or administrator keys. Separate offensive-role
access is still pending. The current workstation has administrative reach into
both target segments.

A separate checkout gives an independent state/key directory. In that checkout,
set an unused project name and entry port before all lifecycle commands:

```sh
export RANGE_PROJECT=paper-vianden-alice
export BLUE_PORT=12223
```

Use that same environment for build, up, check, login, collect, reset and down.
The browser-forwarding example also needs -p 12223. In one checkout, changing the
project name alone does not create separate keys or state directories.

## Troubleshooting

| Symptom | Next check |
| --- | --- |
| Cannot connect to Docker | Check docker version and docker context show; start your local lab engine if needed. |
| docker compose is unavailable | Compose v2.20+ is required; the script does not install it automatically. |
| Image missing with up --no-build or reset | Run ./range build for the selected profile, then retry. |
| Startup reports an unhealthy service | Run ./range collect and inspect its services.log; stop failed startup with ./range down --volumes. |
| Port 12222 is occupied | Set BLUE_PORT to an unused port before starting and use it consistently. |
| A *.dmz or *.internal name does not resolve on your laptop | Those are range-local names; use the workstation or an SSH forward. |
| A reduced instance fails the full check | Use ./range check --minimal, or reset to the default full set. |
| Host key warning after reset | reset updates the local entry trust record; avoid manually trusting an unexpected host key. |

The --minimal option is for a four-target troubleshooting set. To switch an
already-running instance between sets, use reset with the intended option; up
does not remove services left from a previously larger set.

Source course guides under upstream/ are reference material pending integration.
Do not run their launchers directly on the shared VPS as if they used our envelope.
