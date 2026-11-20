# Validation record

The source-only prototype originates from a locally evaluated adaptation of
VulnCastle. That evaluation used Docker Desktop's Linux ARM64 engine. All nine
containers became healthy; management SSH and portal/SMB/SQL/webmail/API/admin/
Redis checks passed. Reset removed writable-layer and database-volume markers
and restored the seed data. Unrelated local containers remained unchanged.

The clean Paper Vianden copy has passed Python compilation, shell syntax checks
and resolved Compose validation. Its default model contains nine containers with
2016 MiB summed RAM ceilings and 3.85 summed CPU ceilings; the troubleshooting
model has six containers with 1440 MiB and 2.6 CPU ceilings. These limits exclude
host/engine overhead and are not measured attack-load usage.

No containers were started to create or publish this repository. Server AMD64,
Sysbox lifecycle and combined learn-to-hack functionality have not yet been
validated. Runtime evidence and server inventories remain outside Git.
