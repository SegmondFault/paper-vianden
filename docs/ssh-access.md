# SSH access and exercise ownership

Distinct human, blue, red and green Unix accounts are bound by UID/name to their fixed workstation.
Clients cannot select roles, forward ports, transfer host files via SFTP, or
execute arbitrary host processes. Commands are single arguments to `bash -lc`
inside the workstation. Models and SOC orchestration run elsewhere.

```sh
ssh agent@range.example 'hostname'
ssh -t agent@range.example
ssh human@range.example 'range status'
ssh human@range.example 'observe status'
```

Blue administers lab targets, without host Docker or private instructor journals.
White is an unprivileged observer with read-only journal mounts, no administrator
key and no target interfaces. Its narrowly parsed `range` commands control the
lifecycle through the host portal; ordinary shell commands stay in white.

A human runs `range claim` to create a named, time-limited reservation. The
command prints a reservation code in its JSON `token` field; the human keeps
that code and supplies it with the existing `--token` option to
start/reset/stop/release the one shared exercise. See the
[operator quickstart](../OPERATOR_QUICKSTART.md#1-reserve-the-exercise) for the
exact commands. Agent accounts do not need the reservation code.
Agent logins never start scenarios. The reservation is independent of SSH
sessions: 16 concurrent workstation sessions per account are allowed by default.
A UID-bound slot limit caps connections globally; SSH MaxSessions is 16 per
transport. Coordinate conflicting changes to shared hosts. Disconnects do not
stop the managed owner. Lease expiry stops it; there is no boot-time start.

See the [demo guide](demo.md) for claims, central evidence, exports and a
scripted containment rehearsal. The 24-hour storyline becomes idle when complete;
a human reset creates fresh fixtures. Per-user concurrent networks, lease renewal
and tenant isolation are not provided. Sysbox shares the host kernel.

## Administrator installation

First install a prepared root-owned release and create two unprivileged Unix
accounts. Configure their passwords/authorized keys separately; the installer
preserves them and rejects privileged or Docker-group accounts.

```sh
sudo python3 /opt/paper-vianden/current/tools/install_portals.py \
  --blue-account blue-agent --white-account human \
  --red-account red-agent --green-account green-agent \
  --seed 42 --clock-speed 60 --lease-hours 26 --max-sessions 16 --configure-ssh
```

This validates a scoped EOF-managed Match User block and reloads SSH. It installs
a root-owned forced shell, UID/role policy, narrow portal sudo rule and an
unenabled owner service. Host Docker is not reconfigured or restarted. Keep an
administrator connection open until both portals have been checked. Backup and
policy files remain under `/etc/paper-vianden`; release source is root-private.
Human claims cannot exceed the configured maximum lease (26 hours by default).

Stop the owner before explicitly installing an update and reconfiguring portals;
Git pulls do not deploy releases. Administrators can stop
`paper-vianden-owner.service` for recovery. Legacy foreground operator commands
remain available; the full `--control` console must stay out of model context.
Archives include private instructor truth as well as SOC findings, so give them
to the demo owner. Forced termination/host failure can interrupt export.
