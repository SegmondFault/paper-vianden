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

## Documentation walkthrough — 21 November 2026

The ten project Markdown documents were reviewed against the launcher and service
source. Relative documentation links, all twelve pinned course links, CLI help
options and the source manifest/submodule revision were checked.

A clean checkout of revision 2841225a68b9512efd6bbb9aa38d785e216cf4a2 was then
tested using a separate local Docker project on Linux ARM64. The walkthrough
passed:

- Key initialization, configuration, image build and explicit no-build startup.
- All eleven service/connectivity checks and management SSH entry.
- The documented portal, target SSH, guest SMB, authenticated SMB and SQL access.
- Browser access through a loopback-only SSH forward.
- Corrected database and webmail credential hints, matching real lab accounts.
- Evidence collection, writable-layer and database-volume reset, restoration of
  five seed customer rows, and SSH re-entry after reset.
- Clean shutdown with this project's containers, networks and data volumes
  removed. The three unrelated local containers kept their original start times
  and restart counters, and the source checkout stayed clean.

The review added a complete quickstart, service/credential reference, browser
instructions, lifecycle details, troubleshooting and explicit source-update
commands. It also corrected two stale upstream credential fixtures.

The VPS has only a source checkout tracking Git; no range was started there for
this review. Server AMD64, Sysbox lifecycle and combined learn-to-hack
functionality have not yet been validated. Runtime evidence, keys and server
inventories remain outside Git.
