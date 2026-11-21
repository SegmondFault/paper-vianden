"""Clear live exercise views before actors start; never touches saved exports."""
import argparse
from datetime import datetime,timezone
import glob
import json
import os
from pathlib import Path
import shutil
import stat
import uuid

VOLUMES=('activity-journal','story-journal','dns-evidence','soc-evidence','green-journal',
         'agent-findings','red-findings','green-findings','analyst-access','ids-evidence','firewall-evidence')
LOGS=('/var/log/auth.log','/var/log/nginx/*.log','/var/log/samba/*.log',
      '/var/log/api.log','/var/log/vsftpd.log','/var/log/mail.log','/var/log/health.log')
HISTORY=('.bash_history','.zsh_history','.python_history','.mysql_history','.lesshst')


def clear_directory(root,preserve_logs=False):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise RuntimeError('Unsafe live-evidence directory')
    count=0
    for path in root.iterdir():
        if preserve_logs and not path.is_symlink() and path.is_file() and path.suffix in ('.jsonl','.log'):
            # Sink loggers already hold these descriptors. Keep their inode so
            # new requests remain visible after clearing startup probes.
            if not truncate_regular(path):raise RuntimeError('Could not clear live journal')
        elif path.is_symlink() or not path.is_dir():path.unlink()
        else:shutil.rmtree(path)
        count+=1
    return count


def truncate_regular(path):
    try:fd=os.open(path,os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except OSError:return False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):return False
        os.ftruncate(fd,0);return True
    finally:os.close(fd)


def terminal_reset():
    for pattern in LOGS:
        for path in glob.glob(pattern):truncate_regular(path)
    homes=[Path('/root'),Path('/tmp')]+list(Path('/home').glob('*'))
    for home in homes:
        if home.is_symlink():continue
        for name in HISTORY+('.ssh/known_hosts','.ssh/known_hosts.old'):
            path=home/name
            if path.is_symlink() or path.is_file():path.unlink()
    print(json.dumps({'live_logs_cleared':True,'terminal_history_cleared':True}))


def volume_reset(base=Path('/evidence')):
    for name in VOLUMES:clear_directory(base/name,preserve_logs=name.endswith('journal') or name=='dns-evidence')
    marker={'fresh':True,'run_id':uuid.uuid4().hex,'time':datetime.now(timezone.utc).isoformat(),
            'roles':['blue','red','green','white']}
    (base/'soc-evidence/clean-start.json').write_text(json.dumps(marker)+'\n')
    print(json.dumps(marker))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--volumes',action='store_true')
    args=parser.parse_args()
    if args.volumes:volume_reset()
    else:terminal_reset()
