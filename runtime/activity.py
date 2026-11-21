#!/usr/bin/env python3
"""Small, explicitly synthetic users making real requests inside the range."""
import argparse
from datetime import datetime, timezone
from email.message import EmailMessage
import ftplib
import imaplib
import json
import logging
import math
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import smtplib
import subprocess
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo
from fixture_dns import lookup
from scenario import Clock, DEFAULT_SEED, DURATION, office_modulation, rng_for

LOG_DIR = Path('/var/log/simulated-users')
STATUS = LOG_DIR/'status.json'
KINDS = ('web', 'api', 'files', 'directory', 'report', 'ssh', 'mail', 'ftp')
ZONE = ZoneInfo('Europe/Luxembourg')


def office_profile(now):
    """A small office-hours approximation, not a fitted human behaviour model."""
    local = now.astimezone(ZONE)
    hour = local.hour+local.minute/60+local.second/3600
    if local.weekday() >= 5 or not 9 <= hour < 18:
        return 0.0, 'outside office hours'
    if 12 <= hour < 13:
        return 0.0, 'lunch'
    def ramp(value):
        value = max(0.0, min(1.0, value))
        return value*value*(3-2*value)
    peaks = max(math.exp(-.5*((hour-10.5)/.65)**2),
                math.exp(-.5*((hour-16)/.8)**2))
    lunch = ramp((12-hour)/.25) if hour < 12 else ramp((hour-13)/.35)
    return ramp((hour-9)/.75)*ramp((18-hour)/.75)*lunch*(.15+.85*peaks), 'office hours'


def address(name):
    return lookup(name)


def command(args, **kwargs):
    return subprocess.check_output(args, timeout=8, stderr=subprocess.PIPE, **kwargs)


def http(url, actor):
    request = urllib.request.Request(url, headers={'User-Agent': 'SimulatedEmployee/'+actor})
    with urllib.request.urlopen(request, timeout=5) as response:
        response.read(8192)


def files(actor):
    Path('/tmp/samba').mkdir(exist_ok=True)
    command(['smbclient', '--configfile=/dev/null',
             '--option=lock directory=/tmp/samba', '--option=cache directory=/tmp/samba',
             '--option=state directory=/tmp/samba', '--option=private dir=/tmp/samba',
             '//'+address('files')+'/public', '-N', '-c', 'get welcome.txt /dev/null'])


def directory(actor):
    command(['ldapsearch', '-x', '-H', 'ldap://'+address('directory'), '-b', 'dc=enum,dc=lab',
             '(uid=jdoe)', 'dn', 'mail'])


def report(actor):
    command(['mariadb', '--skip-ssl', '--connect-timeout=5', '-h', address('database'),
             '-u', 'app_user', '--batch', '-N', '-e',
             '/* simulated employee report */ SELECT id,name FROM acme_corp.customers ORDER BY id LIMIT 3'],
            env=dict(os.environ, MYSQL_PWD='S3cretDB!2024'))


def ssh(actor):
    # Already supplied by the toolbox's pwntools dependency. No admin key/agent.
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(address('gateway'), username='devuser', password='devuser2024',
                       look_for_keys=False, allow_agent=False, timeout=5,
                       auth_timeout=5, banner_timeout=5)
        _, stdout, _ = client.exec_command('id -un', timeout=5)
        if stdout.read(128).strip() != b'devuser':
            raise RuntimeError('Unexpected SSH response')
    finally:
        client.close()


def mail(actor):
    message = EmailMessage()
    message['From'] = actor+'@range.test'
    message['To'] = 'helpdesk@range.test'
    message['Subject'] = 'Synthetic routine status update'
    message.set_content('Simulated employee activity. No external delivery.')
    with smtplib.SMTP(address('smtp'), 1025, timeout=5) as smtp:
        smtp.send_message(message)
    with imaplib.IMAP4(address('mail'), 143, timeout=5) as inbox:
        inbox.login('sysadmin', 'admin123')
        if inbox.select('INBOX', readonly=True)[0] != 'OK':
            raise RuntimeError('Mailbox unavailable')
        inbox.search(None, 'ALL')


def ftp(actor):
    with ftplib.FTP(address('ftp'), timeout=5) as connection:
        connection.login()
        connection.nlst('pub')


ACTIONS = (
    ('web', 'employee-01', 'web-01.dmz',
     lambda actor: http('http://'+address('portal')+'/?employee='+actor, actor)),
    ('api', 'employee-02', 'app-01.internal',
     lambda actor: http('http://'+address('api')+':3000/api/users/2?employee='+actor, actor)),
    ('files', 'employee-01', 'file-01.internal', files),
    ('directory', 'employee-02', 'ldap.internal', directory),
    ('report', 'reporting-service', 'db-01.internal', report),
    ('ssh', 'operations-service', 'vpn-gw-01.internal', ssh),
    ('mail', 'employee-01', 'mail-sink.dmz,mail.internal', mail),
    ('ftp', 'employee-02', 'ftp.dmz', ftp),
)
WORKFLOWS = (('web', 'files'), ('mail', 'web'), ('directory', 'api', 'ftp'),
             ('report',), ('ssh',))


