# Quickstart - operators

Use this guide to run an exercise on an **already installed** Paper Vianden
server. Participants follow the [participant quickstart](QUICKSTART.md). For
building, installing or updating the server, use the
[server administrator guide](docs/operators.md).

Get the deployment host and human account's SSH credentials privately. Replace
`range.example` below with that host. The configured human account (`vianden` in
these examples) controls the single shared exercise and enters the read-only
white workstation for observation. Agent accounts join their own workstations.

## 1. Reserve the exercise

Check whether someone is already using the range, then claim a slot using your
name:

```sh
ssh vianden@range.example 'range status'
ssh vianden@range.example 'range claim Alice --minutes 120'
```

**`range claim` generates and prints your reservation code.** The response
includes a JSON field named `token`, for example (shortened):

```json
{"token": "...your generated reservation code...", "holder": "Alice"}
```

Copy the complete value of `token`, without the surrounding quotes. Replace
`RESERVATION_CODE` in later commands with that value. The existing command-line
option is named `--token`; its value is the reservation code.

Keep the code with the human operator. It identifies who owns the reservation,
even when several people share the human SSH account. Participant agents only
need their role's SSH credentials. `range status` shows the holder and expiry,
but does not display the code. The same code works until release or expiry.

Only one exercise can run at a time. A competing claim is rejected while another
reservation is active or a previous run is still stopping. Reservation duration
uses real time; expiry stops the exercise.

## 2. Start the basic blue smoke test

The default runs a pre-programmed intruder and scripted ordinary employees:

```sh
ssh vianden@range.example 'range start --token RESERVATION_CODE --seed 42 --clock-speed 60'
ssh vianden@range.example 'range status'
```

Wait for `phase: ready`; cold startup can take several minutes. A 60x clock spans
24 simulated hours in about 24 minutes, plus actual protocol delays. The storyline
becomes idle after its simulated day; reset to start another exercise.

Every new start/reset clears live logs, workspace data, role findings, shell
histories, startup probe evidence and containment rules before actors begin.
Saved exports survive. Disconnecting from SSH keeps a managed exercise running.

Give participants the host, blue SSH credentials and
[participant guide](QUICKSTART.md#1-blue-team-with-the-pre-programmed-scenario).
Their agent connects as `vianden-agent-blue@range.example`. Models run outside
the range; the server supplies SSH workstations and tools.

## 3. Add a real red team, then green

Reset into real red mode while keeping ordinary employees scripted:

```sh
ssh vianden@range.example 'range reset --token RESERVATION_CODE --seed 42 --clock-speed 60 --attacker llm --normal-traffic scripted'
```

Wait for `phase: ready`, then give the red participant its role credentials,
objective and allowed lab actions. Its external model connects as
`vianden-agent-red@range.example`. **Red LLM mode disables the automatic malicious
storyline**; it never runs alongside the red model. External red activity is
unscored.

To add benign green activity as well:

```sh
ssh vianden@range.example 'range reset --token RESERVATION_CODE --seed 42 --clock-speed 60 --attacker llm --normal-traffic llm'
```

Wait for readiness, then provide the green role's credentials. Its model connects
as `vianden-agent-green@range.example`; `green-work all` exercises eight ordinary
workflows. **Green LLM mode disables automatic employee workflows** while keeping
the clock alive. The green model supplies ongoing normal activity.

Both traffic choices belong to the operator:

| Exercise | Flags on start/reset | Malicious activity | Ordinary activity |
| --- | --- | --- | --- |
| Basic blue test | Defaults | Scripted | Scripted |
| Add red LLM | `--attacker llm --normal-traffic scripted` | Red LLM | Scripted |
| Add red and green LLMs | `--attacker llm --normal-traffic llm` | Red LLM | Green LLM |
| Scripted intruder with green LLM | `--attacker scripted --normal-traffic llm` | Scripted | Green LLM |

Each reset archives the previous run and clears live investigation data. Confirm
the transition with participants. Supply both mode flags when changing modes;
omitting them selects the scripted defaults. Red/green logins are denied unless
their corresponding LLM mode is enabled.

## 4. Observe the exercise

The human account can inspect the analyst workspace and private observations:

```sh
ssh vianden@range.example 'observe status'
ssh vianden@range.example 'observe analyst'
ssh vianden@range.example 'observe story --tail 10'
ssh vianden@range.example 'observe green --tail 10'
```

Keep instructor observations and human credentials out of the participant models'
context. Blue investigates observed evidence through its own tools; white lets
you compare those findings with the simulated storyline. There is no automatic
assessment of an LLM's judgement.

## 5. Export results and release the reservation

Create an export and copy its returned `id` into `ARCHIVE_ID`:

```sh
ssh vianden@range.example 'range export --token RESERVATION_CODE'
ssh vianden@range.example 'range archives'
ssh vianden@range.example 'range download ARCHIVE_ID' > demo.tar.gz
ssh vianden@range.example 'range release --token RESERVATION_CODE'
ssh vianden@range.example 'range status'
```

Exports include observed evidence, cases, Markdown handovers and each role's
findings, as well as private instructor truth. Keep the complete archive with
the operator; provide participants their relevant findings separately. Check
`manifest.json` for omitted files. Normal teardown also attempts a bounded export;
forced termination or host failure can interrupt it.

`release` stops the range and frees the reservation. `stop --token
RESERVATION_CODE` stops it while retaining your reservation. To start fresh while
keeping the reservation, use `reset` with the chosen traffic flags. Reuse the same
reservation code until release or expiry; after expiry and cleanup, claim a new
slot.

For detailed evidence/API integration and rehearsal commands, see
[demo operations](docs/demo.md). For server installation, diagnostics and recovery,
see the [server administrator guide](docs/operators.md).
