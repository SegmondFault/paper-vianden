#!/usr/bin/env python3
"""Offline timing exercise: estimate a cadence from exported synthetic DNS logs.

Uses observed sink timestamps only, not scenario offsets, seed or packet indexes.
An event-time Fourier periodogram avoids inventing exact, 'de-jittered' timestamps.
This is an exploratory teaching aid, not a production detector or significance test.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import statistics


def observed_times(lines, clock_speed=1, suffix=None):
    speed = float(clock_speed)
    if not math.isfinite(speed) or not 1 <= speed <= 3600:
        raise ValueError('Clock speed must be between 1 and 3600')
    times = []
    for line in lines:
        if not line.strip():
            continue
        event = json.loads(line)
        name = event.get('query', '').lower()
        if event.get('protocol') != 'dns' or not name:
            continue
        if suffix and not (name == suffix.lower().strip('.') or
                           name.endswith('.'+suffix.lower().strip('.'))):
            continue
        stamp = datetime.fromisoformat(event['time'])
        if stamp.tzinfo is None:
            raise ValueError('Observed timestamps must include a timezone')
        times.append(stamp.timestamp())
    times.sort()
    return [(stamp-times[0])*speed for stamp in times] if times else []


def fourier_power(times, period):
    """Normalized squared phase coherence, in [0,1]; 1 means perfectly periodic."""
    if not times or not math.isfinite(period) or period <= 0:
        raise ValueError('Need timestamps and a positive finite period')
    phase = [2*math.pi*(stamp-times[0])/period for stamp in times]
    return (sum(map(math.cos, phase))**2+sum(map(math.sin, phase))**2)/len(times)**2


def estimate_cadence(times):
    if len(times) < 12 or any(not math.isfinite(stamp) for stamp in times):
        raise ValueError('Need at least 12 finite observed timestamps')
    times = sorted(times)
    if times[-1] <= times[0]:
        raise ValueError('Need a nonzero observation span')
    # Broad, fixed teaching window: 5–20 minutes, not the ground-truth carrier.
    period = max(range(300, 1201), key=lambda candidate: fourier_power(times, candidate))
    gaps = [b-a for a, b in zip(times, times[1:])]
    return {'samples': len(times), 'period_seconds': period, 'period_minutes': round(period/60, 3),
            'phase_coherence': round(fourier_power(times, period), 4),
            'interval_cv': round(statistics.pstdev(gaps)/statistics.mean(gaps), 4),
            'search_seconds': [300, 1200], 'at_search_boundary': period in (300, 1200),
            'caution': 'Exploratory timing estimate, not a detection verdict; other indicators remain visible.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path, help='Exported scenario-sink.jsonl')
    parser.add_argument('--clock-speed', type=float, default=1,
                        help='Run multiplier, to convert observed seconds to simulated seconds')
    parser.add_argument('--suffix', help='Candidate DNS suffix to isolate; no preselected suspicious domain')
    args = parser.parse_args()
    try:
        with args.journal.open() as source:
            report = estimate_cadence(observed_times(source, args.clock_speed, args.suffix))
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
