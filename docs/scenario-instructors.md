# Intrusion exercise — instructor notes / spoilers

Do not provide this guide, the source checkout, control console or private
journals to an LLM being evaluated as a black-box blue-team investigator.
Everything here is a synthetic lab fixture, not an exploit implementation.

## Reproducible variants

```sh
./start-range --seed 42 --clock-speed 60
./start-range --seed 43 --clock-speed 60
```

The unsigned 32-bit seed defaults to `20260112`. It selects a **behavioural
variant of the same story**, not a different attack path. Independent SHA-256-
derived PRNG streams control employee workflow choices, lognormal pauses,
smooth office intensity variation (±15%), story-slot jitter (up to ±90 simulated
seconds), and DNS phase jitter. Extra draws in an employee stream cannot shift
the attacker schedule. The shared clock publishes the seed to both workers.

A seed reproduces planned schedules and random choices, not packet-exact logs.
Clock speed, operation duration, skipped office workflows, failures and defender
intervention affect what actually runs. Protocol identifiers and SSH/transport
cryptography are deliberately not made deterministic.

## Story / evidence opportunities

The DMZ-only story worker has no direct internal network interface. Internal
protocol connections and lateral SSH traverse the gateway using fixed-destination
SSH channels. It runs separately from employee activity, sharing a monotonic clock.

| Approximate hours | Stage | Investigator evidence / correlation |
| --- | --- | --- |
| 0.5–1 | Banner reconnaissance | HTTP/SSH connections to old-looking Java/SSH emulators; inspect requests and version strings, not a synthetic alert |
| 2–2.25 | Emulated foothold, then fixture gateway access | Benign session POST followed by a real `devuser` password login from a new DMZ source; gateway `/var/log/auth.log` |
| 3–4 | Host/service discovery | Fixed identity/interface commands and four internal service connections originating at the gateway; captures and SSH sessions |
| 5–7 | Directory/API enumeration | LDAP fixture DN/UID search and API user request via the same gateway source; service/capture evidence |
| 8–9 | Emulated credential use / account-context increase | Inert profile marker followed by a real `sysadmin` fixture login; correlate account and source changes, not root access |
| 10 | Lateral movement | File-host `devuser` SSH login **from the gateway's internal IP**, correlated with gateway sessions |
| 11 | Synthetic collection | Real MariaDB general-log query with `report_export` comment, returning literals only, through the gateway |
| 13–14 | Staging | `/tmp/report-cache/export.jsonl` on the file host; fixed generated records, ownership, timestamps and hash |
| 16–22 | DNS transfer | Encoded fixture labels below `telemetry.range.test`, originating at the file host; compare with ordinary office lookups, payload characteristics, time-of-day and periodicity |
| 23 | Objective | Instructor completion marker only if all 32 DNS chunks succeeded |
| 24 | End | Both workers remain healthy and idle until teardown |

These are several independent places to detect the simulated intrusion. No
single clue or frequency estimator is required. A good investigation should
correlate time, source, account and protocol changes, distinguish routine
employee work from unusual activity, and identify which evidence supports a
conclusion. A version string by itself does not establish exploitation.

Foothold/credential acquisition are inert, allowlisted HTTP markers. Their wire
responses are ordinary `{"ok":true}` acknowledgements, not attack-stage labels.
Actual access uses already-seeded public lab passwords. Privilege escalation is
an account-context simulation: no sudo/SUID use, root shell, malicious payload,
persistence or arbitrary command input. The SQL query reads literals, not
customer tables. Staging uses exclusive creation and refuses existing paths;
transfer checks the exact synthetic fixture hash and generates each chunk,
never collecting arbitrary files. No evidence destruction runs.

## DNS timing exercise

