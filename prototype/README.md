# Linux service prototype

This source-only prototype adapts VulnCastle. Its original README is retained
in UPSTREAM.md, with attribution in ../THIRD_PARTY_NOTICES.md.

It has been tested locally using a Linux ARM64 Docker engine. AMD64 validation
and Sysbox integration are pending. It runs its containers on the selected
Docker engine directly; it does not create the planned outer sandbox.

See the [user guide](../docs/users.md) for commands and the
[coverage matrix](../docs/services.md) for available services.

Use the root Dockerfile and ./range launcher. The retained per-service
Dockerfiles, PowerShell launchers and UPSTREAM.md are upstream reference
material; they are not the supported Paper Vianden launch path.
