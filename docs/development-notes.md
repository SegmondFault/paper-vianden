# Development notes / TODOs

Public roadmap items. These are planned work, not implemented features or
instructions for the agent being evaluated. No deployment credentials belong here.

- [ ] **Red portal — attacker LLM.** Add a dedicated, server-enforced SSH entry
  point for an attacker-side agent, separate from blue and white. The existing
  red tooling workstation is not yet an account-bound attacker portal. Keep
  host administration and white ground truth out of the attacker context.
- [ ] **Green portal — normal-traffic LLM.** Add a role for an agent whose job is
  to simulate ordinary user/business activity with synthetic data. Treat this as
  an additional traffic-generation option; the current lightweight seeded
  employee scheduler remains the reproducible baseline. Define the green
  agent's permitted accounts/actions and record its activity for white-team
  observation.
- [ ] **Create a flat scenario.** Agree the intended topology and storyline
  scope before implementation; do not assume that "flat" means either an
  unsegmented network or a single-stage story without confirmation.

For what is implemented today, see [scenario overview](scenario.md) and
[SSH workstation access](ssh-access.md).