There are still exactly 32 small, range-local DNS transfers. The underlying
carrier is 675 **simulated** seconds (11.25 minutes), but each nominal slot gets
stratified phase jitter: 32 offsets distributed across ±28% of the carrier,
then assigned to slots by a seeded shuffle. This is not a random walk: cumulative
random delays would wash out the intended frequency. Stratification keeps a
small-sample draw from accidentally flattening the carrier. Slots stay ordered
and inside hours 16–22 for every seed.

For the default seed the gaps vary roughly 6–17 minutes instead of repeating a
constant interval. An event-time Fourier periodogram of the planned jittered
samples estimates 675 seconds without reading seed, packet indexes or scheduled
offsets. Regression tests recover within 15 seconds for 100 seeds. This fixes
an observed old-generator failure where seed 42 had a stronger unrelated peak
near 309 seconds. It remains a controlled teaching result, not a unique-peak or
significance guarantee for every seed, detector or real capture.

Office activity also performs genuine DNS A lookups under `office.range.test`
through the sink. The allowlisted server returns only fixed Docker fixture
aliases; unknown names receive NXDOMAIN and are never forwarded. The raw DNS
journal therefore contains background queries **and** transfer queries, without
phase labels or a preselected suspicious group. Encoded labels contain synthetic
records only. The suffix is neutral, not named `exfil`.

For an optional instructor/reference analysis after exporting raw evidence:

```sh
python3 tools/analyse_dns_timing.py queries.jsonl \
  --clock-speed 1 --suffix telemetry.range.test
```

The helper uses observed timestamps only and searches a 5–20 minute period
window. It reports an exploratory phase-coherence estimate, not a significance
test, alert or detection verdict. An investigator must select a candidate stream;
the helper has no hard-coded suspicious suffix. FFT on binned counts,
autocorrelation or phase folding are alternative approaches. Unknown jitter
cannot literally be subtracted from a real capture; aggregation estimates the
underlying cadence statistically. Only 32 samples limits confidence.

Prefer default speed or modest acceleration for a timing investigation. Real
SSH/network latency is not accelerated. At high multipliers work can fall behind
and catch up in bursts, destroying the intended **observed** frequency even when
the planned schedule is correct. Timing tests cover planned samples; the fastest
integration rehearsal tests connectivity and event completion, not FFT fidelity.
Other indicators (payload structure, staging, authentication and query origin)
remain detectable; this is not an evasion guarantee.

## Journals / access separation

Blue gets ordinary target logs, employee health/activity and the read-only raw
DNS journal at `/var/log/dns/queries.jsonl`. It does **not** get scenario source,
`story.jsonl`, stage schedules, marker labels or objective status mounted into its
workstation. Instructor truth and synthetic marker logs live on a separate tmpfs
volume, accessible through control:

```sh
# In ./join-range --control; these are instructor-only diagnostics.
docker compose -p paper-vianden --profile extended \
  -f prototype/docker-compose.yml -f compose.yaml exec scenario-runner \
  python3 /opt/paper-vianden/runtime/scenario_runner.py --check

docker compose -p paper-vianden --profile extended \
  -f prototype/docker-compose.yml -f compose.yaml exec scenario-runner \
  tail -n 20 /var/log/range-instructor/story.jsonl
```

`story-status.json` in the same directory separates runner health from objective
success (`pending`, `complete`, `incomplete`). The sink's private marker journal
is `/var/log/range-instructor/scenario-sink.jsonl`. Normal-looking HTTP paths are
`/api/session`, `/api/profile` and `/api/status`; they only acknowledge fixed
simulation markers and never execute request contents. Their private logs mark
simulation explicitly.

This prevents accidental answer-key exposure, **not** a tenant/security boundary:
control is administrative and the repository is public. Existing blue SSH access
can examine target artifacts as intended. All three journal volumes, service
processes and staged files disappear at teardown. Export evidence first.

Critical milestones gate later actions. Blocking the gateway, changing a fixture
password, altering the staged fixture or denying DNS produces errors/blocked
events, not fabricated success. There are no retries or repeated attack loops.
A missing DNS acknowledgement prevents the objective marker.
