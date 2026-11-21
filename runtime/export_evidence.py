#!/usr/bin/env python3
"""Stream a bounded evidence archive from white; never follow agent symlinks."""
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

ROOTS = {'observations':Path('/var/log/soc-evidence'),'employees':Path('/var/log/simulated-users'),
         'dns':Path('/var/log/dns'),'instructor':Path('/var/log/range-instructor'),
         'findings':Path('/var/lib/soc-ai')}


def export(stream, roots=ROOTS, budget=48*2**20):
    manifest={'created':time.time(),'files':[],'omitted':[]}
    examined=0
    with tarfile.open(fileobj=stream,mode='w|gz') as archive:
        for label,root in roots.items():
            if not root.is_dir(): continue
            for base,dirs,files in os.walk(root,followlinks=False):
                dirs[:]=sorted(x for x in dirs if not (Path(base)/x).is_symlink())[:64]
                for name in sorted(files)[:1000]:
                    examined+=1
                    if examined>2000:
                        manifest['omitted'].append('Archive entry limit reached')
                        dirs[:]=[]
                        break
                    path=Path(base)/name; relative=label+'/'+str(path.relative_to(root))
                    try:
                        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                        with os.fdopen(fd,'rb') as source:
                            info=os.fstat(source.fileno())
                            if not stat.S_ISREG(info.st_mode) or info.st_size>budget:
                                manifest['omitted'].append(relative); continue
                            data=source.read(info.st_size)
                        entry=tarfile.TarInfo(relative); entry.size=len(data); entry.mode=0o600
                        archive.addfile(entry,io.BytesIO(data)); budget-=len(data)
                        manifest['files'].append(relative)
                    except (OSError,ValueError): manifest['omitted'].append(relative)
                if examined>2000: break
            if examined>2000: break
        data=json.dumps(manifest,indent=2).encode()
        entry=tarfile.TarInfo('manifest.json'); entry.size=len(data); entry.mode=0o600
        archive.addfile(entry,io.BytesIO(data))
    return manifest


if __name__=='__main__': export(sys.stdout.buffer)
