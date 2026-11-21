"""Role-bound portal command/configuration tests (no host changes)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'runtime'))
import pv
import white
from tools import install_portals


class PortalTests(unittest.TestCase):
    def test_roles_are_bound_to_both_uid_and_account(self):
        config = {'accounts': {'agent': {'uid': 1200, 'role': 'blue'},
                               'observer': {'uid': 1201, 'role': 'white'}}}
        self.assertEqual(pv.portal_role(config, 1200, 'agent'), 'blue')
        self.assertEqual(pv.portal_role(config, 1201, 'observer'), 'white')
        for uid, account in ((1201, 'agent'), (1200, 'observer'), (0, 'root'), (1200, 'missing')):
            with self.assertRaises(RuntimeError):
                pv.portal_role(config, uid, account)
        config['accounts']['agent']['role'] = 'control'
        with self.assertRaises(RuntimeError):
            pv.portal_role(config, 1200, 'agent')

    def test_one_workstation_session_per_uid_and_release_on_disconnect(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(pv, 'RUNTIME', Path(tmp)):
            with pv.portal_login_lock(1200):
                with self.assertRaisesRegex(RuntimeError, 'already has a workstation session'):
                    with pv.portal_login_lock(1200):
                        self.fail('Duplicate login was allowed')
                with pv.portal_login_lock(1201):
                    pass  # A white account can observe while blue is connected.
            with pv.portal_login_lock(1200):
                pass  # Reconnect after the previous session ended.
            with self.assertRaises(ValueError):
                with pv.portal_login_lock(1200):
                    raise ValueError('Session failed')
            with pv.portal_login_lock(1200):
                pass  # Exceptions release the account slot too.

    def test_exec_is_one_argument_inside_blue_not_host_shell(self):
        payload = "echo ok; whoami; printf '%s' '--role control'"
        argv = pv.join_argv('blue', 'paper-vianden-test', payload, tty=False)
        self.assertEqual(argv[-4:], ['defender', 'bash', '-lc', payload])
        self.assertIn('-T', argv)
        self.assertNotIn('-t', argv)
        self.assertEqual(argv[:len(pv.DOCKER)], pv.DOCKER)
        self.assertNotIn('shell=True', str(argv))

    def test_interactive_white_enters_distinct_container(self):
        argv = pv.join_argv('white', 'paper-vianden-test', tty=True)
        self.assertEqual(argv[-2:], ['white', 'bash'])
        self.assertIn('-t', argv)
        with self.assertRaises(KeyError):
            pv.join_argv('unknown', 'paper-vianden-test')

    def test_ssh_block_scopes_forcing_to_selected_accounts(self):
        block = install_portals.ssh_block({'agent': {}, 'observer': {}})
        self.assertIn('Match User agent,observer', block)
        self.assertIn('DisableForwarding yes', block)
        self.assertIn('PermitUserRC no', block)
        # UID flock, not MaxSessions=1: OpenSSH channel teardown can lag exit
        # status and spuriously reject sequential commands on a reused transport.
        self.assertNotIn('MaxSessions 1', block)
        self.assertIn('ForceCommand /usr/local/libexec/paper-vianden-ssh', block)
        self.assertNotIn('Match all', block)
        for name in ('root\nForceCommand evil', '../root', 'a,b', 'x y'):
            with self.assertRaises(ValueError):
                install_portals.ssh_block({name: {}})

    def test_ssh_config_update_is_idempotent_preserves_admin_settings(self):
        original = 'Port 22\nUsePAM yes\nPermitRootLogin prohibit-password\n'
        block = install_portals.ssh_block({'agent': {}})
        configured = install_portals.replace_block(original, block)
        self.assertTrue(configured.startswith(original.rstrip()))
        self.assertEqual(install_portals.replace_block(configured, block), configured)
        with self.assertRaises(ValueError):
            install_portals.replace_block(configured+'Port 23\n', block)
        with self.assertRaises(ValueError):
            install_portals.replace_block(original+install_portals.BEGIN, block)

    def test_owner_lease_has_deadline_not_restart_or_boot_enable(self):
        unit = install_portals.owner_unit(42, 60, 7200)
        self.assertIn('RuntimeMaxSec=7200', unit)
        self.assertIn('serve --seed 42 --clock-speed 60', unit)
        self.assertIn('KillMode=mixed', unit)
        self.assertIn('Restart=no', unit)
        self.assertNotIn('[Install]', unit)

    def test_white_status_waits_for_workers_and_reads_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = tuple(Path(tmp)/name for name in ('private', 'users', 'dns'))
            for path in dirs:
                path.mkdir()
            with patch.object(white, 'ROOTS', dirs):
                self.assertEqual(white.status()['story'], {'state': 'waiting'})
                path = dirs[0]/'story-status.json'
                path.write_text(json.dumps({'phase': 'discovery'}))
                before = path.read_bytes()
                self.assertEqual(white.status()['story']['phase'], 'discovery')
                self.assertEqual(path.read_bytes(), before)
            self.assertEqual(white.tail(dirs[0]/'absent', 2), [])
            journal = dirs[0]/'story.jsonl'
            journal.write_text('one\ntwo\nthree\n')
            self.assertEqual(white.tail(journal, 2), ['two\n', 'three\n'])


if __name__ == '__main__':
    unittest.main()
