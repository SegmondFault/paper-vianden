# VulnCastle

Intentionally vulnerable multi-host lab environment for offensive security training, built with Docker Compose.

Inspired by the concepts in books like *Black Hat Bash* (No Starch Press), but built as an **original, independent** lab environment with unique architecture and vulnerabilities.

## Architecture

```
Attacker (Host Machine)
    │
    ▼
┌─── DMZ Network (172.20.1.0/24) ───────────────────────┐
│  web-01    (172.20.1.10) → localhost:8080               │
│    Nginx + PHP: XSS, Command Injection, LFI, Upload    │
│  mail-01   (172.20.1.11) → localhost:8025               │
│    Webmail: Info Disclosure, Hardcoded Creds, /debug     │
│  vpn-gw-01 (172.20.1.12) → localhost:2222 (SSH)         │
│    SUID binary, Pivot point ──────────────────────┐     │
└───────────────────────────────────────────────────┼─────┘
                                                    │
┌─── Internal Network (10.10.0.0/24) ───────────────┘
│  app-01    (10.10.0.13)  Node.js API: SSRF, IDOR, CMDi │
│  db-01     (10.10.0.14)  MariaDB: Weak auth, Cred leak │
│  file-01   (10.10.0.15)  Samba: Guest access, SMBv1     │
│  admin-01  (10.10.0.16)  SQLi, Redis (no auth)          │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose v2)

### Launch

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**Linux / macOS:**
```bash
chmod +x start.sh
./start.sh
```

**Or manually:**
```bash
docker build -t vulncastle-base:latest ./lab/base/
docker compose up -d --build
```

### Stop

**Windows:** `.\stop.ps1`
**Linux / macOS:** `./stop.sh`
**Or:** `docker compose down`

## Accessible Services

| Service | URL / Access | Network |
|---------|-------------|---------|
| Web Portal | http://localhost:8080 | DMZ |
| Webmail | http://localhost:8025 | DMZ |
| SSH Gateway | `ssh -p 2222 sysadmin@localhost` | DMZ |
| API Server | app-01:3000 (via pivot) | Internal |
| Database | db-01:3306 (via pivot) | Internal |
| File Share | file-01:445 (via pivot) | Internal |
| Admin Panel | admin-01:8080 (via pivot) | Internal |

## Vulnerability Map

| Category | Vulnerability | Location |
|----------|--------------|----------|
| Injection | OS Command Injection | web-01 (ping), app-01 (diagnostics) |
| Injection | SQL Injection | admin-01 (login) |
| XSS | Reflected XSS | web-01 (search) |
| File Handling | Unrestricted File Upload | web-01 (upload) |
| File Handling | Local File Inclusion / Path Traversal | web-01 (notes), app-01 (files) |
| Access Control | IDOR | app-01 (/api/users/:id) |
| Access Control | Broken Authentication | admin-01 (no session) |
| SSRF | Server-Side Request Forgery | app-01 (/api/fetch) |
| Privilege Escalation | SUID Binary | vpn-gw-01 (python3-suid) |
| Privilege Escalation | World-writable Cron Jobs | web-01, admin-01 |
| Privilege Escalation | Weak sudo Configuration | web-01, mail-01 |
| Information Disclosure | Debug Endpoints | mail-01 (/debug), app-01 (/api/health) |
| Information Disclosure | Hardcoded Credentials | mail-01, db-01, notes |
| Misconfiguration | Redis No Auth | admin-01 |
| Misconfiguration | Samba Guest Access | file-01 |
| Misconfiguration | Directory Listing | web-01 (/uploads/, /backup/) |
| Lateral Movement | Credential Reuse | DB service_accounts table |
| Lateral Movement | Network Pivoting | vpn-gw-01 (dual-homed + socat) |

## Attack Scenarios

### 1. Initial Reconnaissance
- Port scan DMZ hosts
- Enumerate web directories on web-01
- Discover debug endpoint on mail-01

### 2. Initial Access
- Exploit command injection on web-01
- Upload a web shell via unrestricted file upload
- Brute-force webmail credentials

### 3. Pivoting
- SSH to vpn-gw-01 with discovered credentials
- Use socat for port forwarding into internal network

### 4. Internal Exploitation
- SSRF on app-01 to scan internal services
- SQL injection on admin-01 to bypass authentication
- Redis key injection on admin-01
- Access Samba shares on file-01

### 5. Privilege Escalation
- SUID python3 on vpn-gw-01
- Writable cron jobs on web-01 / admin-01
- sudo misconfiguration (find, python3)

### 6. Data Exfiltration
- Customer PII from db-01
- Service account credentials from db-01
- Confidential files from file-01

## Disclaimer

**This environment is intentionally vulnerable and designed for authorized security training only.**

- DO NOT expose this lab to the internet or untrusted networks
- DO NOT use these techniques against systems without explicit authorization
- Use only in isolated, controlled environments

## License

MIT
