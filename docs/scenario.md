# Current scenario: a quiet-office intrusion

Paper Vianden models a small office network over **24 simulated hours**. Normal
employee activity creates real protocol traffic while an independent, harmless
intrusion simulation progresses through the same environment. The exercise is
intended for testing agentic blue-team architectures: the agent receives a blue
terminal and must investigate evidence, not follow a supplied attack transcript.

All identities, accounts and records are public training fixtures. There are no
malicious payloads, external transfer destinations or real-data collection.
This page contains no deployment credentials or instance addresses.

## The environment

The range contains management, DMZ and internal networks, with a blue workstation,
white observation workstation, red tooling workstation, gateway, web/API services,
database, file server, directory, captured mail and other training fixtures.
The scenario uses a DMZ-only actor; internal discovery and lateral connections
must traverse the gateway rather than originate directly from that actor.

The blue workstation provides a command-line investigation environment. A human
can use white to compare the agent's findings with private ground truth. White's
journals and scenario source are not mounted into blue. White is read-only and
is not the administrative control console. See [SSH access](ssh-access.md).

## What normal looks like

Lightweight employee/service workflows generate actual requests:

- Portal browsing and API calls.
- SMB public-share reads and LDAP directory lookups.
- SQL reports and routine SSH identity checks.
- Captured SMTP delivery, mailbox checks and anonymous FTP listings.
- Range-local DNS lookups for office service names.

Traffic ramps through office hours, pauses for lunch and becomes quiet overnight.
Workflow selection, pauses and small intensity changes are seeded and jittered.
This is lightweight protocol simulation, not desktop automation or a fitted model
of human behaviour.

## The intrusion storyline

The current story has **47 bounded events**, including 32 small synthetic DNS
transfers. Approximate stages are shown below; seeded timing varies.

| Simulated time since start | Stage | What actually happens |
| --- | --- | --- |
| First hour | Reconnaissance | HTTP requests and an old-looking SSH banner exchange |
| Around hours 2–3 | Initial access | An inert application marker, followed by a real gateway login using a fixture account |
| Hours 3–7 | Discovery | Harmless identity/interface commands, four fixed internal service connections, directory enumeration and an API request |
| Hours 8–9 | Credential/account context | An inert credential-access marker and a fixture-account switch; no secret extraction or root escalation |
| Around hour 10 | Lateral movement | A real SSH login to the file host through the gateway |
| Hours 11–14 | Collection and staging | A logged SQL query returning literals, followed by creation and verification of a generated report fixture |
| Hours 16–22 | Simulated DNS transfer | Fixed synthetic records sent to a non-forwarding, range-local DNS sink with seeded timing jitter |
| Around hour 23 | Objective | A private completion marker, only if all required transfers succeeded |
| Hour 24 | End of activity | Workers become idle; the range remains until its lifecycle ends |

Initial exploitation, credential acquisition and privilege escalation are
**represented**, not performed. The simulation never invokes an exploit, sudo
abuse, persistence mechanism or arbitrary command supplied by a network request.
Actual access uses existing fixture accounts and fixed, harmless commands.
The SQL operation does not collect customer-table contents; staging and transfer
use generated records only. There is no evidence-destruction stage.

## What an agent can detect

There are multiple independent investigation opportunities—not just DNS timing:

- New authentication sources and changes in account context.
- Internal service/directory/API discovery associated with gateway sessions.
- File-host authentication originating from the gateway.
- Unusual SQL activity, staging artifacts and correlated timestamps.
- DNS query origins, encoded-label structure, time-of-day and aggregate timing.

Transfer gaps are **not constant**. Bounded phase jitter makes individual
intervals irregular while retaining an underlying cadence for statistical
analysis over a longer observation window. FFT on binned counts, autocorrelation
or an event-time periodogram can be useful; no single technique is mandatory.
The small sample size and other visible indicators mean this is not an evasion
guarantee or a production detector benchmark.

Blue gets ordinary target evidence and mixed raw DNS logs, not automatic attack
labels or the full story transcript. A useful result should explain which
observations support the agent's conclusions and correlate them across hosts.

## Seeds, clocks and failures

The default clock begins at a synthetic Monday 09:00 Luxembourg time. A multiplier
controls simulated time independently of the VPS's date:

```sh
# Foreground operator mode; configured SSH portals use the server's preset.
./start-range --seed 42 --clock-speed 60
```

A 60× clock covers 24 simulated hours in about 24 real minutes, excluding startup
and delays. Different seeds vary workflow mixes, pauses, intensity and scheduled
story timing through independent PRNG streams. They are variants of the same
story—not distinct attack paths. Reusing a seed reproduces planned variation,
not exact packet timestamps or network outcomes.

Real operation latency is not accelerated. Prefer default or modest speed for
frequency analysis: very high multipliers can cause catch-up bursts that distort
the observed cadence. The fastest rehearsal is for functional testing, not proof
of realistic timing fidelity.

Critical milestones gate later stages. Defender changes that block access,
alter the staged fixture or prevent DNS acknowledgements produce errors/blocked
events. The simulation does not invent successes, retry indefinitely or continue
the objective after a failed prerequisite.

## Scope and spoilers

The current system has one shared range at a time, not isolated concurrent runs.
There is no built-in LLM, scoring engine, SOC dashboard or whole-network packet
mirror. Evidence and mutable state disappear with teardown unless exported.

For full stage timings, synthetic-data details and private observation paths,
see [instructor notes — spoilers](scenario-instructors.md). Do not include those
notes, source or observer credentials in the context of an agent being evaluated
as a black-box investigator. Keeping the answer key separate reduces leakage;
it does not make synthetic fixtures indistinguishable from a real enterprise.
