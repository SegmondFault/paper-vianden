# Contributing

Use Python for lifecycle code and Compose YAML for network/service definitions.
Prefer existing tools and images over implementing service daemons. Keep changes
small and document both supported behaviour and known gaps.

Enable the public-source checks in your checkout:

```sh
git config core.hooksPath .githooks
python3 tools/check_public_tree.py
python3 tools/check_public_tree.py --history
```

The hooks reject private document/data paths, classified labels and common
credential formats. They inspect Git objects, so force-adding an ignored document
does not bypass the check. Review provenance as well: generic automated checks
cannot recognize confidential prose without identifying labels. Do not copy
source exercise documents, meeting notes or server records into public guides.

For the current prototype, these checks do not start a range:

```sh
python3 -m py_compile prototype/range
bash -n prototype/scripts/node-init.sh prototype/scripts/workstation-init.sh prototype/start.sh prototype/stop.sh
./prototype/range config
./prototype/range config --minimal
git diff --check
```

Use the [user guide](docs/users.md) for runtime validation on a dedicated lab
engine, including explicit shutdown. Preserve the course source as a pinned
submodule; document changes to sources.json when its revision changes.

Do not commit keys, credentials, runtime records, server inventories or restricted
scenario material. Published weak target credentials must be clearly synthetic.

Preserve third-party copyright/licence notices and record upstream revisions.
The project licence covers original Paper Vianden contributions; dependencies
and imported source retain their own licensing.

Verify changes at the boundary they affect: Compose configuration, service
functionality, clean seed reset, cleanup after interruption, and absence of
changes to unrelated workloads. Do not present local ARM64 testing as server
AMD64 validation. Record images and source commits for runtime tests.
