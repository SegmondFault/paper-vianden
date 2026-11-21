"""Non-exploit protocol checks, executed inside the management workstation."""
import ftplib
import imaplib
import poplib
import smtplib
import socket
import subprocess
import sys
import time
import urllib.request


def http(url):
    return urllib.request.urlopen(url, timeout=8).read().decode(errors='replace')


def cli(*args):
    return subprocess.check_output(args, text=True, timeout=15)


def sql(query):
    return cli('env', 'MYSQL_PWD=S3cretDB!2024', 'mariadb', '--skip-ssl',
               '--connect-timeout=5', '-h', 'db-01.internal', '-u', 'root', '-N', '-e', query)


def contains(expected, actual):
    assert expected in actual, 'Expected seeded content was absent'


def redis():
    with socket.create_connection(('admin-01.internal', 6379), timeout=5) as sock:
        sock.sendall(b'*1\r\n$4\r\nPING\r\n')
        assert sock.recv(128) == b'+PONG\r\n'


def mail():
    with smtplib.SMTP('mail-sink.dmz', 1025, timeout=8) as smtp:
        smtp.sendmail('check@range.test', ['analyst@range.test'],
                      'Subject: Paper Vianden health check\r\n\r\nSynthetic internal test.\r\n')
    with imaplib.IMAP4('mail.internal', 143, timeout=8) as imap:
        imap.login('sysadmin', 'admin123')
        assert imap.select('INBOX')[0] == 'OK'
    pop = poplib.POP3('mail.internal', 110, timeout=8)
    try:
        pop.user('sysadmin'); pop.pass_('admin123')
        assert pop.stat()[0] >= 1
    finally:
        pop.quit()


def ftp():
    with ftplib.FTP('ftp.dmz', timeout=8) as client:
        client.login()
        assert client.nlst()


def bof():
    with socket.create_connection(('bof.internal', 4444), timeout=5) as sock:
        def until(text):
            data = b''
            while text not in data:
                part = sock.recv(4096)
                if not part: break
                data += part
            return data
        until(b'Username:'); sock.sendall(b'guest\n')
        until(b'Password:'); sock.sendall(b'letmein123\n')
        assert b'SECRET MENU' in until(b'Access granted.')


def activity():
    import json
    from pathlib import Path
    state = json.loads(Path('/var/log/simulated-users/status.json').read_text())
    assert state['state'] == 'running' and time.time()-state['last_tick'] < 90
    assert state['mode'] in ('active','idle','complete','external')
    assert 0 <= state['scenario_seconds'] <= 86400
    assert 1 <= state['clock_speed'] <= 3600
    # Story health is checked from its container, never via a blue answer-key mount.


checks = [
    ('portal', lambda: http('http://web-01.dmz/')),
    ('SSH gateway', lambda: cli('ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', 'vpn-gw-01.internal', 'hostname')),
    ('SMB public share', lambda: cli('smbclient', '//file-01.internal/public', '-N', '-c', 'ls')),
    ('SQL seed records', lambda: contains('5', sql('SELECT COUNT(*) FROM acme_corp.customers'))),
    ('LDAP seeded directory', lambda: contains('uid=adminservice', cli('ldapsearch', '-x', '-H', 'ldap://ldap.internal', '-b', 'dc=enum,dc=lab'))),
    ('LDAP administration UI', lambda: http('http://ldap-admin.internal/')),
    ('SNMP router fixture', lambda: cli('snmpget', '-v2c', '-c', 'public', '-t', '3', '-r', '0', 'router.internal', '.1.3.6.1.2.1.1.1.0')),
    ('FTP anonymous listing', ftp),
    ('SMTP, IMAP and POP3', mail),
    ('mail capture UI', lambda: http('http://mail-sink.dmz:8025/')),
    ('DVWA schema', lambda: contains('5', sql('SELECT COUNT(*) FROM dvwa.users'))),
    ('DVWA HTTP', lambda: http('http://dvwa.dmz/login.php')),
    ('Juice Shop', lambda: http('http://juice-shop.dmz:3000/')),
    ('admin panel', lambda: http('http://admin-01.internal:8080/')),
    ('Redis', redis),
    ('internal API', lambda: http('http://app-01.internal:3000/api/health')),
    ('HTTP webmail fixture', lambda: http('http://mail-01.dmz:8025/')),
    ('phishing administration UI', lambda: http('http://phishing.dmz:3333/')),
    ('badge-reader simulator', lambda: http('http://badge.internal/status')),
    ('32-bit teaching server', bof),
    ('packet analysis and password tools', lambda: cli('sh', '-c', 'command -v tshark john hydra hashcat gdb nmap')),
]
if '--activity-only' in sys.argv:
    checks = [('simulated user traffic', activity)]
elif '--activity' in sys.argv:
    checks.append(('simulated user traffic', activity))
for label, check in checks:
    for attempt in range(30):
        try:
            check()
            print('PASS:', label, flush=True)
            break
        except Exception:
            if attempt == 29: raise
            time.sleep(1)
