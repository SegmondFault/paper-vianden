# Architecture

```text
SSH operator (no Docker group; fixed sudo commands)
  Python launcher
    transient systemd service — explicit invocation only
      private mount namespace + bounded disposable filesystem
      dedicated Docker daemon + private Sysbox helpers
        Sysbox envelope — no external network, 4 CPUs, 6 GiB RAM
          inner Docker daemon + offline images
            management: blue workstation
            DMZ: participant workstation + exposed fixtures
            internal: database, directory, file and other services
```

Host Docker is separate and never restarted or reconfigured. The dedicated
daemon has no bridge, firewall management, forwarding or masquerading. Its only
container has network=none. Inner bridges and rules belong to that container's
network namespace. No target port is published on the host. The only host bind
in the envelope is the read-only target image archive.

## Lifecycle

The owner takes a singleton lock and starts a transient service. It verifies
image checksums, creates a sparse 32 GiB ext4 disk, launches private helpers,
loads the offline network and checks actual protocols before opening a shell.
Joining only connects to an existing session.

Owner exit, startup errors and terminal signals invoke cleanup. systemd owns
the entire helper/container cgroup and kills descendants when the unit ends.
Where available it also binds the unit to the caller's login scope. Mounts are
private. The backing file is unlinked immediately after mounting so a forced
exit cannot leave a named session disk. Explicit stop targets this unit only.
Power-loss recovery requires a separate reboot test; no reboot is performed.

## Boundaries

The whole service has caps of 4 CPUs, 7 GiB RAM, zero swap and 4,096 tasks.
A 5 GiB soft threshold reclaims file cache before it reaches the hard ceiling.
The outer container has 6 GiB RAM and 2,048 tasks. Per-service caps and rotated
logs add limits inside it. The filesystem bounds all mutable image, volume,
upload and database growth together; sparse allocation grows with actual writes.
The prepared library remains cached outside the disposable filesystem.

Release source, binaries and library are root-owned. The user-writable Git
checkout and account scripts are not privileged executable inputs. Updates
require explicit administrator installation.

Sysbox shares the host kernel; it is not a hardware VM. Role consoles are
administrative within the lab and do not provide separate tenant isolation.
There is no model runtime, scoring service, traffic generator or automatic
evidence retention.
