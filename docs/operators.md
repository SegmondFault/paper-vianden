# Operator guide

## Deployment status

A source checkout is not a runtime deployment. The prototype is not a
shared-server installer; the disposable Sysbox runtime is still being built.

No global Docker restart, default-runtime change, daemon address-pool change, or
host-wide prune is part of the accepted deployment. The Sysbox package's standard
installer may change Docker configuration and restart it; its exact package
scripts and dependencies must be reviewed before use on the shared server.

## Proposed installation

1. Review the exact Sysbox package, dependencies and integration procedure.
2. Establish a no-disruption installation path. If this requires restarting or
   changing unrelated workloads, stop and resolve the deployment design.
3. Build the envelope and target image library for the server architecture.
4. Install an administrator-owned release and a narrow operator interface.
5. Validate creation, access, interruption cleanup, reset and resource boundaries.

The operator should not need Docker-group membership or unrestricted sudo. A
privileged launcher must run only administrator-owned code/configuration; do not
execute it as root from an operator-writable checkout.

## Git deployment

The public source repository is [SegmondFault/paper-vianden](https://github.com/SegmondFault/paper-vianden).
Clone as an ordinary user; this starts no services:

```sh
git clone --recurse-submodules https://github.com/SegmondFault/paper-vianden.git
cd paper-vianden
git status --short
git log -1 --oneline
git submodule status
```

The main branch tracks origin/main. An existing checkout can fetch and update
explicitly, provided its working tree is clean:

```sh
git fetch origin
git log --oneline HEAD..origin/main
git pull --ff-only
git submodule update --init --recursive
```

These commands update source only; they do not install a runtime or start targets.
If there are local changes or divergent commits, stop and review them rather than
resetting or overwriting the checkout.

Keep server checkout and administrator-owned deployed release separate. The
public repository requires no GitHub credential to clone. Where authenticated
access is used, scope a deploy key to read-only repository access; private key
material stays on the server and outside the repository.

An update is explicit: fetch, review a selected tag/commit, stage it, validate it,
then switch the deployed release. Record the deployed commit. An ordinary range
invocation must not git pull, switch releases or update images automatically.
No cron job, boot hook or login hook should start the range.

The submodule command obtains dependency revisions recorded by Paper Vianden;
do not add --remote for an ordinary checkout/update. Changing its recorded pin
is a reviewed source change, not a session-start operation.

## Resources and host protection

Give the outer sandbox an aggregate CPU/RAM/PID budget and verified bounded
session storage. Docker log rotation alone does not cap database, upload or image
growth. Plan image storage separately from disposable session data.

The envelope must not mount the host Docker socket, use host network/PID
namespaces, or expose unrelated host directories. Restrict its host-facing
network and verify host-service reachability rather than assuming that container
networks provide a complete host boundary.

Sysbox shares the host kernel. It is not a hardware-virtualized boundary. The
installation and network policy must reflect the workloads permitted in the lab.
