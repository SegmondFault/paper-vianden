#!/usr/bin/env python3
"""Central, observable evidence feed. Never reads instructor truth or story code."""
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shlex
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import uuid

DIRECTORY = Path('/var/log/soc-evidence')
URL = 'http://telemetry.management:8088'
SOURCES = {
    'vpn-gw-01.internal': ['/var/log/auth.log'],
    'file-01.internal': ['/var/log/auth.log', '/var/log/samba/*.log'],
    'web-01.dmz': ['/var/log/auth.log', '/var/log/nginx/access.log', '/var/log/nginx/error.log'],
    'app-01.internal': ['/var/log/auth.log', '/var/log/api.log'],
    'ftp.dmz': ['/var/log/auth.log', '/var/log/vsftpd.log'],
    'mail.internal': ['/var/log/auth.log', '/var/log/mail.log'],
}
LOCAL = {'dns': Path('/var/log/dns/queries.jsonl'),
         'employees':Path('/var/log/simulated-users/activity.jsonl'),
         'green':Path('/var/log/green-users/activity.jsonl')}

# Fixed file roots, bounded reads, no pipes/device files/symlink traversal.
READ_FILES = '''import glob,json,os,stat
patterns=PATTERNS
previous=PREVIOUS
result=[]
for pattern in patterns:
 for name in sorted(glob.glob(pattern))[:32]:
  try:
   fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   with os.fdopen(fd,'rb') as f:
    info=os.fstat(f.fileno())
    if not stat.S_ISREG(info.st_mode):continue
    old=previous.get(name,{})
    offset=old.get('offset',0) if old.get('inode')==info.st_ino and old.get('offset',0)<=info.st_size else 0
    skipped=max(0,info.st_size-offset-65536)
    if skipped:offset+=skipped
    f.seek(offset);data=f.read(65536)
    end=data.rfind(b'\\n')+1
    if end:data=data[:end]
    elif len(data)<65536:data=b''
    result.append({'path':name,'inode':info.st_ino,'offset':offset+len(data),
                   'skipped_bytes':skipped,'lines':data.decode(errors='replace').splitlines()})
  except FileNotFoundError:pass
print(json.dumps(result))'''


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def cli(argv, **kwargs):
    return subprocess.check_output(argv, timeout=10, stderr=subprocess.PIPE, text=True, **kwargs)


