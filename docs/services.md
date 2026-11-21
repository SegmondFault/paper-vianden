# Service capabilities

The current local prototype provides the following capabilities. The additional
services are being integrated into the disposable sandbox; availability of a
source component is not a claim of validated runtime support.

| Capability | Current local prototype | Additional implementation |
| --- | --- | --- |
| Network segmentation | DMZ and internal segments | Disposable outer boundary |
| SSH and pivoting | Weak Linux accounts, management keys, dual-homed gateway | Separate participant console |
| HTTP/PHP portal | Upload, file-read and command-execution weaknesses | Additional web targets |
| SQL | MariaDB with synthetic records | Separate vulnerable-web application database |
| SMB | Guest and authenticated Samba shares | Existing protocol retained |
| API/admin/Redis | Present | Existing targets retained |
| Directory services | Not present | OpenLDAP and administration UI |
| SNMP | Not present | Simulated router endpoint |
| FTP | Not present | Anonymous file service |
| Mail protocols | HTTP mailbox mock only | SMTP capture, IMAP and POP3 |
| Vulnerable web applications | Simple portal and API | DVWA and Juice Shop |
| Packet analysis | tcpdump on individual nodes | Headless packet-analysis tools |
| Password analysis | Weak accounts only | Hash and credential-testing tools |
| Binary analysis | Not present | 32-bit teaching server and debugger tools |
| Physical-access simulation | Not present | Badge-reader HTTP simulator |
| Mail-based simulation | Not present | Internal campaign tooling and captured delivery |

OpenLDAP is not a Windows Active Directory domain controller. Actual AD, radio
hardware, mobile devices and industrial process models are outside this version.

The existing applications are independent training fixtures. The API uses
in-memory records; the admin login uses SQLite; the PHP portal does not use the
MariaDB customer database. This is a service network, not a complete connected
business application or a normal-traffic generator.

For current endpoints and synthetic credentials, see the
[user guide](users.md#find-the-services). Runtime support is recorded separately
in the [validation record](validation.md).
