# Operator guide

## Deployment status

Sysbox and the range have not been installed by this project. The prototype is
not a shared-server installer. No global Docker restart, default-runtime change,
daemon address-pool change, or host-wide prune is part of the accepted deployment.

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

The intended source repository is SegmondFault/paper-vianden. Keep server checkout
and administrator-owned deployed release separate. The server may fetch source
with a repository-scoped read-only deploy key. Private key material stays on the
server and outside the repository.

An update is explicit: fetch, review a selected tag/commit, stage it, validate it,
then switch the deployed release. Record the deployed commit. An ordinary range
invocation must not git pull, switch releases or update images automatically.
No cron job, boot hook or login hook should start the range.

Use git submodule update --init --recursive to obtain the pinned course sources.
Updating that pin is a reviewed source change, not a session-start operation.

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