class Feed:
    def __init__(self, directory=DIRECTORY):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.epoch = uuid.uuid4().hex
        self.sequence = 0
        self.events = deque(maxlen=5000)
        self.offsets = {}
        self.sql_seen = {}
        self.sql_since=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
        self.lock = threading.RLock()
        self.poll_lock = threading.Lock()
        self.last_poll = 0
        self.errors = {}
        self.logger = logging.getLogger('evidence-'+self.epoch)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(RotatingFileHandler(self.directory/'events.jsonl', maxBytes=4*2**20, backupCount=2))

    def append(self, host, source, message, original=None):
        with self.lock:
            self.sequence += 1
            event = {'id': self.epoch+':'+str(self.sequence), 'sequence': self.sequence,
                     'observed_at': timestamp(), 'host': host, 'source': source,
                     'message': str(message)[:8192]}
            if isinstance(original, dict):
                event['fields'] = original if len(json.dumps(original))<=8192 else {'truncated':True}
                event['timestamp'] = original.get('time', original.get('event_time'))
            self.events.append(event)
            self.logger.info(json.dumps(event, ensure_ascii=True))
            return event

    def page(self, after='', limit=200):
        if not 1 <= limit <= 1000:
            raise ValueError('limit must be 1..1000')
        epoch, sequence = after.rsplit(':', 1) if after else (self.epoch, '0')
        sequence = int(sequence)
        with self.lock:
            reset = epoch != self.epoch
            if reset: sequence = 0
            if sequence<0 or sequence>self.sequence:raise ValueError('Cursor outside this run')
            rows = [x for x in self.events if x['sequence'] > sequence][:limit]
            first = self.events[0]['sequence'] if self.events else 1
            return {'events': rows, 'cursor': rows[-1]['id'] if rows else self.epoch+':'+str(max(sequence,self.sequence)),
                    'reset': reset, 'gap': sequence < first-1, 'more': bool(rows and rows[-1]['sequence'] < self.sequence)}

    def status(self):
        with self.lock:
            return {'epoch': self.epoch, 'events': self.sequence, 'retained': len(self.events),
                    'last_poll': self.last_poll, 'errors': self.errors.copy(),
                    'sources': sorted(SOURCES)+['db-01.internal', 'dns', 'employees']}

    def records(self, host, records):
        previous = self.offsets.setdefault(host, {})
        for record in records:
            if record.get('skipped_bytes'):
                self.append(host, record['path'], 'Collector skipped older bytes', {'skipped_bytes': record['skipped_bytes']})
            for line in record['lines']:
                try: original = json.loads(line)
                except (ValueError, TypeError): original = None
                self.append(host, record['path'], line, original)
            previous[record['path']] = {k: record[k] for k in ('inode', 'offset')}

    def remote(self, host):
        source = READ_FILES.replace('PATTERNS', repr(SOURCES[host])).replace('PREVIOUS', repr(self.offsets.get(host, {})))
        output = cli(['ssh','-o','BatchMode=yes','-o','UserKnownHostsFile=/tmp/known_hosts',
                      '-o','ConnectTimeout=3',host,'python3 -c '+shlex.quote(source)])
        return host, json.loads(output)

    def sql(self):
        # JSON_OBJECT preserves tabs/newlines. Our own collector query is excluded.
        query = ("/* pv-evidence */ SELECT JSON_OBJECT('event_time',DATE_FORMAT(event_time,'%Y-%m-%d %H:%i:%s.%f'),"
                 "'user_host',user_host,'command',command_type,'argument',LEFT(argument,8192),'thread',thread_id) "
                 "FROM mysql.general_log WHERE event_time >= '"+self.sql_since+"' AND command_type='Query' "
                 "AND argument NOT LIKE '%pv-evidence%' ORDER BY event_time,thread_id,argument LIMIT 500")
        output = cli(['mariadb','--skip-auto-rehash','--skip-ssl','--connect-timeout=3','-h','db-01.internal','-u','root','--batch','--raw','-N','-e',query],
                     env=dict(os.environ, MYSQL_PWD='S3cretDB!2024'))
        for line in output.splitlines():
            row = json.loads(line); ident = hashlib.sha256(line.encode()).hexdigest()
            if ident not in self.sql_seen:
                self.append('db-01.internal','mysql.general_log',row['argument'],row)
                self.sql_seen[ident]=None
                if len(self.sql_seen)>20000:self.sql_seen.pop(next(iter(self.sql_seen)))
            self.sql_since = max(self.sql_since, row['event_time'])

    def collect(self):
        with self.poll_lock:
            errors = {}
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = {host: pool.submit(self.remote, host) for host in SOURCES}
                for host, future in futures.items():
                    try:
                        _, records = future.result(); self.records(host, records)
                    except Exception as error: errors[host] = type(error).__name__
            for source, path in LOCAL.items():
                try:
                    script = READ_FILES.replace('PATTERNS', repr([str(path)])).replace('PREVIOUS', repr(self.offsets.get(source, {})))
                    self.records(source, json.loads(cli(['python3','-c',script])))
                except Exception as error: errors[source] = type(error).__name__
            try: self.sql()
            except Exception as error: errors['db-01.internal'] = type(error).__name__
            with self.lock:
                self.errors = errors; self.last_poll = time.time()
                pending = self.directory/'status.tmp'
                pending.write_text(json.dumps(self.status())+'\n'); pending.replace(self.directory/'status.json')
            return self.status()


