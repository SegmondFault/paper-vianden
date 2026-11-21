# Quickstart: blue first, then red, then green

Your SOC models run outside Paper Vianden and use SSH tools to work inside it.
Replace `range.example` with the deployment host. Get credentials privately from
the operator; passwords and instance addresses are not stored in this repository.
The human account controls the single shared exercise. Agent logins only join it.

See the [environment diagram](docs/environment.md) for the networks and workstations.

## 1. Blue team with the pre-programmed scenario

The human reserves and starts a fresh demo:

```sh
ssh vianden@range.example 'range claim Alice --minutes 120'
# Keep the returned TOKEN private. It belongs to the human, not the model.
ssh vianden@range.example 'range start --token TOKEN --seed 42 --clock-speed 60'
ssh vianden@range.example 'range status'
```

Wait for `phase: ready`; cold startup can take several minutes. Every new start
or reset clears live logs, findings and shell histories across all four roles
before exercise traffic begins. Saved exports stay outside the live run. This default runs
scripted ordinary employees and the pre-programmed intrusion. A 60x clock spans
24 simulated hours in about 24 minutes, plus actual protocol delays.

Connect the blue SOC architecture's SSH tool to:

```sh
ssh vianden-agent-blue@range.example 'hostname'
ssh vianden-agent-blue@range.example 'evidence status'
ssh vianden-agent-blue@range.example 'evidence tail --limit 100'
```

It lands in `defender`, can discover services, inspect the central evidence feed
and administer lab targets. A small analyst workspace is available through
`analyst`; it uses the same SSH tool connection. Interactive tools can use `ssh -t`. Up to 16 parallel
workstation sessions per account join the same scenario. Start the blue model
with a task such as: **Discover the network, investigate suspicious activity,
explain the evidence, and propose or carry out a targeted response.**

A basic investigation looks like this (replace IDs and versions with the returned values):

```sh
ssh vianden-agent-blue@range.example 'analyst assets'
ssh vianden-agent-blue@range.example 'analyst inbox'
ssh vianden-agent-blue@range.example 'analyst logs --query "Failed password" --host file-01.internal --limit 50'
ssh vianden-agent-blue@range.example 'analyst open "Investigate suspicious login" --alert ALERT_ID'
ssh vianden-agent-blue@range.example 'analyst note CASE_ID "Observed repeated failures; checking source" --event EVENT_ID --version 1'
ssh vianden-agent-blue@range.example 'analyst status CASE_ID investigating --version 2'
ssh vianden-agent-blue@range.example 'analyst handover CASE_ID --version 3 --summary "Evidence and current assessment" --actions "Actions taken and business checks" --next-steps "Outstanding questions and next owner"'
```

Omit `--alert` to open a case directly. `analyst cases`, `analyst case CASE_ID`
and `analyst audit` show saved work. Each update returns a new `version`; use it
for the next change so concurrent agents cannot overwrite one another. Notes can
retain an event snapshot after it leaves the bounded live log feed. Search also
accepts `--source`, `--since` and `--until` (ISO timestamps with UTC offsets).

The inbox contains alerts from real Suricata observations and an authentication
failure rule; it does not consume instructor truth. The rules are intentionally
small, so agents should also search logs. See [security coverage](docs/security.md).
For reversible network containment, use an address from `analyst assets`:

```sh
ssh vianden-agent-blue@range.example 'analyst firewall status'
ssh vianden-agent-blue@range.example 'analyst firewall block --ip LAB_IP --reason "Contain observed source; case CASE_ID"'
ssh vianden-agent-blue@range.example 'evidence availability'
ssh vianden-agent-blue@range.example 'analyst firewall unblock --ip LAB_IP --reason "Investigation complete; case CASE_ID"'
```

These actions affect only the disposable network and are audited. Blocking a
business service can interrupt legitimate work; verify the eight ordinary
workflows and record the result in the case. Target account controls remain
available through blue's lab SSH access. `observe analyst` gives the human a
read-only view of the workspace.

The model can use `evidence tail --after CURSOR` to poll events and
`evidence availability` to check ordinary work. Save its findings/actions under
`/var/lib/soc-ai`. The human separately watches truth:

```sh
ssh vianden@range.example 'observe status'
ssh vianden@range.example 'observe story --tail 10'
```

Keep human credentials and instructor notes out of the blue model's context.
The storyline becomes idle after 24 simulated hours; a human reset starts fresh.

## 2. Replace the scripted intruder with a real red-team LLM

The same human lease holder resets into red LLM mode:

```sh
ssh vianden@range.example 'range reset --token TOKEN --seed 42 --clock-speed 60 --attacker llm --normal-traffic scripted'
# Wait for phase: ready again.
ssh vianden-agent-red@range.example 'hostname'
```

Connect your external red model's SSH tool using the red account. It lands in
`red`, with DMZ access and tools, but no blue administrator key or instructor
journal. Blue continues through its own account; ordinary employees are still
scripted. **The automatic malicious storyline is disabled in this mode.** It
never runs alongside the red LLM. White reports external red activity as unscored;
review its actual effects through the evidence feed rather than a scripted score.

The human chooses the red model's objective and allowed lab actions. Models run
outside the range; the role portal supplies their terminal, not a model API.
Red logins are rejected when the human has selected a scripted attacker.

## 3. Replace scripted employees with a benign green-team LLM

To use blue, red and green models together:

```sh
ssh vianden@range.example 'range reset --token TOKEN --seed 42 --clock-speed 60 --attacker llm --normal-traffic llm'
# Wait for phase: ready again.
ssh vianden-agent-green@range.example 'hostname'
ssh vianden-agent-green@range.example 'green-work all'
```

Connect the external green model through the green account and assign ordinary
business activity: browse, read public shares, check mail, query the directory
and run routine reports. `green-work web`, `green-work mail` and the other named
workflows provide simple normal actions. They create real service requests and
a green activity journal. The account is unprivileged inside `green`, with no
administrator key, Docker socket or instructor truth.

**Automatic employee workflows are disabled in green LLM mode.** The exercise
clock keeps running, and readiness probes still work. Only the green model
supplies ongoing ordinary activity. The human can inspect `observe green`.
Green logins are rejected when scripted normal traffic is selected.

To combine a scripted intruder with a green LLM instead, use
`--attacker scripted --normal-traffic llm`. Both choices belong to the human:

| Human selection | Malicious activity | Ordinary activity |
| --- | --- | --- |
| Defaults | Scripted | Scripted |
| `--attacker llm` | Red LLM | Scripted |
| `--normal-traffic llm` | Scripted | Green LLM |
| Both flags set to `llm` | Red LLM | Green LLM |

## Save results and finish

Alerts, cases, notes and generated Markdown handovers are exported with evidence.
A fresh start/reset clears them, their API token, IDS logs and containment rules.
All agent roles can save reports under their own `/var/lib/soc-ai`. Reset and
normal teardown archive evidence and findings outside the disposable run.
Archives also contain private instructor truth, so give them to the human owner.

```sh
ssh vianden@range.example 'range export --token TOKEN'
ssh vianden@range.example 'range archives'
ssh vianden@range.example 'range download ARCHIVE_ID' > demo.tar.gz
ssh vianden@range.example 'range release --token TOKEN'
```

Release stops the exercise and frees the human reservation. A second person
cannot claim it while that lease is active, even through the same human account.
Review the export's `manifest.json` for omitted files; forced kills and host
failure can interrupt export. See [demo operations](docs/demo.md) for details,
[SSH setup](docs/ssh-access.md) for operators, and [the scenario](docs/scenario.md)
for the default storyline.
