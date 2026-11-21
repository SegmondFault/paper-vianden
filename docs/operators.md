# Operator guide

## Prepare a release

Use a development Docker 28+ engine supporting Linux amd64, Git, Python 3.9+ and
modern Compose with `!reset` overlays. Build away from the shared server:

```sh
git clone --recurse-submodules https://github.com/SegmondFault/paper-vianden.git
cd paper-vianden
python3 tools/check_public_tree.py --history
python3 tools/build_bundle.py --context default
```

This builds shared layers and service images, exports compressed images and
packages tracked public source. The pinned Sysbox package is SHA-256 verified.
The ignored artifacts/ directory contains the bundle and checksum manifest.
Keep the upstream dependency clean at its recorded revision. `--skip-build`
reuses target images; the envelope is still rebuilt.

## Install explicitly

The initial target is Debian 12 Linux amd64 with cgroup v2, user namespaces,
FUSE and an existing compatible Docker engine. Allow 34 GiB free disk for the
bounded session filesystem, separately from the prepared image library.
The installer does not install or upgrade the host Docker engine.

Transfer the bundle, tools/install.py and the operator's **public** Ed25519 key
using existing administrator access. Keep the private key on the operator's
computer. On the server:

```sh
sudo python3 tools/install.py --bundle /path/to/bundle --public-key /path/to/operator.pub --account range-user
```

The installer verifies hashes, creates a restricted account and Sysbox subordinate
ID account, extracts only runtime binaries and a licence notice from the package,
and installs a root-owned release. It does not run package maintainer scripts,
apt, sysctl, Docker restarts or boot-time enabling.

| Path | Purpose |
| --- | --- |
| /opt/paper-vianden/release-* | Root-owned source and runtime binaries |
| /opt/paper-vianden/current | Selected release |
| /var/lib/paper-vianden/library | Prepared images and manifest |
| /usr/local/bin/paper-vianden | Fixed privileged launcher |
| /etc/sudoers.d/paper-vianden | Exact permitted commands |
| /run/paper-vianden | Ephemeral session control state |
| Operator home | start-range, join-range, stop-range, range-status |

No Docker-group membership, password or general sudo is granted. Existing
unmanaged accounts are refused. Never run privileged code from a user-writable
checkout.

## Validate

Record the original service state and Docker PID/start time. In the new account
run `./range-status`, then `./start-range --check`. All protocols must pass,
cleanup must complete and status must return `Stopped`. Confirm that original
Docker and unrelated workloads kept their PID/start/restart state. Test shell
exit, explicit stop and fresh fixture restoration before shared use.

Only one session is allowed. Joining cannot start it. The control console
manages inner containers without exposing the host socket. Users must export
needed evidence explicitly before stopping.

## Update from Git

Keep the ordinary checkout tracking origin/main separate from the root release:

```sh
git status --short
git fetch origin
git log --oneline HEAD..origin/main
git pull --ff-only
git submodule update --init --recursive
```

Review the revision, rebuild its bundle, stop an active range and rerun the
installer explicitly. A pull changes source only; it neither installs nor starts
the range. Invocations never pull Git or images. No cron, boot or login hooks
start the range. Avoid global Docker prune or shared-daemon reconfiguration.

## Recovery

`sudo systemctl stop paper-vianden-session.service` targets the range only.
Failed startup prints diagnostic helper log tails before deleting its disk.
Investigate any cleanup failure before another start. Never stop host Docker
to recover this range. Startup refuses if another Sysbox instance is already
running. No shared-host reboot is part of installation or validation.
