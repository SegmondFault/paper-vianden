# Contributing

Use Python for lifecycle code and Compose YAML for network/service definitions.
Prefer existing tools and images over implementing service daemons. Keep changes
small and document both supported behaviour and known gaps.

Do not commit keys, credentials, runtime records, server inventories or restricted
scenario material. Published weak target credentials must be clearly synthetic.

Preserve third-party copyright/licence notices and record upstream revisions.
The project licence covers original Paper Vianden contributions; dependencies
and imported source retain their own licensing.

Verify changes at the boundary they affect: Compose configuration, service
functionality, clean seed reset, cleanup after interruption, and absence of
changes to unrelated workloads. Do not present local ARM64 testing as server
AMD64 validation. Record images and source commits for runtime tests.
