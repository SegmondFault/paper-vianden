# Architecture

This document describes the target design, not a deployed implementation.
It is one disposable Sysbox system container containing its own
Docker daemon and the complete training network. The outer sandbox is the unit
of lifecycle and aggregate resource control. Docker Compose defines services and
segments inside it. A small Python controller owns session creation and cleanup.

```text
Server
  administrator-owned launcher and image library
    disposable Sysbox envelope
      private Docker daemon
        management / participant access
        DMZ services
        internal services
        selected course targets
```

Session creation is explicit. The controller provides access after services are
ready and removes session resources after normal exit or cancellation. Host
shutdown, power loss and forced termination need a tested recovery policy;
cleanup must not be promised solely on the basis of a Python finally block.

No host Docker socket enters the sandbox. The runtime image library may remain
cached, but mutable target state and temporary credentials belong to the session.
Evidence retained after teardown must be an explicit export, with a documented
storage budget.

The current prototype under prototype/ implements the inner Linux service
network only. It does not implement the outer envelope or one-shot lifecycle.
Its existing down/reset commands save local records automatically; the final
session's explicit evidence-export policy has not yet been implemented.

## Design constraints

- Reuse service images, course fixtures and standard runtime behaviour.
- Keep custom code to lifecycle, access and evidence glue.
- Start only on invocation; no automatic boot/login/scheduled startup.
- Restore seed state for a fresh session.
- Preserve unrelated server services, networking and data.
- Pin upstream revisions and deployment commits.
- Keep real credentials and restricted exercise documents outside Git.
