# Linux service prototype

This source-only prototype adapts VulnCastle. Its original README is retained
in UPSTREAM.md, with attribution in ../THIRD_PARTY_NOTICES.md.

It has been tested locally using a Linux ARM64 Docker engine. AMD64 validation
and Sysbox integration are pending. It runs its containers on the selected
Docker engine directly; it does not create the planned outer sandbox.

See ../docs/users.md for commands and ../docs/services.md for coverage.
