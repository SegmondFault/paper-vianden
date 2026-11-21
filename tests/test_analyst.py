"""Analyst workflow, HTTP isolation, evidence retention and contention checks."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from evidence import Feed,handler
from analyst_workspace import Workspace
from export_evidence import export


class AnalystTests(unittest.TestCase):
    def test_inbox_uses_observed_ids_and_auth_events_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed=Feed(tmp)
            feed.append('ordinary','application','normal query')
            self.assertEqual(feed.workspace.read('inbox'),[])
            fields={'event_type':'alert','src_ip':'172.28.20.23','alert':{'signature_id':9000002,'signature':'SQL union','severity':1}}
            event=feed.append('ids','eve.json',json.dumps(fields),fields)
            feed.append('ids','eve.json',json.dumps(fields),fields)
            inbox=feed.workspace.read('inbox')
            self.assertEqual(len(inbox),1);self.assertEqual(inbox[0]['count'],2)
            self.assertEqual(inbox[0]['evidence']['id'],event['id'])
            for _ in range(5):feed.append('file-01','auth.log','Failed password for example')
            self.assertEqual(len(feed.workspace.read('inbox')),2)

    def test_case_notes_keep_evidence_after_log_ring_expires_and_export_handover(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed=Feed(tmp); event=feed.append('web-01','nginx','suspicious request')
            case=feed.workspace.mutate('open',{'title':'Investigate request'})
            case=feed.workspace.mutate('note',{'case':case['id'],'version':1,'text':'Observed request','event':event['id']},list(feed.events))
            feed.events.clear()
            case=feed.workspace.mutate('handover',{'case':case['id'],'version':2,'summary':'Review needed','actions':'None yet','next_steps':'Check source'})
            self.assertEqual(case['evidence'][0]['message'],'suspicious request')
            self.assertIn('Check source',(Path(tmp)/'analyst'/(case['id']+'-handover.md')).read_text())
            resumed=Workspace(Path(tmp)/'analyst');self.assertEqual(resumed.read('case',case['id'])['version'],3)
            output=io.BytesIO();export(output,{'observations':Path(tmp)})
            with tarfile.open(fileobj=io.BytesIO(output.getvalue())) as archive:
                self.assertIn('observations/analyst/'+case['id']+'-handover.md',archive.getnames())

    def test_parallel_agents_cannot_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Workspace(tmp);case=work.mutate('open',{'title':'Shared investigation'})
            outcomes=[]
            def note():
                try:work.mutate('note',{'case':case['id'],'version':1,'text':'Concurrent note'});outcomes.append('saved')
                except ValueError:outcomes.append('conflict')
            threads=[threading.Thread(target=note) for _ in range(2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join()
            self.assertCountEqual(outcomes,['saved','conflict'])
            self.assertEqual(len(work.read('case',case['id'])['notes']),1)

    def test_search_filter_and_live_retention_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed=Feed(tmp)
            feed.append('web','nginx','GET /')
            feed.append('file','auth','Failed password')
            self.assertEqual(feed.search({'query':['password'],'host':['file']})['matches'],1)
            self.assertEqual(feed.search({'source':['nginx']})['matches'],1)
            with self.assertRaises(ValueError):feed.search({'since':['yesterday']})
            with self.assertRaises(ValueError):feed.search({'limit':['10000']})

    def test_http_rejects_uncredentialed_read_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed=Feed(tmp);feed.token='test-only-secret'
            server=ThreadingHTTPServer(('127.0.0.1',0),handler(feed))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url='http://127.0.0.1:'+str(server.server_port)
            try:
                for path,body in [('/analyst/inbox',None),('/events',None),('/analyst/open',b'{"title":"unauthorized"}')]:
                    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(url+path,data=body))
                    self.assertEqual(error.exception.code,403)
                req=urllib.request.Request(url+'/analyst/open',data=b'{"title":"Review"}',headers={'Authorization':'Bearer '+feed.token})
                result=json.load(urllib.request.urlopen(req));self.assertEqual(result['version'],1)
            finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
