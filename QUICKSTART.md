# Quickstart - participants

Your SOC models should run outside Paper Vianden and use SSH tools to work inside
it. This guide covers joining an exercise as blue, red or green. The operator
reserves and starts the shared range, chooses its traffic modes and handles
exports and teardown; see the [operator quickstart](OPERATOR_QUICKSTART.md).

Get the deployment host, your role's SSH credentials and the selected traffic
modes from the operator. Replace `range.example` below with that host. Wait for
the operator to confirm the exercise is ready. Participant logins only join an
existing exercise; they do not start one. You only need your role's SSH login;
the operator keeps the reservation code and human account credentials.

See the [environment diagram](docs/environment.md) for the networks and
workstations, and [security coverage](docs/security.md) for the available tools
and their limits.

## 1. Blue team with the pre-programmed scenario

For the first smoke test, ask the operator to use the default scripted intruder
and scripted normal employees. Connect your blue agent's SSH tool using:

```sh
ssh vianden-agent-blue@range.example 'hostname'
ssh vianden-agent-blue@range.example 'evidence status'
ssh vianden-agent-blue@range.example 'analyst inbox'
ssh vianden-agent-blue@range.example 'analyst logs --limit 50'
```

The workstation hostname is `defender`. It can inspect the evidence feed and
administer lab targets. Interactive tools can use `ssh -t`; up to 16 concurrent
SSH tool sessions per account join the same exercise. Coordinate changes to
shared targets across agents.

Give the agent a task such as:

> Investigate suspicious activity using the alert inbox and logs. Open a case,
> record supporting evidence and notes, and produce a handover.

Collection and alerting run automatically. The agent supplies the investigation,
case notes and handover content. The inbox can be empty until a rule matches;
log search remains useful during quiet periods. These small rules are not a
complete detection library.

A basic investigation uses the following commands. Replace IDs and versions with
values returned by the workspace:

```sh
ssh vianden-agent-blue@range.example 'analyst assets'
ssh vianden-agent-blue@range.example 'analyst logs --source auth.log --limit 50'
ssh vianden-agent-blue@range.example 'analyst open "Investigate suspicious activity"'
ssh vianden-agent-blue@range.example 'analyst note CASE_ID "Observed activity; checking its source" --event EVENT_ID --version 1'
ssh vianden-agent-blue@range.example 'analyst status CASE_ID investigating --version 2'
ssh vianden-agent-blue@range.example 'analyst handover CASE_ID --version 3 --summary "Evidence and current assessment" --actions "Actions taken and business checks" --next-steps "Outstanding questions and next owner"'
```

When an alert exists, add `--alert ALERT_ID` to `analyst open` to attach it.
`analyst cases`, `analyst case CASE_ID` and `analyst audit` show saved work. Each
update returns a new `version`; use it for the next change so concurrent agents
cannot overwrite one another. Notes can retain an event snapshot after it leaves
the bounded live feed. Search also accepts `--query`, `--host`, `--since` and
`--until` (ISO timestamps with UTC offsets).

For continuous ingestion, use `evidence tail --after CURSOR` or
`evidence tail --follow`. Cursor responses indicate restarts and retention gaps.
Save additional findings under `/var/lib/soc-ai` in the blue workstation.

If containment is part of the smoke test, use an address from `analyst assets`:

```sh
ssh vianden-agent-blue@range.example 'analyst firewall status'
ssh vianden-agent-blue@range.example 'analyst firewall block --ip LAB_IP --reason "Contain observed source; case CASE_ID"'
ssh vianden-agent-blue@range.example 'evidence availability'
ssh vianden-agent-blue@range.example 'analyst firewall unblock --ip LAB_IP --reason "Investigation complete; case CASE_ID"'
```

These actions are audited and affect the disposable network. Blocking a business
service can interrupt legitimate work; record the availability result in the
case. Blue can also administer lab targets through SSH.

## 2. Add a real red-team LLM

Ask the operator to switch the exercise to red LLM mode and confirm the new run
is ready. **This disables the automatic malicious storyline.** Ordinary employees
can remain scripted, and blue continues through its own account.

Connect your external red model's SSH tool using:

```sh
ssh vianden-agent-red@range.example 'hostname'
```

It lands in `red`, with DMZ access and tools. The operator supplies the red team's
objective and allowed lab actions. Red has no blue administrator key or instructor
journal; save its findings under its own `/var/lib/soc-ai`. Red logins are denied
while the operator has selected the scripted intruder.

## 3. Add a benign green-team LLM

Ask the operator to switch normal traffic to green LLM mode and confirm the run
is ready. This works with either the scripted intruder or a real red LLM.
**Automatic employee workflows are disabled in this mode.** The clock keeps
running; the green model supplies ongoing ordinary business activity.

Connect the external green model's SSH tool using:

```sh
ssh vianden-agent-green@range.example 'hostname'
ssh vianden-agent-green@range.example 'green-work all'
```

It lands in `green` as an unprivileged user. Assign ordinary business activity:
browse, read public shares, check mail, query the directory and run reports.
`green-work web`, `green-work mail` and the other named workflows create real
service requests and a green activity journal. Green has no administrator key,
Docker socket or instructor truth. Save its findings under its own
`/var/lib/soc-ai`. Green logins are denied while scripted normal traffic is
selected.

## Finish and keep results

Tell the operator when your run is finished so they can export results and release
the reservation. Cases, notes, handovers, observed evidence and each role's
`/var/lib/soc-ai` findings are included in normal exports. The operator handles
the archive because it also contains private instructor observations.

Reconnecting keeps the active exercise. A new start or reset clears live logs,
workspace data, role findings, shell histories and containment rules. Saved exports
survive reset and teardown. If you need another run or cannot connect, contact
the operator; [their quickstart](OPERATOR_QUICKSTART.md) covers readiness,
traffic modes, reset and export.
