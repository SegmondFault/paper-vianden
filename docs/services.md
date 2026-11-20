# Service coverage

This matrix distinguishes the tested prototype from available upstream material.
Upstream availability does not imply that a service is integrated or tested here.

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

Week 10's upstream privileged host-ASLR changes must not be copied unchanged
onto a shared host. Architecture requirements and per-session containment need
validation before that module is supported. All modules must follow the common
on-demand lifecycle and leave unrelated host workloads unchanged.
