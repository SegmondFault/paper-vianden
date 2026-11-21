"""Human-only ownership of one shared exercise, independent of SSH sessions."""
import argparse
import contextlib
import fcntl
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import time


def atomic_json(path, data):
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(data)+'\n')
    pending.chmod(0o600)
    pending.replace(path)


class Controller:
    def __init__(self, directory, running, start, stop, archive, archives, download, maximum=1560):
        self.directory = Path(directory)
        self.running, self.start, self.stop = running, start, stop
        self.archive, self.archives, self.download = archive, archives, download
        self.maximum = maximum

    @property
    def path(self):
        return self.directory/'demo-lease.json'

    def lease(self):
        try:
            return json.loads(self.path.read_text())
        except FileNotFoundError:
            return {}

    def authorize(self, token, uid):
        lease = self.lease()
        digest = hashlib.sha256((token or '').encode()).hexdigest()
        if lease.get('uid') != uid or lease.get('expires', 0) <= time.time() or not hmac.compare_digest(
                lease.get('token_hash', ''), digest):
            raise RuntimeError('A valid human demo lease/token is required; use range status or range claim.')
        return lease

    def execute(self, argv, uid, username):
        parser = argparse.ArgumentParser(prog='range')
        subs = parser.add_subparsers(dest='action', required=True)
        subs.add_parser('status')
        subs.add_parser('archives')
        get = subs.add_parser('download'); get.add_argument('archive_id')
        claim = subs.add_parser('claim')
        claim.add_argument('name'); claim.add_argument('--minutes', type=int, default=min(120, self.maximum))
        for action in ('start', 'reset', 'stop', 'release', 'export'):
            p = subs.add_parser(action); p.add_argument('--token', required=True)
            if action in ('start', 'reset'):
                p.add_argument('--seed', type=int, default=42)
                p.add_argument('--clock-speed', type=float, default=60)
        args = parser.parse_args(argv)
        self.directory.mkdir(mode=0o700, exist_ok=True)
        with (self.directory/'demo-control.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            lease = self.lease()
            if args.action == 'status':
                return {'running': self.running(), 'lease': {k: v for k, v in lease.items() if k != 'token_hash'},
                        'lease_active': lease.get('expires', 0) > time.time()}
            if args.action == 'archives':
                return self.archives()
            if args.action == 'download':
                return self.download(args.archive_id)
            if args.action == 'claim':
                if not 1 <= args.minutes <= self.maximum or not 1 <= len(args.name) <= 80 or not args.name.isprintable():
                    raise RuntimeError('Use a printable name and a bounded lease duration.')
                if lease.get('expires', 0) > time.time() or self.running():
                    raise RuntimeError('The exercise is reserved or still stopping; use range status.')
                token = secrets.token_hex(32)
                lease = {'uid': uid, 'account': username, 'holder': args.name, 'expires': time.time()+60*args.minutes,
                         'token_hash': hashlib.sha256(token.encode()).hexdigest()}
                atomic_json(self.path, lease)
                return {'token': token, 'holder': args.name, 'expires': lease['expires']}
            lease = self.authorize(args.token, uid)
            if args.action in ('start', 'reset'):
                if not 0 <= args.seed <= 2**32-1 or not 1 <= args.clock_speed <= 3600:
                    raise RuntimeError('Seed or clock speed is out of bounds.')
                if self.running():
                    if args.action != 'reset':
                        raise RuntimeError('A run already exists; agents join it. Use reset deliberately.')
                    self.archive()  # Preserve evidence before a deliberate reset.
                    self.stop()
                if lease['expires'] <= time.time()+30:
                    raise RuntimeError('Lease is nearly expired; release it and claim a new slot.')
                atomic_json(self.directory/'demo-run.json', {'seed': args.seed, 'clock_speed': args.clock_speed})
                self.start()
                return {'state': 'starting', 'seed': args.seed, 'clock_speed': args.clock_speed}
            if args.action == 'export':
                return self.archive()
            if self.running():
                self.archive()
                self.stop()
            if args.action == 'release':
                self.path.unlink(missing_ok=True)
                (self.directory/'demo-run.json').unlink(missing_ok=True)
            return {'state': 'stopped', 'released': args.action == 'release'}


@contextlib.contextmanager
def session_slot(directory, uid, limit=16):
    """Bound concurrent tools without using an SSH login as an exercise lock."""
    directory = Path(directory); directory.mkdir(mode=0o700, exist_ok=True)
    for slot in range(limit):
        stream = (directory/f'portal-{uid}-{slot}.lock').open('a')
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            stream.close()
            continue
        try:
            yield
        finally:
            stream.close()
        return
    raise RuntimeError('Workstation concurrency limit reached; retry when a tool call finishes.')
