# Service capabilities

The combined configuration has 27 containers. Runtime verification is recorded
separately in the [validation record](validation.md).

| Area | Services / tools |
| --- | --- |
| Network | Management, DMZ and internal bridges; dual-homed gateway |
| Access | Blue workstation, DMZ participant, administrative control console |
| Linux / SSH | Weak accounts, management keys, pivoting |
| Web | PHP portal, Node API, admin panel, DVWA, Juice Shop |
| Data | MariaDB fixtures, application database, Redis |
| Files | Guest/authenticated Samba, anonymous FTP |
| Directory | OpenLDAP and phpLDAPadmin |
| Enumeration | SNMP router simulator, silent host, nmap |
| Mail | HTTP mailbox mock, IMAP/POP3, captured SMTP with inbox UI |
| Campaign simulation | Internal campaign manager and landing pages |
| Binary / debugging | 32-bit teaching server, gdb, compiler, pwntools |
| Access simulation | HTTP badge-reader simulator |
| Analysis | tcpdump, headless tshark, Hydra, John, Hashcat, sqlmap |

Hashcat is installed without a GPU or OpenCL compute backend. Use John for
CPU-only exercises, or add a compatible backend in a derived image.

Captured mail never delivers externally. OpenLDAP is not Windows Active
Directory. There is no wireless hardware, industrial process, desktop Wireshark
GUI or model runtime. Host ASLR remains enabled; the teaching binary is non-PIE.

Applications are independent fixtures rather than one connected business
application. The disposable runtime adds lightweight synthetic users and an
inert, clock-scaled DNS-transfer storyline; see [scenario](users.md#simulated-users-and-storyline).
No scoring engine or central traffic mirror is included.
See [endpoints](users.md#find-the-services).

Central evidence collection and durable demo exports are described in the [demo guide](demo.md).
