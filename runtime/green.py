#!/usr/bin/env python3
"""Ordinary business actions for an external green LLM; no admin key or truth."""
import argparse
from datetime import datetime,timezone
import json
from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path
import sys

sys.path.insert(0,'/opt/workflows')
from evidence import availability


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workflow',choices=('web','api','files','directory','report','ssh','mail','ftp','all'))
    args=parser.parse_args()
    result=availability(None if args.workflow=='all' else args.workflow)
    result.update(actor='green-llm',workflow=args.workflow,time=datetime.now(timezone.utc).isoformat())
    directory=Path('/var/log/green-users');directory.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('green-actions');logger.setLevel(logging.INFO)
    logger.addHandler(RotatingFileHandler(directory/'activity.jsonl',maxBytes=524288,backupCount=1))
    logger.info(json.dumps(result));print(json.dumps(result))
    raise SystemExit(0 if result['ok'] else 1)


if __name__=='__main__':main()