def availability(only=None):
    """Real ordinary-work probes; no instructor journal or scenario imports."""
    import ftplib, imaplib, smtplib
    def web(): urllib.request.urlopen('http://web-01.dmz/', timeout=4).read(4096)
    def api(): urllib.request.urlopen('http://app-01.internal:3000/api/health', timeout=4).read(4096)
    def files(): cli(['smbclient','//file-01.internal/public','-N','-c','get welcome.txt /dev/null'])
    def directory(): cli(['ldapsearch','-x','-H','ldap://ldap.internal','-b','dc=enum,dc=lab','(uid=jdoe)','dn'])
    def report(): cli(['mariadb','--skip-ssl','--connect-timeout=3','-h','db-01.internal','-u','app_user','-N','-e',
                       '/* ordinary availability */ SELECT id,name FROM acme_corp.customers LIMIT 3'],env=dict(os.environ,MYSQL_PWD='S3cretDB!2024'))
    def ssh():
        import paramiko
        client=paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect('vpn-gw-01.internal',username='devuser',password='devuser2024',allow_agent=False,look_for_keys=False,timeout=4,auth_timeout=4,banner_timeout=4)
            _,out,_=client.exec_command('id -un',timeout=4)
            assert out.read(128).strip()==b'devuser'
        finally: client.close()
    def mail():
        with smtplib.SMTP('mail-sink.dmz',1025,timeout=4) as smtp:
            smtp.sendmail('availability@range.test',['helpdesk@range.test'],'Subject: Availability\r\n\r\nSynthetic test.\r\n')
        with imaplib.IMAP4('mail.internal',143,timeout=4) as inbox:
            inbox.login('sysadmin','admin123'); assert inbox.select('INBOX',readonly=True)[0]=='OK'
    def ftp():
        with ftplib.FTP('ftp.dmz',timeout=4) as client: client.login(); assert client.nlst()
    result={}
    for name,action in (('web',web),('api',api),('files',files),('directory',directory),('report',report),('ssh',ssh),('mail',mail),('ftp',ftp)):
        if only is not None and name!=only:continue
        try: action(); result[name]={'ok':True}
        except Exception as error: result[name]={'ok':False,'error':type(error).__name__}
    return {'time':timestamp(),'checks':result,'ok':all(x['ok'] for x in result.values())}


def handler(feed):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            try:
                url=urllib.parse.urlsplit(self.path); query=urllib.parse.parse_qs(url.query)
                if url.path=='/events': data=feed.page(query.get('after',[''])[0],int(query.get('limit',['200'])[0]))
                elif url.path=='/status': data=feed.status()
                elif url.path=='/availability': data=availability()
                else: self.send_error(404); return
                self.reply(data)
            except (ValueError, IndexError): self.send_error(400)
        def do_POST(self):
            if self.path!='/flush': self.send_error(404); return
            self.reply(feed.collect())
        def reply(self,data):
            body=json.dumps(data).encode(); self.send_response(200)
            self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers()
            self.wfile.write(body)
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('serve','status','tail','availability','flush'))
    parser.add_argument('--after',default=''); parser.add_argument('--limit',type=int,default=200)
    parser.add_argument('--follow',action='store_true'); args=parser.parse_args()
    if args.command=='serve':
        feed=Feed(); server=ThreadingHTTPServer(('0.0.0.0',8088),handler(feed)); server.daemon_threads=True
        threading.Thread(target=server.serve_forever,daemon=True).start()
        while True:
            feed.collect(); time.sleep(2)
    else:
        cursor=args.after
        while True:
            path='/events?'+urllib.parse.urlencode({'after':cursor,'limit':args.limit}) if args.command=='tail' else '/'+args.command
            request=urllib.request.Request(URL+path,method='POST' if args.command=='flush' else 'GET')
            with urllib.request.urlopen(request,timeout=90) as response: data=json.load(response)
            print(json.dumps(data),flush=True)
            if not args.follow: break
            cursor=data['cursor']; time.sleep(1)


if __name__=='__main__': main()
