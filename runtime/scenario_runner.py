#!/usr/bin/env python3
"""Independent DMZ actor following the employee scheduler's shared range clock."""
import argparse
from datetime import datetime, timezone
import json
import logging
import os
from logging.handlers import RotatingFileHandler
import signal
import sys
import time

from scenario import Clock, DURATION, STORY_DIR, Story, save_json

STATUS = STORY_DIR/'story-status.json'


def check_status(path=STATUS):
    state = json.loads(path.read_text())
    if state['state'] not in ('running','complete','external') or time.time()-state['last_tick'] > 90:
        raise RuntimeError('Story runner is not healthy')
    return state


def deadline(signum, frame):
    raise TimeoutError('Story action exceeded its real-time budget')


def run(clock, story, logger, status=STATUS):
    state = {'state': 'running', 'last_tick': time.time(), 'phase': 'waiting',
             'clock_speed': clock.speed, 'simulated': True}
    while True:
        elapsed = clock.elapsed
        # Four events maximum per tick; write a heartbeat after every action.
        # At high speeds late actions catch up; none are silently omitted.
        for _ in range(4):
            if story.index >= len(story.events) or elapsed < story.events[story.index].offset:
                break
            event = story.events[story.index]
            signal.alarm(25)
            try:
                result = story.perform(event, clock.now)
            finally:
                signal.alarm(0)
            logger.info(json.dumps(result))
            state.update(phase=event.phase, last_event=result['activity'])
            state.update(story.state, last_tick=time.time(), scenario_seconds=clock.elapsed,
                         scenario_time=clock.now.isoformat())
            save_json(status, state)
        done = clock.elapsed >= DURATION and story.index == len(story.events)
        if done and state['state'] != 'complete':
            logger.info(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                'scenario_time': clock.now.isoformat(), 'simulated': True,
                'activity': 'story-finished', **story.state}))
        state.update(story.state, state='complete' if done else 'running',
                     last_tick=time.time(), scenario_seconds=clock.elapsed,
                     scenario_time=clock.now.isoformat())
        save_json(status, state)
        time.sleep(15 if done else max(.05, min(2, 15/clock.speed)))


def external_status(clock):
    return {'state':'external','phase':'red-llm','last_tick':time.time(),
            'scenario_seconds':clock.elapsed,'scenario_time':clock.now.isoformat(),
            'clock_speed':clock.speed,'events_processed':0,'events_total':0,
            'objective':'unscored','results':{},'simulated':True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        state = check_status()
        print('Story runner healthy: '+state['phase']+'; objective '+state['objective'])
        return
    signal.signal(signal.SIGALRM, deadline)
    STORY_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('intrusion-story')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.addHandler(RotatingFileHandler(STORY_DIR/'story.jsonl', maxBytes=524288, backupCount=1))
    # The shared monotonic origin is valid across containers on the same kernel.
    for _ in range(120):
        try:
            clock = Clock.load()
            break
        except FileNotFoundError:
            time.sleep(.5)
    else:
        raise RuntimeError('Employee scheduler did not publish the scenario clock')
    if os.environ.get('PV_ATTACKER_MODE','scripted')=='llm':
        while True:
            save_json(STATUS,external_status(clock));time.sleep(2)
    else:run(clock, Story(clock.seed), logger)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