def check_status(path=STATUS):
    state = json.loads(path.read_text())
    if state.get('state') != 'running' or time.time()-state['last_tick'] > 90:
        raise RuntimeError('Simulated users are not running')
    if state.get('mode') not in ('active', 'idle', 'complete'):
        raise RuntimeError('Unknown activity schedule state')
    return state


def save_status(state):
    pending = STATUS.with_suffix('.tmp')
    pending.write_text(json.dumps(state)+'\n')
    pending.replace(STATUS)


def deadline(signum, frame):
    raise TimeoutError('Activity exceeded its time budget')


def perform(kind, validation=False):
    _, actor, target, action = next(item for item in ACTIONS if item[0] == kind)
    started = time.monotonic()
    event = {'time': datetime.now(timezone.utc).isoformat(), 'simulated': True,
             'actor': actor, 'activity': kind, 'target': target}
    if validation:
        event['validation'] = True
    signal.alarm(12)
    try:
        action(actor)
        event['result'] = 'ok'
    except Exception as error:
        event.update(result='error', error=type(error).__name__, detail=str(error)[:256])
    finally:
        signal.alarm(0)
    event['duration_ms'] = round((time.monotonic()-started)*1000)
    return event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--once', choices=KINDS+('all',), help='Explicit diagnostic requests, outside the user schedule')
    args = parser.parse_args()
    if args.check:
        state = check_status()
        print('Simulated users scheduler is healthy: '+state['mode']+' ('+state['reason']+').')
        return
    signal.signal(signal.SIGALRM, deadline)
    if args.once:
        events = [perform(kind, validation=True) for kind in (KINDS if args.once == 'all' else (args.once,))]
        for event in events:
            print(json.dumps(event), flush=True)
        raise SystemExit(0 if all(e['result'] == 'ok' for e in events) else 1)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('simulated-users')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.addHandler(RotatingFileHandler(LOG_DIR/'activity.jsonl', maxBytes=524288, backupCount=1))
    state = {'state': 'running', 'last_tick': time.time(), 'successes': {}, 'failures': {},
             'timezone': str(ZONE), 'mode': 'idle', 'reason': 'starting'}
    clock = Clock(os.environ.get('PV_CLOCK_SPEED', '1'), seed=os.environ.get('PV_SEED', str(DEFAULT_SEED)))
    workflows = rng_for(clock.seed, 'employee.workflows')
    pauses = rng_for(clock.seed, 'employee.pauses')
    clock.publish()
    previous_mode = None
    pending = []
    due = 0.0
    while True:
        now = clock.now
        elapsed = clock.elapsed
        complete = elapsed >= DURATION
        intensity, reason = (0, '24-hour scenario complete') if complete else office_profile(now)
        intensity = min(1, intensity*office_modulation(clock.seed, elapsed))
        state.update(scenario_seconds=round(elapsed, 2), clock_speed=clock.speed,
                     scenario_time=now.isoformat(),
                     last_tick=time.time(), mode='complete' if complete else 'active' if intensity > 0 else 'idle',
                     reason=reason, intensity=round(intensity, 4), local_time=now.astimezone(ZONE).isoformat())
        save_status(state)
        current_mode = (state['mode'], reason)
        if current_mode != previous_mode:
            logger.info(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                    'scenario_time': now.isoformat(), 'simulated': True,
                                    'activity': 'schedule', 'mode': state['mode'], 'reason': reason}))
            previous_mode = current_mode
        if not intensity:
            pending = []
            due = 0.0
            time.sleep(15 if complete else max(.25, min(15, 15/clock.speed)))
            continue
        if time.monotonic() < due:
            time.sleep(min(15, due-time.monotonic()))
            continue
        if not pending:
            pending = list(workflows.choices(WORKFLOWS, weights=(4, 3, 4, 1, 1))[0])
        event = perform(pending.pop(0))
        event['scenario_time'] = clock.now.isoformat()
        counters = state['successes' if event['result'] == 'ok' else 'failures']
        counters[event['activity']] = counters.get(event['activity'], 0)+1
        logger.info(json.dumps(event))
        state['last_tick'] = time.time()
        save_status(state)
        pause = min(15, max(1, pauses.lognormvariate(math.log(4), .6))) if pending else \
            min(600, max(5, pauses.lognormvariate(math.log(45/intensity)-.8**2/2, .8)))
        due = time.monotonic()+max(.25, pause/clock.speed)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, KeyError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
