# Paper Vianden

A disposable, on-demand cyber range for attack and defence.

Paper Vianden is being assembled as shared infrastructure for people to test
their own tools and ideas. Python handles session lifecycle; Docker Compose YAML
describes the service network. Existing lab software supplies the targets.

## Current status

This first revision contains the locally tested VulnCastle-based prototype,
project documentation, and a pinned copy of Michael Borck's learn-to-hack labs.
The prototype starts, provides management access, collects basic logs and resets.
It has seven targets and nine containers in total.

The Sysbox envelope, combined learn-to-hack service configuration and automatic
session destruction are **not implemented yet**. The prototype is not the final
server deployment. Creating this repository does not start or install a range.

## Try the working prototype locally

Use a dedicated local Linux Docker engine, Docker Desktop, or WSL2. Requirements
are Python 3.9+, Git, OpenSSH tools and Docker Compose v2.20+.

```sh
git clone --recurse-submodules https://github.com/SegmondFault/paper-vianden.git
cd paper-vianden/prototype
./range init
./range config
./range build
./range up --no-build
./range check
./range login
```

config should report nine services. up waits for their health checks; check
reports PASS for the ordinary service and management-access checks. login opens
the management workstation. From there, try curl http://web-01.dmz/.

After leaving that shell, stop the prototype explicitly:

```sh
./range down --volumes
```

This discards target changes and database data after saving logs. Images, access
keys and saved logs remain. Exiting the workstation alone does not stop the
prototype. See the [user guide](docs/users.md) for endpoints, credentials, browser
access, reset behaviour and troubleshooting.

## Intended use

The finished user interface will create one fresh session on explicit invocation,
provide access to its isolated network, and destroy session containers, networks,
temporary credentials and mutable data when the session ends. Evidence export
will be explicit. No boot, login or scheduled range startup is intended.

Sysbox will host a separate Docker daemon inside the disposable envelope. The
host Docker socket will remain outside the range. The shared server's existing
Docker configuration and workloads must be preserved during setup.

## Documentation

- [User guide](docs/users.md): current prototype commands and planned session use.
- [Service coverage](docs/services.md): what exists and what remains to integrate.
- [Operator guide](docs/operators.md): installation boundary and Git deployment.
- [Architecture](docs/architecture.md): encapsulation and lifecycle design.
- [Contributing](CONTRIBUTING.md): changes, tests and attribution.
- [Validation record](docs/validation.md): what has actually been checked.

## Sources and licence

Our original code and documentation use the [MIT licence](LICENSE). Third-party
components retain their own licences. See [third-party notices](THIRD_PARTY_NOTICES.md)
and [source revisions](sources.json).

The range builds on [VulnCastle](https://github.com/0x6d61/vulncastle) and
[Ethical Hacking Docker Labs](https://github.com/michael-borck/ethical-hacking-docker-labs).
The course source is a Git submodule; clone with --recurse-submodules.
