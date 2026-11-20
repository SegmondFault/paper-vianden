# Service coverage

This matrix distinguishes the tested prototype from available upstream material.
Upstream availability does not imply that a service is integrated or tested here.
For current endpoints and synthetic credentials, see the [user guide](users.md#find-the-services).

| Capability | Current prototype | Learn-to-hack source / planned work |
| --- | --- | --- |
| Segmented network and SSH pivot | DMZ/internal segments; dual-homed SSH gateway | Week 9 pivot topology; separate participant entry pending |
| Linux SSH targets | Weak lab accounts and management keys | Weeks 4, 6, 8 and 9 |
| HTTP/PHP portal | Nginx/PHP, uploads and other intentional weaknesses | Weeks 4 and 8 web targets |
| SQL database | MariaDB and synthetic records | Weeks 4, 5, 7 and 9 MySQL exercises |
| SMB | Samba guest/authenticated shares | Week 5 enumeration |
| API/admin/Redis | Present | Additional VulnCastle targets |
| Directory services | Absent | Week 5 OpenLDAP and phpLDAPadmin |
| SNMP | Absent | Week 5 simulator |
| FTP | Absent | Week 8 service |
| Actual mail protocols | Absent; webmail is an HTTP mock | Week 8 SMTP and Dovecot; Week 12 MailHog |
| DVWA and Juice Shop | Absent | Week 7 vulnerable applications |
| Packet analysis | tcpdump on individual nodes; no central sensor | Weeks 1/3/7 Wireshark and sample captures |
| Password exercises | Weak accounts only | Week 6 tools, hashes and wordlists |
| Exploit development | Absent | Week 10 32-bit x86 C target and debugger tools |
| Badge-reader simulation | Absent | Week 11 Python simulation |
| Phishing simulation | Absent | Week 12 GoPhish with internal MailHog delivery |
| Ethics, scope and reporting | No runtime required | Course documentation |

The linked directory exercise uses OpenLDAP, not a Windows Active Directory
domain controller. Actual AD is a separate capability and is not currently
included. Wi-Fi radios, mobile hardware and industrial process models are also
outside the current implementation.

The existing applications are independent training fixtures, not a connected
business system: the API uses in-memory records, the admin login uses its own
SQLite database, and the PHP portal does not use the MariaDB customer database.
Service availability is useful for protocol and administration experiments, but
does not establish a realistic end-to-end business workflow or traffic baseline.

Week 10's upstream privileged host-ASLR changes must not be copied unchanged
onto a shared host. Architecture requirements and per-session containment need
validation before that module is supported. All modules must follow the common
on-demand lifecycle and leave unrelated host workloads unchanged.

## Read the source exercises

These links open the pinned upstream revision. The guides describe their own
standalone labs; their launchers do not yet use Paper Vianden's planned envelope.

- [Week 1: setup and packet tools](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week1)
- [Week 2: ethics](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week2)
- [Week 3: traffic analysis](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week3)
- [Week 4: scanning/reporting](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week4)
- [Week 5: LDAP, SMB, SQL and SNMP](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week5)
- [Week 6: password exercises](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week6)
- [Week 7: web applications](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week7)
- [Week 8: privilege escalation and services](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week8)
- [Week 9: pivoting](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week9)
- [Week 10: exploit development](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week10)
- [Week 11: badge-reader simulation](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week11)
- [Week 12: phishing/mail simulation](https://github.com/michael-borck/ethical-hacking-docker-labs/tree/60d981e509ea186be0c31d1ea1cbb536fa6f387e/labs/week12)
