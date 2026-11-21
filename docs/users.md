# Using the disposable range

## Role-bound SSH access

For agent/human portal deployments, follow [SSH workstation access](ssh-access.md):
agent accounts enter blue directly, humans enter read-only white, and connections
share a human-reserved managed run that survives disconnects until its lease expires. The
operator-owned foreground workflow below remains supported separately.

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
./join-range --white
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
use different passwords for sysadmin. For internal campaign delivery, configure
its SMTP sender to use mail-sink.dmz:1025; mail stays in the captured inbox.

The blue key reaches the prototype Linux targets and custom FTP, mail, badge
and binary targets over SSH. Use control for other containers. Captures see the
interface on which you capture; there is no central mirror. The disposable
runtime includes a lightweight [synthetic user scenario](#simulated-users-and-storyline).

## Simulated users and storyline

```sh
./start-range --seed 42 --clock-speed 60 # reproducible 24-minute exercise variant
./start-range --seed 43 --clock-speed 60 # different behavioural variant
./start-range --clock-speed 3600        # fastest clock; protocol work can take minutes
```

Default speed is 1 (24 real hours); accepted multipliers are 1–3600. The clock
starts after service checks, at a fixed synthetic Monday 09:00 Luxembourg time,
independent of the host's date. Startup/seeding time is not accelerated. Requests
still use real network timeouts, so slow/broken targets can delay a fast rehearsal.
`--seed` accepts 0–4294967295 (default 20260112). It modulates workflow choices,
pauses, intensity and story timing through independent deterministic RNG streams.
Same seed/configuration replays planned variation; real latency and defender
changes mean captures will not be byte-for-byte identical. Different seeds are
behavioural versions of the same story, not different attack storylines.

`users-01` runs low-rate, jittered office workflows: portal/API browsing, SMB
reads, LDAP lookups, SQL reports, SSH `id -un`, captured mail and anonymous FTP.
Activity ramps with office hours, pauses for lunch and stops overnight. These
are protocol requests, not desktop/browser automation or separate employee VMs.

The independent, range-local storyline provides multiple investigation points
across authentication, discovery, account use, lateral access, staging and DNS.
Access uses public fixture accounts; exploitation/privilege escalation are
emulated, not malicious payloads or a real root compromise. All data is synthetic.
DNS timing is jittered around an underlying cadence rather than clockwork gaps;
other evidence remains detectable too. Use modest acceleration for timing work,
since real network latency and catch-up bursts can distort very fast rehearsals.

Inside the blue workstation:

```sh
cat /var/log/simulated-users/status.json
tail -n 20 /var/log/simulated-users/activity.jsonl
tail -n 20 /var/log/dns/queries.jsonl
```

The central `evidence` command and HTTP feed collect the observable logs; see
[demo operations](demo.md). Save agent findings under `/var/lib/soc-ai`.

The raw DNS journal mixes office lookups with other range-local DNS activity;
it contains timestamps, source IPs and query names, not attack labels or alerts.
Correlate it with actual target authentication/application/database logs, target
artifacts and packet captures. Capture on the relevant host/interface: there is
no whole-network traffic mirror, central alert feed, SOC dashboard or scoring.

The blue workstation deliberately has no mounted story source, schedule or
answer journal. [Instructor notes](scenario-instructors.md) contain spoilers;
keep those and control access out of black-box LLM evaluations. This avoids
accidental answer-key exposure, not a separate tenant security boundary.
Health checks do not require all workflows to succeed: defender actions can
legitimately break them. Normal teardown preserves bounded evidence archives outside the disposable session.

## Data and troubleshooting

Store findings under `/var/lib/soc-ai` and use the human export/download commands
in the [demo guide](demo.md). Normal teardown also attempts a bounded archive;
review its manifest and download important results before forced termination.

- No active range: its owner must explicitly start one.
- A session is already active: join it, or have its owner stop it.
- Startup failure: retain the diagnostic output; cleanup still runs.
- A lab name fails on your laptop: run the command inside the workstation.
- A modified service is broken: end the session and start fresh.

The unencapsulated development workflow has a separate [prototype guide](prototype.md).
