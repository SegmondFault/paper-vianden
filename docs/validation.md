# Validation record

## Current analyst workspace acceptance — 21 November 2026

The installed executable runtime is revision `0e22b93`. Later documentation and
acceptance-harness updates do not change that executable code.

All **56 unit tests pass on native Linux AMD64 on the VPS**, as well as on the
Mac development host. The suite includes real loopback HTTP authorization tests,
case evidence retention/export, concurrent version conflicts, workspace capacity
rollback and the private-namespace guard. Suricata's configuration and four rules
also pass its own `-T` check with the production read-only filesystem and restricted
capabilities.

The native `tools/rehearse_analyst.py` run passed through the real role portals:

- A real HTTP request raised a Suricata alert with the actual source address and
  reached both the alert inbox and log search.
- A case retained selected evidence, accepted notes and a Markdown handover,
  rejected a stale version update and appeared in white's read-only snapshot.
- DMZ requests to internal SSH and the management evidence API were denied.
  An unauthenticated workspace request from blue was also rejected.
- Blocking the observed red source stopped its HTTP requests; unblock restored
  them. All eight ordinary-work probes remained successful. A separate check
  through the actual green workstation also passed all eight workflows across
  the enforced network policy.
- Export contained the case, handover, raw IDS observations and firewall actions,
  with no omissions and no access token. After a fresh reset, cases/inbox and
  containment blocks were empty, the token changed, business checks passed and
  the previous export remained downloadable unchanged.

The scripted response regression also passed on this revision: blue locked the
file-host fixture account through SSH, the intruder objective remained incomplete,
and all eight ordinary-work probes stayed successful. The human lease rejected a
competing claim, parallel blue tool sessions worked and agent lifecycle control
was denied. Export retained the response findings and instructor observations.

The four-mode portal rehearsal passed scripted/scripted, red LLM/scripted,
red LLM/green LLM and scripted/green LLM. Each mode passed all eight ordinary-work
probes; both green configurations also passed `green-work all` from the actual
green workstation. Role gates, disabled automatic actors, concurrent blue tools,
read-only unprivileged white and private findings exports all passed. Every export
manifest reported no omissions. Final release left no active state or Sysbox
helpers, and agent logins did not restart the exercise.

The active firewall/IDS namespace was verified distinct from the VPS namespace.
The original host Docker/containerd PID, start and restart state stayed unchanged.
Normalized VPS firewall rules matched during the active run and after teardown.
Reproduce with `tools/rehearse_analyst.py`, `tools/rehearse_demo.py` and
`tools/rehearse_roles.py`; private reports and exports stay under ignored `local/`.

These are scripted interface checks, not a measurement of an LLM's judgement.
Detection coverage, analyst grading and optional flags remain stretch work in
the [roadmap](development-notes.md). See the [coverage guide](security.md) for the
implemented corporate/SOC features and the components not included.

## Earlier portal acceptance — 21 November 2026

The installed runtime is revision `1d19ea8`. Documentation-only updates record
these results without changing the installed executable code.

**49 unit tests pass**, covering human lease exclusivity/expiry, UID/role binding,
parallel SSH slots, human-selected traffic modes, clock-only green mode, cursor
reset/gap handling, SQL deduplication, archive safety, startup cleanup and EDNS
queries from standard DNS clients.

Native Linux AMD64 checks through the actual VPS SSH portals passed:

- Blue, red, green and human accounts enter their fixed workstations. The old
  unsuffixed agent login is retired. Red/green logins are denied unless their
  LLM modes were selected by the human. Agents cannot invoke human controls.
- A competing human cannot claim an existing reservation, including through the
  same Unix account. Concurrent blue SSH tool calls work within the shared run.
- All four combinations pass: scripted/scripted, red LLM/scripted, red LLM/green
  LLM, and scripted/green LLM. Automatic malicious actions stay off in red LLM
  mode; scripted employee actions stay off in green LLM mode, with the clock alive.
- All eight ordinary-work probes pass in each mode. The scripted response
  rehearsal locked the intruder fixture account through the agent SSH interface,
  prevented its objective and kept all eight ordinary workflows working.
- White runs as UID 65534 with zero effective capabilities. Agent workstations
  have no host Docker socket or private instructor journal; red/green have no
  blue administrator key.
- Private blue/red/green findings are included in bounded downloadable archives,
  including files written with umask 077. Exports survive reset and teardown.
- The clean-start rehearsal planted a unique prior-case marker in all four role
  histories, all agent findings and a target authentication log. After reset,
  live views contained no marker, the run identifier changed and startup-probe
  mail was empty. Saved exports still contained the earlier findings.
- A standard `dig` query produced fresh DNS evidence after cleanup, confirming
  that active sink log descriptors survived the wipe. All eight ordinary-work
  probes still passed after reset.
- Release leaves the range stopped with no active state or Sysbox helpers.
  Agent login attempts do not start a new exercise. The original host Docker
  and containerd PID/start/restart state remained unchanged throughout.

Reproduce with `tools/rehearse_demo.py`, `tools/rehearse_roles.py` and
`tools/rehearse_clean_start.py`, using private local credentials and pinned host
keys. Reports/archives live under ignored `local/` paths, never in public Git.

These are scripted acceptance clients. They verify the interface used by an
external SOC architecture, not an AI model's judgement or adversarial robustness.
No provider reboot/power-loss test or multi-user load benchmark was performed.
Uncatchable termination or host failure can interrupt export. Archive manifests
report entries omitted by the documented size/file limits.

## Earlier validation records

The entries below describe earlier revisions and development-platform checks.
The current native acceptance results above supersede their older test counts.


## Synthetic activity layer

