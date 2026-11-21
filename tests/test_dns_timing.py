"""Timing-only tests; no network traffic or target data involved."""
from datetime import timedelta
import json
import math
from pathlib import Path
import statistics
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'runtime'))
sys.path.insert(0, str(ROOT/'tools'))
import scenario
from analyse_dns_timing import estimate_cadence, fourier_power, observed_times


class DNSTimingTests(unittest.TestCase):
    def test_schedule_is_seeded_ordered_and_bounded(self):
        self.assertEqual(scenario.exfil_offsets(), scenario.exfil_offsets())
        self.assertNotEqual(scenario.exfil_offsets(1), scenario.exfil_offsets(2))
        for seed in range(50):
            offsets = scenario.exfil_offsets(seed)
            self.assertEqual(len(offsets), 32)
            self.assertEqual(tuple(sorted(set(offsets))), offsets)
            self.assertGreaterEqual(offsets[0], 16*3600)
            self.assertLess(offsets[-1], 22*3600)
            anchor = 16*3600+scenario.EXFIL_JITTER_LIMIT*scenario.EXFIL_PERIOD
            for index, offset in enumerate(offsets):
                self.assertLessEqual(abs(offset-(anchor+index*scenario.EXFIL_PERIOD)),
                    scenario.EXFIL_JITTER_LIMIT*scenario.EXFIL_PERIOD+.5)
        scheduled = [event.offset for event in scenario.EVENTS if event.kind == 'dns-exfil']
        self.assertEqual(scheduled, list(scenario.exfil_offsets()))

    def test_intervals_are_not_clockwork(self):
        offsets = scenario.exfil_offsets()
        gaps = [b-a for a, b in zip(offsets, offsets[1:])]
        self.assertGreater(len(set(gaps)), 25)
        self.assertGreater(statistics.pstdev(gaps)/statistics.mean(gaps), .15)
        self.assertLess(min(gaps), .8*scenario.EXFIL_PERIOD)
        self.assertGreater(max(gaps), 1.2*scenario.EXFIL_PERIOD)

    def test_carrier_recovered_without_ground_truth_dejittering(self):
        offsets = scenario.exfil_offsets()
        estimate = estimate_cadence(offsets)
        self.assertLess(abs(estimate['period_seconds']-scenario.EXFIL_PERIOD), 15)
        self.assertGreater(estimate['phase_coherence'], .15)
        self.assertLess(estimate['phase_coherence'], .5)
        regular = [index*scenario.EXFIL_PERIOD for index in range(32)]
        self.assertAlmostEqual(fourier_power(regular, scenario.EXFIL_PERIOD), 1)
        self.assertLess(fourier_power(offsets, scenario.EXFIL_PERIOD), .6)

    def test_carrier_recovery_across_seed_variants(self):
        # Regression: old seed 42 had a stronger unrelated peak near 309 s.
        for seed in range(100):
            offsets = scenario.exfil_offsets(seed)
            estimate = estimate_cadence(offsets)
            self.assertLess(abs(estimate['period_seconds']-scenario.EXFIL_PERIOD), 15, seed)
            self.assertGreater(fourier_power(offsets, scenario.EXFIL_PERIOD), .25, seed)
        for seed in (42, 43, 20260112, 2**32-1):
            self.assertEqual(scenario.exfil_offsets(seed), scenario.exfil_offsets(seed))

    def test_analysis_uses_observed_timestamps_and_clock_scale_only(self):
        for speed in (1, 10, 60):
            # No scheduled_seconds, indexes, seed or other timing ground truth.
            events = [{'protocol': 'dns', 'query': 'fixture.telemetry.range.test',
                'time': (scenario.START+timedelta(seconds=offset/speed)).isoformat()}
                for offset in reversed(scenario.exfil_offsets())]
            events += [{'protocol': 'http', 'time': scenario.START.isoformat()},
                       {'protocol': 'dns', 'query': 'portal.office.range.test',
                        'time': scenario.START.isoformat()}]
            samples = observed_times(['', *map(json.dumps, events)], speed, 'telemetry.range.test')
            estimate = estimate_cadence(samples)
            self.assertEqual(estimate['samples'], 32)
            self.assertLess(abs(estimate['period_seconds']-scenario.EXFIL_PERIOD), 15)

    def test_variant_seed_changes_timeline_without_changing_story(self):
        a = scenario.build_events(42)
        b = scenario.build_events(43)
        self.assertEqual(a, scenario.build_events(42))
        self.assertNotEqual([event.offset for event in a], [event.offset for event in b])
        self.assertEqual([(event.kind, event.requires, event.grant) for event in a],
                         [(event.kind, event.requires, event.grant) for event in b])
        for seed in (0, 42, 43, 2**32-1):
            grants = set()
            events = scenario.build_events(seed)
            self.assertEqual(len(events), 47)
            for event in events:
                self.assertTrue(set(event.requires) <= grants)
                if event.grant:
                    grants.add(event.grant)
            self.assertLess(events[-1].offset, scenario.DURATION)

    def test_rng_streams_are_reproducible_and_independent(self):
        a = scenario.rng_for(42, 'employee.workflows')
        b = scenario.rng_for(42, 'employee.workflows')
        self.assertEqual([a.random() for _ in range(20)], [b.random() for _ in range(20)])
        expected = scenario.exfil_offsets(42)
        for _ in range(200):
            a.random()
        self.assertEqual(scenario.exfil_offsets(42), expected)
        pauses = scenario.rng_for(42, 'employee.pauses')
        workflows = scenario.rng_for(42, 'employee.workflows')
        self.assertNotEqual([pauses.random() for _ in range(4)], [workflows.random() for _ in range(4)])

    def test_intensity_modulation_is_light_smooth_and_seeded(self):
        for elapsed in range(0, 86401, 60):
            value = scenario.office_modulation(42, elapsed)
            self.assertGreaterEqual(value, .85)
            self.assertLessEqual(value, 1.15)
            self.assertEqual(value, scenario.office_modulation(42, elapsed))
        self.assertNotEqual(scenario.office_modulation(42, 1800), scenario.office_modulation(43, 1800))
        self.assertAlmostEqual(scenario.office_modulation(42, 1800-1e-4),
                               scenario.office_modulation(42, 1800+1e-4), places=9)

    def test_seed_validation_and_shared_clock(self):
        for value in (-1, 2**32, 'x', '1.5', 1.5):
            with self.assertRaises(ValueError):
                scenario.simulation_seed(value)
        clock = scenario.Clock(60, started=100, seed=42)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'clock.json'
            clock.publish(path)
            self.assertEqual(scenario.Clock.load(path).seed, 42)

    def test_bad_and_short_observations_are_not_verdicts(self):
        for samples in ([], [1]*32, list(range(11)), [math.nan]*32, [math.inf]*32):
            with self.assertRaises(ValueError):
                estimate_cadence(samples)
        with self.assertRaises(ValueError):
            observed_times([json.dumps({'protocol': 'dns', 'query': 'x.telemetry.range.test',
                                       'time': '2026-01-12T08:00:00'})])
        for speed in (0, -1, math.nan, math.inf, 3601):
            with self.assertRaises(ValueError):
                observed_times([], speed)


if __name__ == '__main__':
    unittest.main()
