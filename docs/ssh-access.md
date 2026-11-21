# SSH workstation portals

The application exposes terminal environments, not an LLM API. Bring your own
agent architecture and an SSH tool. A human and an agent use separate Unix
accounts/credentials on the same SSH port; the server fixes each account's role.
The examples below use placeholders, not access credentials.

## Agent: blue workstation

```sh
ssh -t agent@range.example
```

Authentication leads directly to the blue workstation shell. No host shell,
role menu, instructor journal or host Docker socket is provided. Root in blue is
container root, not VPS root. Investigation tools and target-network access are
available there. For command-per-connection architectures:

```sh
ssh agent@range.example 'hostname; id; ip -brief address'
```

The command is passed as one argument to `bash -lc` **inside blue**, never to a
privileged host shell. Interactive SSH should request a PTY (`ssh -t` or the
client library's equivalent). Noninteractive commands also work without a PTY.
Each account permits **one active workstation session**, enforced across SSH
connections by a UID-bound lock as well as a per-connection channel limit. A
second concurrent login is rejected; after disconnect, the slot is released.
Blue and white use different accounts and can connect simultaneously. Agent
architectures must serialize SSH tool calls. An authenticated SSH transport with
no open workstation channel does not hold a slot.

SSH forwarding is disabled. The portal cannot select another role or start an
arbitrary host process. SFTP commands, if requested, cannot provide a host-file
transfer channel; export evidence through workstation stdout instead.

## Human: white workstation

```sh
ssh -t observer@range.example
observe status
observe story --tail 30
observe dns --tail 30
observe activity --tail 30
observe status --watch
observe snapshot
```

Or run an observation command directly:

```sh
ssh observer@range.example 'observe status'
```

White is an unprivileged, read-only workstation with read-only journal mounts,
no administrator key or Docker socket, and no DMZ/internal target interfaces.
It sees private ground truth and objective progress in addition to raw evidence.
These are not mounted into blue. `--watch` refreshes every two seconds; Ctrl-C
ends observation, not the exercise. Snapshots can be redirected to a file on the
human's computer. White does not administer, reset or terminate the range.
This is an observation view, not a whole-network packet mirror or SOC dashboard.

## Automatic lifecycle

The first portal login starts the root-managed owner service if needed. Startup
loads offline images and checks protocols; allow several minutes. Subsequent
SSH connections join the same run. Closing blue/white connections does not end
it. No instructor needs to keep an SSH owner terminal open.

A fixed real-time lease defaults to 26 hours, including startup. Its expiry
stops the owner and cleans the disposable range. Nothing is enabled at boot.
The scenario itself spans 24 simulated hours; clock speed is selected by the
administrator and does not accelerate network operations or the lease timer.

**Current limits:** one shared run, not isolated simultaneous experiments; no
per-user leases, idle timeout, lease renewal, or participant reset endpoint.
All portal users of a role share that workstation, but a single account cannot
have concurrent workstation sessions. A new login after lease
expiry starts a fresh run using the configured seed/speed. Separate SSH accounts
provide role/access separation, not separate training networks. Containers share
a kernel; this is not a hardened multi-tenant service.

## Administrator setup

An administrator must first install a prepared release and create two distinct,
unprivileged Unix accounts. Portal configuration requires existing accounts;
it does not set passwords, copy private keys, or grant Docker/group/general-sudo
access. Install SSH public keys or set passwords separately. Keys are preferred.

From the VPS administrator account:

```sh
sudo python3 /opt/paper-vianden/current/tools/install_portals.py \
  --blue-account agent --white-account observer \
  --seed 42 --clock-speed 1 --lease-hours 26 --configure-ssh
```

The tool validates SSH configuration before and after a scoped change and
reloads `ssh`, not host Docker. It preserves passwords and authorized keys. It
adds an EOF-managed `Match User` block, disables forwarding/user SSH rc scripts,
sets a root-owned custom login shell, installs a UID-bound portal policy and a
narrow sudo rule for the portal only. The custom shell does not source a
user-controlled bashrc on the VPS. Installed release source is root-private to
avoid host-side answer-key exposure. Password authentication is enabled for the
selected portal accounts; deployment policy and key management remain the
administrator's responsibility.

Hold an administrator session open until both new logins have been verified.
The SSH backup is `/etc/paper-vianden/sshd_config.before-portals`; the active
UID/role policy is `/etc/paper-vianden/portals.json` (root-only). Neither contains
passwords. Do not give an agent administrator credentials or observer keys.

Useful administrator commands:

```sh
sudo systemctl status paper-vianden-owner.service paper-vianden-session.service
sudo journalctl -u paper-vianden-owner.service --no-pager -n 60
sudo systemctl stop paper-vianden-owner.service
```

Stopping the owner tears down the current run. The next portal login starts a
fresh one. Stop before installing/updating a release. To change the next run's
seed, speed or lease, rerun portal configuration with new options, then explicitly
stop the old owner. The legacy `start-range` foreground mode remains available
for operators; unlike managed portals, exiting its owner shell destroys it.

The existing `--control` console is full administration, not read-only white.
Keep it and the public source/instructor guide out of black-box agent context.
Separation reduces accidental setup/answer leakage; synthetic artifacts can
still reveal that this is a training environment.