`python3 -m unittest discover -s tests -v` passes 33 tests, including portal
UID/role binding, command argument isolation, scoped SSH configuration updates,
read-only observation, and clock
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
- White read the completed objective through read-only mounts, as UID 65534,
  without access to an administrator SSH key or Docker socket.
- The actual blue workstation had no story source, objective journal or private
  instructor volume mounted. It received mixed raw office/transfer DNS evidence
  without phase, marker or scheduled-offset fields.
- Six of eight employee protocol diagnostics passed. FTP and IMAP failed with
  verified Rosetta runtime errors on the ARM64 Mac; SMTP delivery occurs before
  the IMAP failure. These are not reported as passing checks.
- The test's containers, networks and journal volume were removed and checked
  absent after teardown. Unrelated containers remained running.

The timing unit tests estimate a 675-second period from the default seed's
jittered samples, and recover within 15 seconds for 100 seed variants without
reading scheduled fields or the seed. This is not a false-positive/significance assessment or proof
of live timing fidelity at high acceleration; the fast smoke test validates
connectivity and completion, not spectral recovery from its catch-up bursts.

The smoke script is strict by default: use `python3 tests/smoke_simulation.py`
on native Linux AMD64 to require all eight employee diagnostics. Its optional
`--allow-rosetta` mode tolerates only mail/FTP failures with observed Rosetta
errors, and reports them explicitly. LDAP bootstrap is awaited before the clock
starts. This local rehearsal uses service containers directly; the native
rebuilt-envelope checks are recorded separately below.

Rebuild the offline bundle and explicitly reinstall to deploy the new runtime,
launcher and sudo permissions; existing installed releases do not auto-update.


## Native deployed SSH portal rehearsal

The rebuilt 26-service envelope was installed on Debian 12 Linux AMD64 and
tested through real SSH accounts (credentials and instance addresses omitted):

- First blue-account SSH login automatically started the managed range.
- Both interactive PTY login and one-shot, non-PTY SSH commands entered the blue
  workstation, not the VPS host. A file survived disconnect/reconnect.
- Agent-side checks resolved targets, scanned fixed SSH/SMB ports and queried
  the seeded LDAP directory successfully.
- White-account SSH entered a distinct workstation as UID 65534; `observe`
  read private story progress through read-only mounts, without a Docker socket.
- Seed 42 at 3600x completed all 47 events with zero errors/blocked stages; white
  observed all 32 synthetic DNS transfers. This accelerated test establishes
  functional completion, not fidelity of the live DNS frequency signal.
- All eight native employee protocol diagnostics passed, including FTP and mail.
- Blue had no host release, host Docker socket or white journal mounted. SSH
  forwarding and host-side attempts to select another role were denied.
- Explicit managed-owner stop cleaned up. A separate fresh run then expired at
  an actual three-minute lease (`Result=timeout`), removed active state, unmounted
  its disposable filesystem and stopped its Sysbox helpers automatically.
- A previous blue-only test file was absent in the fresh run. The host Docker
  daemon's PID/start time and unrelated workload state stayed unchanged.
- That initial rehearsal restored seed 20260112, a 1x clock and a 26-hour lease.
  The later accelerated qualification below supersedes that operating preset.

No provider reboot/power-loss test was performed. Per-user concurrent ranges,
idle timeout, lease renewal and participant reset controls are not implemented.

## Accelerated evidence and single-login qualification

A blue-side evidence collection run at 120x reconstructed valid-account gateway
access, directory/API activity, account switching, lateral SSH, a literal SQL
export query, a staged fixture and encoded DNS transfers. Collector traffic was
identified by blue source IPs; white ground truth was consulted only afterward
for event-count verification. Authentication logs do not provide precise event
timestamps, so collection time bounds and packet captures were used. Exact SSH
command execution and the emulated initial exploit cannot be proved from those
logs alone; real deployments should add consistent timestamped host auditing.

That test exposed a timing-generator defect: the old Gaussian draw for seed 42
had a stronger unrelated spectral peak than the intended carrier. Stratified,
seed-shuffled phase jitter fixed the small-sample imbalance. A fresh native run
at 300x then verified:

- All 47 story events completed successfully, confirmed afterward through white.
- All 32 decoded DNS records matched records in the staged file.
- Analysis of actual DNS packet-capture timestamps recovered a 680-second
  simulated period against a nominal 675 seconds (less than 1% error).
- Observed phase coherence was 0.3683, with irregular interarrival intervals
  (CV 0.1769). This is an exploratory result, not a significance/false-positive
  assessment or a guarantee for all real captures.
- Source tests recover within 15 seconds for 100 seed variants. A default-only
  test would have missed the original seed-42 regression.

Single-login enforcement was tested through real SSH: a second blue workstation
session was rejected, white could observe concurrently, abrupt disconnect
released the blue slot, and sequential commands on a reused SSH transport
worked. Enforcement uses a UID-bound lock, not `MaxSessions=1`, which caused a
channel-teardown race for legitimate sequential clients.

Evidence exports were checksum-verified and retained privately outside the
range, never committed to Git. Test collectors/captures were removed by range
teardown. The latest portal source was reinstalled and retested on fresh fixtures;
then the test run was stopped again. The operating preset is seed 42, a 120x
clock (about 12 minutes of scenario time), and a 30-minute real-time lease. First
portal login starts a new clean run. The host Docker daemon remained unchanged.

This qualifies a controlled, single-range research pilot. It is not a blind
independent-agent benchmark, a 24-hour endurance test or a hardened multi-tenant
security certification. Red/green agent portals and the flat scenario remain
roadmap items.

## Earlier prototype checks

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
