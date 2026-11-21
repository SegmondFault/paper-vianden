# Using the disposable range

## Start and finish

Your operator supplies an SSH account and your own access key. From your computer:

```sh
ssh -t range-user@server.example
./range-status
./start-range
```

Startup loads offline images and seeds a fresh network; allow several minutes.
The owner receives a root shell in the **blue workstation**, not host root.
There is no LLM or agent framework. External tools can use this terminal
interface to gather information and administer training hosts.

```sh
hostname
ip address
getent hosts web-01.dmz db-01.internal
curl -fsS http://web-01.dmz/
ssh web-01.dmz hostname
ldapsearch -x -H ldap://ldap.internal -b dc=enum,dc=lab
```

`exit` in the owner's workstation destroys the session, including mutable files,
database edits, networks and generated lab keys. The next start restores fixtures.
Only one session can run per installation. Starting never fetches Git or images.

## Join an exercise

In another SSH login:

```sh
./join-range
./join-range --red
./join-range --control
```

Joining never starts anything. Leaving a joined shell does not end the owner's
session; the owner must stay connected. Ending it affects all participants.
The red workstation has tools and DMZ access but no blue administrator key.
Roles are conveniences within the lab, not separate tenant security boundaries.

The control console administers any lab container, including those without SSH.
Its Docker socket belongs to the inner daemon; the host socket is absent.

```sh
docker compose -p paper-vianden --profile extended -f prototype/docker-compose.yml -f compose.yaml ps
docker compose -p paper-vianden --profile extended -f prototype/docker-compose.yml -f compose.yaml logs --tail=30 ldap
docker compose -p paper-vianden --profile extended -f prototype/docker-compose.yml -f compose.yaml exec ldap bash
```

Use `exit` to leave control. From another login, `./stop-range` ends the session.
`./range-status` then says `Stopped`. For a protocol rehearsal use
`./start-range --check`; it destroys the session after success or failure.

## Find the services

These names resolve **inside the range**. No service port is published on the
server; the envelope has no external route. Browser forwarding is not yet
provided by the server wrapper. Use terminal HTTP clients for initial tests.

| Endpoint | Capability / synthetic access |
| --- | --- |
| web-01.dmz:80 | Intentionally weak PHP portal |
| vpn-gw-01.internal:22 | SSH gateway; sysadmin / admin123 |
| db-01.internal:3306 | MariaDB; root / S3cretDB!2024; five customer fixtures |
| file-01.internal:445 | Guest shares; confidential share sysadmin / FileShare#2024 |
| mail-01.dmz:8025 | HTTP mailbox mock; admin / MailP@ss2024 |
| app-01.internal:3000 | Training API |
| admin-01.internal:8080 | Admin panel; administrator / Admin!Panel99 |
| admin-01.internal:6379 | Redis without authentication |
| ldap.internal:389 | Anonymous enumeration; cn=admin,dc=enum,dc=lab / admin |
| ldap-admin.internal:80 | Directory administration UI |
| router.internal:161/udp | SNMP fixture; community public |
| ftp.dmz:21 | Anonymous read-only FTP; passive ports 30000–30009 |
| mail.internal:143,110 | IMAP / POP3; sysadmin / admin123 |
| mail-sink.dmz:1025,8025 | Captured SMTP and HTTP inbox; no external delivery |
| dvwa.dmz:80 | DVWA; admin / password; seeded SQL database |
| juice-shop.dmz:3000 | Juice Shop |
| phishing.dmz:3333,80 | Campaign administration and landing pages |
| badge.internal:80 | Badge-reader simulator |
| bof.internal:4444 | 32-bit teaching server; guest / letmein123 |

The campaign administrator's generated fixture password is in the control
console's `docker logs paper-vianden-phishing-1 2>&1`; it changes each session.
All listed passwords are public fixtures, not server credentials. SMB and SSH
use different passwords for sysadmin.

The blue key reaches the prototype Linux targets and custom FTP, mail, badge
and binary targets over SSH. Use control for other containers. Captures see the
interface on which you capture; there is no central mirror or user-traffic generator.

## Data and troubleshooting

Logs and captures inside the session disappear at teardown. Export anything
needed explicitly before ending it; evidence retention is not automatic.

- No active range: its owner must explicitly start one.
- A session is already active: join it, or have its owner stop it.
- Startup failure: retain the diagnostic output; cleanup still runs.
- A lab name fails on your laptop: run the command inside the workstation.
- A modified service is broken: end the session and start fresh.

The unencapsulated development workflow has a separate [prototype guide](prototype.md).
