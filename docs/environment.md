# Simulated environment

The diagram shows the full encapsulated runtime. Its generated corporate overlay
adds routing policy and the IDS to the development Compose fixtures.
Dotted arrows are terminal/control paths through the VPS portal, not exposed
service ports. Models run outside the range. The human chooses both traffic modes.

```mermaid
flowchart TB
  human["Human owner / observer"]
  blueModel["External blue SOC AI"]
  redModel["External red LLM · optional"]
  greenModel["External benign green LLM · optional"]

  subgraph VPS["VPS · existing SSH service"]
    gate["Human lease + private reservation code<br/>start · reset · export · stop"]
    portals["Fixed SSH account → role mapping<br/>parallel agent sessions · one shared run"]
    archives["Durable private evidence archives<br/>blue/red/green findings + instructor truth"]

    subgraph Envelope["Disposable Sysbox envelope · its own Docker · no external route"]
      mgmt{{"Management bridge"}}
      dmz{{"DMZ bridge"}}
      internal{{"Internal bridge"}}
      entrynet{{"Legacy entry bridge"}}

      blue["Blue: defender<br/>admin key for lab targets"]
      white["White: read-only observer<br/>UID 65534 · private truth"]
      red["Red workstation<br/>DMZ only · no blue key"]
      green["Green workstation<br/>UID 65534 · ordinary work tools"]
      sensor["Central evidence collector<br/>logs · alert inbox · cases · handovers"]
      employees["Scripted employees + clock<br/>workflows off in green LLM mode"]
      actor["Scripted intruder<br/>actions off in red LLM mode"]
      shared["Dual-homed SSH bastion<br/>vpn-gw-01"]
      dmzServices["DMZ fixtures<br/>web-01 · ftp · mail-01 · mail-sink<br/>dvwa · scenario-sink<br/>juice-shop · phishing · silent"]
      internalServices["Internal fixtures<br/>db-01 · file-01 · app-01 · admin-01<br/>ldap · ldap-admin · snmp · mail · badge · bof"]
      relay["Legacy entry relay<br/>no host-published port"]

      blue --- mgmt
      white --- mgmt
      sensor --- mgmt
      red --- dmz
      green --- internal
      employees --- internal
      firewall["Stateful inner firewall<br/>default deny between zones · bounded containment"]
      ids["Suricata passive IDS<br/>DMZ + internal bridge capture → evidence"]
      mgmt --- firewall
      firewall --- dmz
      firewall --- internal
      ids -. observations .-> sensor
      dmz -. capture .-> ids
      internal -. capture .-> ids
      actor --- dmz
      shared --- dmz
      shared --- internal
      dmzServices --- dmz
      internalServices --- internal
      relay --- entrynet
      relay --- mgmt
    end

    portals -. terminal .-> blue
    portals -. terminal .-> red
    portals -. terminal .-> green
    portals -. terminal .-> white
    gate -. lifecycle .-> Envelope
    white -. fixed exporter .-> archives
  end

  human --> gate
  human --> portals
  blueModel --> portals
  redModel --> portals
  greenModel --> portals
```

The three main zones are management, DMZ and internal. Blue and telemetry are
management-only; employees and green are internal-only; red is DMZ-only. The
intentional dual-homed SSH bastion remains a scenario pivot. Other cross-zone
traffic uses the inner Docker bridge gateways and a stateful firewall: blue and
telemetry can manage lab targets, DVWA can reach its database, and internal users
can reach the lab's public web/mail/FTP/DNS services. Other cross-zone requests
are dropped. The small internal LAN is not microsegmented.

Suricata captures the two workload bridges in the **inner system container's
network namespace**, with no VPS interfaces, Docker socket or host-published
listener. Namespace and route checks reject running these controls on a normal
host. Development Compose smoke tests omit this inner-only overlay.

No target service or evidence API is published on the VPS host. The host Docker
socket is absent from agent workstations. Blue has lab administration access;
red and green have no blue key or instructor journal. White normally runs with
no effective capabilities and read-only mounts. A fixed root export process can
read private findings from the different lab UIDs; downloads go to the human.

There are **29 containers**. The table below is derived from the full runtime Compose
configuration; groups in the diagram combine individual fixtures for readability.

| Container | Compose networks |
| --- | --- |
| `activity` | internal |
| `admin-01` | internal |
| `app-01` | internal |
| `badge` | internal |
| `bof` | internal |
| `db-01` | internal |
| `defender` | management |
| `dvwa` | dmz |
| `entry` | entry, management |
| `file-01` | internal |
| `ftp` | dmz |
| `green` | internal |
| `ids` | inner system container namespace; passive bridge capture |
| `juice-shop` | dmz |
| `ldap` | internal |
| `ldap-admin` | internal |
| `mail` | internal |
| `mail-01` | dmz |
| `mail-sink` | dmz |
| `phishing` | dmz |
| `red` | dmz |
| `scenario-runner` | dmz |
| `scenario-sink` | dmz |
| `silent` | dmz |
| `snmp` | internal |
| `telemetry` | management |
| `vpn-gw-01` | dmz, internal |
| `web-01` | dmz |
| `white` | management |
