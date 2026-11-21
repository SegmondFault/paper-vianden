"""Exercise ownership, central feed cursors, and safe evidence preservation."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from demo_control import Controller
from evidence import Feed, READ_FILES
from export_evidence import export


class DemoTests(unittest.TestCase):
    def controller(self,directory):
        return Controller(directory,Mock(return_value=False),Mock(),Mock(),Mock(return_value={'id':'saved'}),Mock(),Mock())

    def test_claim_is_exclusive_even_when_people_share_a_unix_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.controller(tmp)
            claim=c.execute(['claim','Alice'],1200,'human')
            with self.assertRaisesRegex(RuntimeError,'reserved'):
                c.execute(['claim','Bob'],1200,'human')
            status=c.execute(['status'],1200,'human')
            self.assertEqual(status['lease']['holder'],'Alice')
            self.assertNotIn('token_hash',status['lease'])
            self.assertNotIn(claim['token'],c.path.read_text())
            with self.assertRaises(RuntimeError): c.execute(['start','--token','wrong'],1200,'human')
            with self.assertRaises(RuntimeError): c.execute(['start','--token',claim['token']],1201,'other')
            c.start.assert_not_called()

    def test_reset_exports_before_stop_and_keeps_the_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.controller(tmp); claim=c.execute(['claim','Alice'],1200,'human')
            order=[]; c.running.return_value=True
            c.archive.side_effect=lambda:order.append('archive')
            c.stop.side_effect=lambda:order.append('stop')
            c.start.side_effect=lambda:order.append('start')
            c.execute(['reset','--token',claim['token'],'--seed','7','--clock-speed','60'],1200,'human')
            self.assertEqual(order,['archive','stop','start'])
            self.assertEqual(json.loads((Path(tmp)/'demo-run.json').read_text())['seed'],7)
            self.assertTrue(c.path.exists())

    def test_export_failure_prevents_deliberate_destruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.controller(tmp); claim=c.execute(['claim','Alice'],1200,'human')
            c.running.return_value=True; c.archive.side_effect=RuntimeError('disk full')
            with self.assertRaisesRegex(RuntimeError,'disk full'):
                c.execute(['release','--token',claim['token']],1200,'human')
            c.stop.assert_not_called(); self.assertTrue(c.path.exists())

    def test_expired_lease_cannot_control_a_new_run(self):
        with tempfile.TemporaryDirectory() as tmp, patch('demo_control.time.time',return_value=1000):
            c=self.controller(tmp); a=c.execute(['claim','Alice','--minutes','1'],1200,'human')
            with patch('demo_control.time.time',return_value=1061):
                with self.assertRaises(RuntimeError):c.execute(['start','--token',a['token']],1200,'human')
                b=c.execute(['claim','Bob'],1200,'human')
                with self.assertRaises(RuntimeError):c.execute(['stop','--token',a['token']],1200,'human')
                self.assertNotEqual(a['token'],b['token'])

    def test_cursor_pagination_and_gap_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed=Feed(tmp)
            for i in range(8): feed.append('host','auth',str(i))
            page=feed.page(limit=3); next_page=feed.page(page['cursor'],3)
            self.assertEqual([x['message'] for x in next_page['events']],['3','4','5'])
            self.assertFalse(page['gap']); self.assertTrue(page['more'])
            self.assertTrue(feed.page('old-run:5')['reset'])
            feed.events.popleft(); self.assertTrue(feed.page()['gap'])
            with self.assertRaises(ValueError):feed.page(limit=1001)
            with self.assertRaises(ValueError):feed.page(feed.epoch+':999999')

    def test_file_offsets_handle_append_rotation_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/'auth.log'; path.write_text('first\npartial')
            previous={}
            def read():
                script=READ_FILES.replace('PATTERNS',repr([str(root/'*.log')])).replace('PREVIOUS',repr(previous))
                return json.loads(subprocess.check_output([sys.executable,'-c',script]))
            first=read(); self.assertEqual(first[0]['lines'],['first'])
            previous[str(path)]={k:first[0][k] for k in ('inode','offset')}
            with path.open('a') as out:out.write('-completed\n')
            self.assertEqual(read()[0]['lines'],['partial-completed'])
            path.rename(root/'rotated'); path.write_text('new\n')
            (root/'link.log').symlink_to(root/'rotated')
            # ELOOP is an explicit collection error, never a followed symlink.
            (root/'link.log').unlink()
            self.assertEqual(read()[0]['lines'],['new'])

    def test_archive_preserves_findings_and_truth_without_following_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'finding.json').write_text('{"finding":"example"}')
            (root/'link').symlink_to('/etc/passwd')
            (root/'oversized').write_bytes(b'x'*1000)
            buffer=io.BytesIO(); result=export(buffer,{'findings':root},budget=100)
            self.assertIn('findings/finding.json',result['files'])
            self.assertIn('findings/link',result['omitted'])
            self.assertIn('findings/oversized',result['omitted'])
            buffer.seek(0)
            with tarfile.open(fileobj=buffer) as archive:
                self.assertEqual(set(archive.getnames()),{'findings/finding.json','manifest.json'})

    def test_sql_overlap_is_not_re_emitted_when_boundary_batches_change(self):
        a=json.dumps({'event_time':'2026-01-01 00:00:00.000000','thread':1,'argument':'SELECT 1'})
        b=json.dumps({'event_time':'2026-01-01 00:00:00.000000','thread':2,'argument':'SELECT 2'})
        with tempfile.TemporaryDirectory() as tmp, patch('evidence.cli',side_effect=[a,b,a]):
            feed=Feed(tmp)
            feed.sql();feed.sql();feed.sql()
            self.assertEqual(feed.sequence,2)


if __name__=='__main__':unittest.main()
