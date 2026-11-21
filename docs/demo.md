# SOC architecture demo

The SOC model and orchestration run outside the range. The supplied SSH adapter
and acceptance rehearsal are scripted clients; they test the response interface,
not a model's judgement.

For the ordered blue → red → green walkthrough, start with the [Quickstart](../QUICKSTART.md).

## Human exercise gate

Use remote SSH commands on the human account:

```sh
ssh human@range.example 'range status'
ssh human@range.example 'range claim Alice --minutes 120'
# Keep the returned token private.
ssh human@range.example 'range start --token TOKEN --seed 42 --clock-speed 60'
```

Cold startup takes several minutes; `range status` reports `phase: ready`.
One human lease and one scenario exist at a time, even when people share the
human Unix account. Only the token holder can start/reset/stop/release that run.
Lease expiry uses real time and stops the owner. A login never starts a run.

Agent connections only join that exercise. Up to 16 concurrent workstation
sessions per account are supported across SSH connections/channels. Multiple
agents can run tools in parallel; coordinate conflicting writes to shared hosts.
Disconnecting an agent or human observer does not stop the exercise.

## Central evidence and SOC findings

Inside the blue terminal:

```sh
evidence status
evidence tail --limit 200
evidence tail --after RUN_ID:SEQUENCE --limit 200
evidence tail --follow
evidence availability
curl -fsS -H "Authorization: Bearer $(cat /run/analyst/token)" 'http://telemetry.management:8088/events?limit=200'
analyst inbox
analyst logs --query "Failed password"
analyst cases
```

The collector gathers authentication, web/API, Samba, FTP/mail, SQL, mixed raw
DNS, employee observations and Suricata network metadata/alerts. Events have IDs, observation timestamps, host,
source and original message; structured inputs retain their fields/timestamps.
No private story journal is collected. Polls run about every two seconds plus
source latency; sensor errors appear in `evidence status`. Cursor responses
expose restarts (`reset`) and retention gaps (`gap`). Handle both when ingesting.
The collector supplies a small set of SIEM functions. It is not a full SIEM
distribution or whole-network packet mirror. The [coverage guide](security.md)
describes its rules, retention and limits. The [Quickstart](../QUICKSTART.md)
walks through case notes, version checks, handovers and reversible containment.

Save findings, actions and selected evidence under `/var/lib/soc-ai`. It survives
SSH disconnects and is included in exports. Humans separately use `observe status`
and `observe story` for instructor truth. Keep white credentials out of model context.

## Export and finish

```sh
ssh human@range.example 'range export --token TOKEN'
ssh human@range.example 'range archives'
ssh human@range.example 'range download ARCHIVE_ID' > demo.tar.gz
ssh human@range.example 'range reset --token TOKEN --seed 43 --clock-speed 60'
ssh human@range.example 'range stop --token TOKEN'
ssh human@range.example 'range release --token TOKEN'
```

Reset exports before replacing the run. Stop keeps the lease; release exports,
stops and releases it. A deliberate stop/reset/release is refused if its explicit
export fails. Normal teardown also attempts a final archive, including lease
expiry and foreground exit. Uncatchable termination, power loss or disk failure
cannot guarantee preservation: download important results during the exercise.

Archives persist outside the disposable filesystem in root-private
`/var/lib/paper-vianden/evidence`. Human portal downloads need no host shell/SFTP.
They contain blue observations/findings AND private instructor truth; restrict
these archives to the demo owner. Each export has a 48 MiB content budget and
2,000-entry limit. `manifest.json` lists omitted files. Administrators manage
archive retention explicitly after downloading results.

## Rehearse the response path

Configure ignored `.env` keys `VIANDEN_HOST`, `VIANDEN_HUMAN_USER`,
`VIANDEN_HUMAN_PASSWORD`, `VIANDEN_AGENT_USER`, `VIANDEN_AGENT_PASSWORD`, plus a
pinned `local/known_hosts`. Environment variables can supply the same settings;
without passwords the adapter uses existing SSH key/agent authentication.

```sh
python3 tools/rehearse_demo.py
```

The rehearsal refuses another person's slot, checks human gate exclusion and
parallel agent tools, observes file-host intrusion authentication in the central
feed, then locks that host's fixture `devuser` through the agent portal. It checks
all eight ordinary-work probes still pass and the simulated objective is prevented,
downloads an archive containing its findings, then releases the run. Results go
to ignored `local/demo-rehearsal-*`. Default 600x spans about 2.4 minutes plus
startup and actual protocol latency. Use a slower clock for presentations or
frequency analysis. This is a scripted acceptance check, not an AI performance score.

The same adapter can be imported by the SOC architecture:

```python
from tools.demo_client import SSHClient
client = SSHClient()
events = client.json('agent', 'evidence tail --limit 100')
```

## External team modes

Only the human lease holder selects `--attacker scripted|llm` and
`--normal-traffic scripted|llm` on start/reset. Red LLM mode disables the scripted
malicious actor; green LLM mode disables automatic normal workflows while keeping
the clock alive. Corresponding role logins are gated by these human choices.
Red and green have separate workstations, no blue key and no instructor journal.
Green is UID 65534 and offers `green-work` actions with an observation journal.
All three roles can save reports under their own `/var/lib/soc-ai`; exports keep
these separate. LLM-driven red activity is unscored, not labelled a scripted success.

## Clean starts

Every new start/reset clears live journals, all role findings and shell histories,
target authentication/application logs, SQL general logs and readiness-probe mail
before the collector and actors begin. Seeded business fixtures remain available.
The new run has its own `/var/log/soc-evidence/clean-start.json` identifier.
Reconnecting keeps the active investigation; saved host-side exports survive
case cleanup. Host operational SSH/audit logs are outside the disposable lab.
`python3 tools/rehearse_clean_start.py` verifies live-view isolation and retained exports.
