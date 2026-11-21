# Corporate network and analyst coverage

This is a small environment for exercising an agent working as a SOC analyst.
It supplies real protocols, observable events and response controls within a
single disposable range. It is not a full production SOC distribution.

| Familiar component | This range |
| --- | --- |
| DMZ, internal LAN, management network | Separate routed bridges retain client source IPs; default deny between zones, with explicit business and administration exceptions. One intentional dual-homed SSH bastion supports the exercise. |
| Firewall and containment | Stateful iptables rules in the private inner namespace; audited block/unblock by workload IP through `analyst firewall`. No VPS rules or host modules are changed. |
| IDS | Suricata 8.0.8 passively observes DMZ/internal traffic. Four generic lab rules cover TCP scans, HTTP traversal, HTTP SQL unions and long DNS labels. EVE alerts, HTTP, DNS and TLS metadata enter the central feed. |
| IPS | No inline IPS. Prevention is the firewall and blue's target account controls. An IDS alert does not establish that traffic was blocked. |
| SIEM functions | Small collector for SSH/auth, web/API, SMB, SQL, FTP, mail, DNS and IDS evidence; bounded log search and an alert inbox. No Elastic/Splunk/Security Onion deployment, broad rule library or long-term data lake. |
| Analyst workspace | Cases, append-only notes, retained event snapshots, status, Markdown handovers and audit. Version checks coordinate concurrent blue agents. |
| Directory and identity | Seeded LDAP, Unix/SSH and application accounts. No Windows AD domain, Entra, MFA or enterprise identity lifecycle. |
| Business services | Web/DMZ applications, SQL, SMB, internal API, LDAP, mail and FTP; scripted or external green employee activity. DNS is an allowlisted, nonforwarding lab fixture. |
| Endpoint monitoring | Real service and authentication logs over SSH. No EDR agent, Windows event fleet or host-wide process telemetry. |
| Response and verification | Lab SSH administration, reversible IP containment, eight ordinary-work probes and separate human observations. Broad detection coverage and automated analyst grading remain future work. |

The evidence API requires a per-run bearer token mounted only into blue and the
collector. Red, green and white receive no token. The management firewall also
blocks workload access. White instead reads a snapshot through a read-only mount.
No analyst input is executed as a shell command by these APIs.

Log search covers the latest 5,000 normalized events, with cursor gap indicators
and rotated raw observations. The inbox retains at most 100 rule/host groups;
cases, notes and handovers have bounded counts and a 4 MiB workspace budget.
Export before resetting or when capacity is reached. Search time filters use the
collector's observation time; original source timestamps remain in each event.
Saved cases retain selected event snapshots beyond live-feed eviction.

Every start/reset clears live workspace data, terminal history, service logs,
IDS output and firewall blocks before actors start. Normal export includes
workspace JSON, Markdown handovers, raw IDS data and firewall audit along with
all role findings and instructor observations. The access-token volume is excluded from export.

Suricata uses passive [AF_PACKET capture](https://docs.suricata.io/en/suricata-8.0.2/manpages/suricata.html).
Its logs use the documented [EVE format](https://docs.suricata.io/en/suricata-8.0.2/output/eve/eve-json-format.html)
and [SIGHUP rotation](https://docs.suricata.io/en/suricata-8.0.2/output/log-rotation.html).
These small lab rules provide testable signals, not comprehensive detection.
