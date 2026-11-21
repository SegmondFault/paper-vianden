# Development notes / TODOs

Public roadmap items. These are planned work, not implemented features or
instructions for the agent being evaluated. No deployment credentials belong here.

- [x] **Red and green VPS portals.** Separate account-bound workstations and human-selected scripted/LLM modes are implemented; see the [Quickstart](../QUICKSTART.md).
- [ ] **Create a flat scenario.** Agree the intended topology and storyline
  scope before implementation; do not assume that "flat" means either an
  unsegmented network or a single-stage story without confirmation.
- [ ] **Stretch goal: flags.** Add optional flags and completion criteria for
  exercises, without exposing the instructor answers to the analyst.
- [ ] **Stretch goal: deeper validation.** Expand scenario, detection and
  response validation, including false positives, missed detections and repeatable
  assessment of an agent's investigation and handover. This is future work;
  routine functional checks remain part of each implemented change.

For what is implemented today, see [scenario overview](scenario.md) and
[SSH workstation access](ssh-access.md).
