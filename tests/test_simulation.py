"""Offline tests: python3 -m unittest discover -s tests -v."""
from datetime import timedelta
import json
import logging
from pathlib import Path
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
import activity
import fixture_dns
import scenario
import scenario_runner as runner
import scenario_sink as sink


class SimulationTests(unittest.TestCase):
    def test_dns_accepts_standard_edns_cookie_queries(self):
        import struct
        wire=b''.join(bytes([len(x)])+x.encode() for x in 'portal.office.range.test'.split('.'))+b'\0'
        question=wire+struct.pack('!HH',1,1)
        cookie=struct.pack('!HH',10,8)+b'12345678'
        packet=struct.pack('!6H',123,0x0100,1,0,0,1)+question+b'\0'+struct.pack('!HHIH',41,1232,0,len(cookie))+cookie
        with patch.object(sink.socket,'gethostbyname',return_value='10.0.0.2'):
            name,reply=sink.dns_reply(packet)
        self.assertEqual(name,'portal.office.range.test')
        self.assertEqual(struct.unpack('!6H',reply[:12])[3:],(1,0,0))
        self.assertEqual(reply[12:12+len(question)],question)
        with self.assertRaises(ValueError):sink.dns_reply(packet[:-1])
    def test_speed_validation(self):
        for value in ('nan', 'inf', '-1', '0', '3601', 'oops'):
            with self.assertRaises(ValueError):
                scenario.clock_speed(value)
        self.assertEqual(scenario.clock_speed('60'), 60)

    def test_clock_is_monotonic_bounded_and_shared(self):
        with patch.object(scenario.time, 'monotonic', return_value=100):
            clock = scenario.Clock(60)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'clock.json'
            clock.publish(path)
            loaded = scenario.Clock.load(path)
            self.assertEqual(loaded.started, clock.started)
            self.assertEqual(loaded.speed, clock.speed)
        with patch.object(scenario.time, 'monotonic', return_value=160):
            self.assertEqual(clock.now, scenario.START+timedelta(hours=1))
        with patch.object(scenario.time, 'monotonic', return_value=100000):
            self.assertEqual(clock.elapsed, 86400)

    def test_workday(self):
        self.assertGreater(activity.office_profile(scenario.START+timedelta(hours=1.5))[0], .5)
        self.assertEqual(activity.office_profile(scenario.START+timedelta(hours=3.5))[0], 0)
        self.assertEqual(activity.office_profile(scenario.START+timedelta(hours=14))[0], 0)

    def test_employee_names_exist_in_compose(self):
        with patch.object(activity, 'lookup', return_value='10.0.0.1') as resolve:
            self.assertEqual(activity.address('files'), '10.0.0.1')
        resolve.assert_called_once_with('files')

    def test_story_is_bounded_sorted_and_dependency_ordered(self):
        self.assertEqual(len(scenario.EVENTS), 47)
        offsets = [event.offset for event in scenario.EVENTS]
        self.assertEqual(offsets, sorted(offsets))
        self.assertLess(max(offsets), scenario.DURATION)
        grants = set()
        for event in scenario.EVENTS:
            self.assertTrue(set(event.requires) <= grants, event.kind)
            if event.grant:
                grants.add(event.grant)
        self.assertIn('objective', grants)

    def test_dns_fixture_and_ack(self):
        for index in range(32):
            name, packet = scenario.dns_packet(index)
            self.assertTrue(name.endswith(scenario.SUFFIX))
            self.assertTrue(all(len(label) <= 63 for label in name.split('.')))
            parsed, reply = sink.dns_reply(packet)
            self.assertEqual(parsed, name)
            self.assertEqual(reply[:2], packet[:2])
            self.assertEqual(reply[3] & 15, 0)
        with self.assertRaises(ValueError):
            scenario.dns_packet(32)

    def test_reject_malformed_dns(self):
        for packet in (b'', b'\0'*17, struct.pack('!6H', 1, 0, 1, 0, 0, 0)+b'\xc0\x0cxxxx'):
            with self.assertRaises(ValueError):
                sink.dns_reply(packet)

    def test_office_dns_is_allowlisted_and_client_validates_answer(self):
        name = 'files.office.range.test'
        wire = b''.join(bytes([len(part)])+part.encode() for part in name.split('.'))+b'\0'
        packet = struct.pack('!6H', 0x1234, 0x100, 1, 0, 0, 0)+wire+struct.pack('!HH', 1, 1)
        with patch.object(sink.socket, 'gethostbyname', return_value='10.0.0.8') as resolve:
            parsed, reply = sink.dns_reply(packet)
        self.assertEqual(parsed, name)
        resolve.assert_called_once_with('file-01.internal')
        sock = MagicMock()
        sock.recv.return_value = reply
        context = MagicMock()
        context.__enter__.return_value = sock
        with patch.object(fixture_dns.socket, 'socket', return_value=context), \
             patch.object(fixture_dns.os, 'urandom', return_value=b'\x12\x34'):
            self.assertEqual(fixture_dns.lookup('files'), '10.0.0.8')
            sock.recv.return_value = reply[:-1]
            with self.assertRaises(RuntimeError):
                fixture_dns.lookup('files')
        with self.assertRaises(ValueError):
            fixture_dns.lookup('arbitrary-external-name')

    def test_foreign_dns_is_nxdomain(self):
        packet = struct.pack('!6H', 1, 0, 1, 0, 0, 0)+b'\x07example\x03com\0\0\x01\0\x01'
        with patch.object(sink.socket, 'gethostbyname') as resolve:
            _, reply = sink.dns_reply(packet)
            resolve.assert_not_called()
        self.assertEqual(reply[3] & 15, 3)

    def test_real_local_protocols_and_inert_markers(self):
        servers = [socketserver.UDPServer(('127.0.0.1', 0), sink.DNS),
                   socketserver.TCPServer(('127.0.0.1', 0), sink.SSH),
                   sink.ThreadingHTTPServer(('127.0.0.1', 0), sink.Java)]
        try:
            for server in servers:
                threading.Thread(target=server.serve_forever, daemon=True).start()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2)
                _, packet = scenario.dns_packet(0)
                sock.sendto(packet, servers[0].server_address)
                self.assertTrue(sock.recv(512)[2] & 0x80)
            with socket.create_connection(servers[1].server_address, timeout=2) as sock:
                self.assertIn(b'OpenSSH_7.2p2', sock.recv(128))
                sock.sendall(b'SSH-2.0-SyntheticTest\r\n')
            url = 'http://127.0.0.1:'+str(servers[2].server_port)
            with urllib.request.urlopen(url+'/status', timeout=2) as response:
                self.assertIn('Java/1.8.0_102', response.headers['X-Powered-By'])
                self.assertEqual(json.loads(response.read())['status'], 'ok')
            for marker in ('session', 'profile', 'status'):
                request = urllib.request.Request(url+'/api/'+marker, data=b'{}')
                with urllib.request.urlopen(request, timeout=2) as response:
                    state = json.loads(response.read())
                    self.assertEqual(state, {'ok': True})
            for path, body in (('/api/run-command', b'{}'), ('/api/session', b'bad')):
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(urllib.request.Request(url+path, data=body), timeout=2)
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()

    def test_story_blocks_after_failed_foothold(self):
        story = scenario.Story()
        with patch.object(story, 'act', side_effect=ConnectionError):
            result = story.perform(scenario.EVENTS[0], scenario.START)
        self.assertEqual(result['result'], 'error')
        with patch.object(story, 'act') as act:
            for event in scenario.EVENTS[2:]:
                result = story.perform(event, scenario.START)
                self.assertEqual(result['result'], 'blocked', event.kind)
            act.assert_not_called()
        self.assertNotIn('objective', story.grants)

    def test_one_failed_dns_chunk_prevents_completion(self):
        story = scenario.Story()
        def act(event):
            if event.kind == 'dns-exfil' and event.index == 8:
                raise TimeoutError
            return {'simulated': True}
        with patch.object(story, 'act', side_effect=act):
            for event in scenario.EVENTS:
                result = story.perform(event, scenario.START)
        self.assertEqual(result['result'], 'blocked')
        self.assertEqual(story.state['objective'], 'incomplete')
        self.assertEqual(story.counts['error'], 1)

    def test_accelerated_runner_finishes_once(self):
        class Finished(Exception):
            pass
        class FakeClock:
            speed = 3600
            elapsed = 0
            @property
            def now(self):
                return scenario.START+timedelta(seconds=self.elapsed)
        clock = FakeClock()
        completed_ticks = []
        def sleep(seconds):
            if clock.elapsed == 86400:
                completed_ticks.append(True)
                if len(completed_ticks) == 2:
                    raise Finished
            clock.elapsed = min(86400, clock.elapsed+seconds*clock.speed)
        story = scenario.Story()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(runner.time, 'sleep', side_effect=sleep), \
             patch.object(story, 'act', return_value={'simulated': True}) as act:
            path = Path(tmp)/'story-status.json'
            with self.assertRaises(Finished):
                runner.run(clock, story, logging.getLogger('test-null'), path)
            state = runner.check_status(path)
            self.assertEqual(state['state'], 'complete')
            self.assertEqual(state['objective'], 'complete')
            self.assertEqual(act.call_count, len(scenario.EVENTS))
            self.assertEqual(state['results']['error'], 0)

    def test_stage_verification_rejects_tampering_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/'synthetic'
            directory.mkdir()
            path = directory/'staged.jsonl'
            with patch.object(scenario, 'STAGE_DIR', str(directory)), \
                 patch.object(scenario, 'STAGE_FILE', str(path)):
                source = scenario.stage_verification()
            path.write_text(scenario.staged_data())
            subprocess.run([sys.executable, '-c', source], check=True)
            path.write_text('not the fixture')
            self.assertNotEqual(subprocess.run([sys.executable, '-c', source], stderr=subprocess.DEVNULL).returncode, 0)
            path.unlink()
            real = Path(tmp)/'other'
            real.write_text(scenario.staged_data())
            path.symlink_to(real)
            self.assertNotEqual(subprocess.run([sys.executable, '-c', source], stderr=subprocess.DEVNULL).returncode, 0)

    def test_employee_idle_and_complete_are_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'status.json'
            for mode in ('idle', 'active', 'complete'):
                path.write_text(json.dumps({'state': 'running', 'last_tick': activity.time.time(), 'mode': mode}))
                self.assertEqual(activity.check_status(path)['mode'], mode)
            path.write_text(json.dumps({'state': 'running', 'last_tick': 0, 'mode': 'idle'}))
            with self.assertRaises(RuntimeError):
                activity.check_status(path)


if __name__ == '__main__':
    unittest.main()
