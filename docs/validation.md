# Validation record

## Synthetic activity layer

`python3 -m unittest discover -s tests -v` passes 24 tests, including clock
sharing/bounds, independent seeded variants, smooth office modulation, jittered
slot bounds/ordering, cadence recovery from observed-style timestamps, accelerated
completion without duplicate events, dependency blocking, a failed chunk
preventing objective completion, staged-data tampering/symlink rejection,
allowlisted office DNS, and live loopback DNS/HTTP/SSH-banner/marker exchanges. These also pass inside the toolbox image,
as UID 65534 with no external network, a read-only root filesystem and dropped
capabilities. Python compilation, launcher shell syntax and merged Compose
validation pass.

`python3 tests/smoke_simulation.py --allow-rosetta` completed an isolated Docker
rehearsal using prepared images, with no builds or pulls:

- Variant seed 42 completed all 47 storyline events, with zero errors or blocked stages.
- All 32 DNS chunks originated from the file host's actual container IP.
- Real gateway/file-host password authentication appeared in target SSH logs.
- The synthetic SQL query appeared in MariaDB's general log.
- The actual blue workstation had no story source, objective journal or private
  instructor volume mounted. It received mixed raw office/transfer DNS evidence
  without phase, marker or scheduled-offset fields.
- Six of eight employee protocol diagnostics passed. FTP and IMAP failed with
  verified Rosetta runtime errors on the ARM64 Mac; SMTP delivery occurs before
  the IMAP failure. These are not reported as passing checks.
- The test's containers, networks and journal volume were removed and checked
  absent after teardown. Unrelated containers remained running.

The timing unit tests estimate a 671-second period from the default seed's
jittered samples, close to the 675-second carrier, without reading scheduled
fields or the seed. This is not a false-positive/significance assessment or proof
of live timing fidelity at high acceleration; the fast smoke test validates
connectivity and completion, not spectral recovery from its catch-up bursts.

The smoke script is strict by default: use `python3 tests/smoke_simulation.py`
on native Linux AMD64 to require all eight employee diagnostics. Its optional
`--allow-rosetta` mode tolerates only mail/FTP failures with observed Rosetta
errors, and reports them explicitly. LDAP bootstrap is awaited before the clock
starts. Full rebuilt-envelope lifecycle and native FTP/IMAP validation remain
outstanding; this rehearsal uses the actual service containers directly.

Rebuild the offline bundle and explicitly reinstall to deploy the new runtime,
launcher and sudo permissions; existing installed releases do not auto-update.


The local prototype was evaluated using Docker Desktop's Linux ARM64 engine. All nine
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
source. Relative links, CLI help options and the source manifest/submodule revision
were checked.

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

## Expanded runtime validation

The complete Sysbox range passed native Linux amd64 validation:

- All exported image configurations are amd64; the offline library starts without
  registry access. Twenty-two service/workstation containers become ready.
- All 21 protocol groups pass, including directory enumeration, FTP, SMTP capture,
  IMAP/POP3 authentication, seeded SQL databases, web applications, file sharing,
  Redis, SNMP, the badge simulator and the 32-bit teaching server.
- Blue, participant and administrative control consoles work. The participant
  lacks the blue key and internal DNS names. Workstations and the enclosing
  container have no external default route; the blue workstation has no Docker
  socket. The control socket belongs to the inner daemon.
- Exiting a joined console leaves the owner's session active. Owner shell exit
  destroys the session; status then reports Stopped. Repeated stop is harmless.
- A new session removes a target file marker, restores the database from six rows
  to its five-row seed and creates a different management key.
- Explicit stop from another login cleans up the fully running network. A forced
  SIGKILL of the transient unit during startup also leaves no range helpers,
  loop devices, named session disks or session cgroup.
- Concurrent starts are rejected. The operator has neither Docker-group access
  nor general sudo. Pre-existing host services remain active and the original
  Docker/containerd processes retain their start and restart state. The global
  Docker configuration remains unchanged.

Verified boundaries include a 6 GiB / 2,048-task outer container, a 7 GiB service
ceiling with a 5 GiB cache-reclamation threshold, and a bounded 32 GiB session
filesystem. Protocol readiness is not an attack-load benchmark. No shared-host
reboot or power-loss recovery test was performed.

The wrapper deliberately provides terminal access rather than browser forwarding.
Hashcat needs a separately supplied compatible compute backend; the other listed
analysis tools are installed. There is no model runtime or automatic evidence
retention. Runtime records, access keys and deployment inventories stay outside Git.
