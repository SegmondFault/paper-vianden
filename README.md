# Paper Vianden

An on-demand, disposable network for attack and defence testing.

One Sysbox system container runs 25 service and workstation containers across
management, DMZ and internal networks. Python owns the lifecycle; Docker Compose
describes services. 

## Use an installed range

Log into the operator account, then run:

```sh
./range-status          # Does not start anything
./start-range           # Fresh network, then a blue workstation shell
```

Exit that owner shell to destroy the session. In another login, use
`./join-range --red` for a participant workstation or
`./join-range --control` to administer lab containers. Joining never starts a
range. `./stop-range` ends the session; `./start-range --check` starts, tests
the protocols and destroys it.

## Capabilities

SSH, HTTP/PHP, SQL, SMB, Redis, LDAP, SNMP, FTP, captured SMTP, IMAP, POP3,
vulnerable web applications, a badge-reader simulator, a 32-bit teaching server
and packet/password/debugging tools. Lightweight synthetic users and an inert
24-hour intrusion storyline (simulated foothold, discovery, fixture-account
movement, staging and DNS transfer) start and stop with the range. Use
`./start-range --seed 42 --clock-speed 60` for a reproducible 24-minute variant;
change the seed for different workflow mixes and timing. DNS timing is jittered,
and blue receives raw evidence rather than storyline answer journals.
Fixtures and passwords are synthetic.
See [services](docs/services.md) and the [user guide](docs/users.md).

## Installation and boundaries

An administrator prepares an offline library and installs a root-owned release
with a restricted operator account. Nothing starts at boot, login or installation.
Each invocation uses its own Docker daemon, socket and disposable filesystem;
it does not reconfigure or restart the host Docker daemon. Targets have no
host-published ports or external route.

The outer container has a 4 CPU, 6 GiB RAM and 2,048-task cap; the whole session
service has a 7 GiB ceiling. Mutable storage has a 32 GiB filesystem limit.
Images remain cached separately. Sysbox shares the host kernel; it is not a VM.

Read the [operator guide](docs/operators.md), [architecture](docs/architecture.md)
and [validation record](docs/validation.md). Native amd64 protocol, reset and
cleanup checks pass. A separately tested [local prototype](docs/prototype.md)
remains available for development.

## Licence

Original code and documentation use [MIT](LICENSE). Dependencies retain their
licences. Attribution and pins are in [notices](THIRD_PARTY_NOTICES.md) and
[sources.json](sources.json). Clone with:

```sh
git clone --recurse-submodules https://github.com/SegmondFault/paper-vianden.git
```
