"""Small, bounded analyst work queue derived only from observable telemetry."""
from collections import defaultdict, deque
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import uuid

STATUSES = ('open', 'investigating', 'resolved', 'false-positive', 'escalated')


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, maximum=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('Expected nonempty text of at most %s characters' % maximum)
    return value.strip()


class Workspace:
    def __init__(self, directory):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        path = self.directory/'workspace.json'
        self.state = json.loads(path.read_text()) if path.exists() else {
            'run': uuid.uuid4().hex, 'alerts': [], 'cases': [], 'audit': []}
        self.failures = defaultdict(lambda: deque(maxlen=5))
        self.dedup = set()
        self.save()

    def save(self):
        pending = self.directory/'workspace.tmp'
        encoded=json.dumps(self.state,ensure_ascii=True)+'\n'
        if len(encoded)>4*2**20: raise ValueError('Workspace capacity reached; export and reset the range')
        pending.write_text(encoded)
        pending.replace(self.directory/'workspace.json')

    def audit(self, action, detail):
        self.state['audit'].append({'time': now(), 'action': action, 'detail': detail})
        self.state['audit'] = self.state['audit'][-1000:]

    def observe(self, event):
        fields = event.get('fields', {})
        rule = title = None; severity = 'medium'
        if fields.get('event_type') == 'alert':
            alert = fields.get('alert', {})
            rule = 'ids:'+str(alert.get('signature_id', 'unknown'))
            title = str(alert.get('signature', 'Network IDS alert'))
            severity = 'high' if alert.get('severity', 3) <= 2 else 'medium'
        elif 'Failed password' in event['message'] or 'authentication failure' in event['message'].lower():
            window = self.failures[event['host']]; window.append(event)
            if len(window) == 5:
                elapsed = datetime.fromisoformat(event['observed_at'])-datetime.fromisoformat(window[0]['observed_at'])
                if elapsed.total_seconds() <= 60:
                    rule, title = 'auth-burst', 'Repeated authentication failures'
        if rule is None: return
        # One inbox item per rule and host per run; further occurrences update it.
        with self.lock:
            existing = next((x for x in self.state['alerts'] if x['rule'] == rule and x['host'] == event['host']), None)
            if existing:
                existing['count'] += 1; existing['last_seen'] = event['observed_at']
            else:
                if len(self.state['alerts']) >= 100: return
                self.state['alerts'].append({'id': 'A'+uuid.uuid4().hex[:10], 'rule': rule,
                    'title': title[:300], 'host': event['host'], 'severity': severity,
                    'status': 'open', 'count': 1, 'first_seen': event['observed_at'],
                    'last_seen': event['observed_at'], 'evidence': event})
            try: self.save()
            except ValueError:
                self.state['alerts'].pop()

    def get_case(self, ident):
        for case in self.state['cases']:
            if case['id'] == ident: return case
        raise ValueError('Unknown case')

    def read(self, kind, ident=None):
        with self.lock:
            if kind == 'inbox': value = self.state['alerts']
            elif kind == 'cases': value = self.state['cases']
            elif kind == 'case': value = self.get_case(ident)
            elif kind == 'audit': value = self.state['audit']
            else: raise ValueError('Unknown workspace view')
            return json.loads(json.dumps(value))

    def mutate(self, action, data, events=()):
        with self.lock:
            previous=copy.deepcopy(self.state)
            try: return self._mutate(action,data,events)
            except (ValueError,TypeError,KeyError):
                self.state=previous
                raise

    def _mutate(self, action, data, events=()):
        with self.lock:
            if action == 'open':
                if len(self.state['cases']) >= 80: raise ValueError('Case limit reached; export and reset the range')
                title = text(data.get('title'), 300)
                alert_id = data.get('alert')
                alert = next((a for a in self.state['alerts'] if a['id'] == alert_id), None)
                if alert_id and not alert: raise ValueError('Unknown alert')
                case = {'id': 'C'+uuid.uuid4().hex[:10], 'title': title, 'status': 'open',
                    'version': 1, 'created': now(), 'updated': now(), 'alert': alert_id,
                    'notes': [], 'evidence': [alert['evidence']] if alert else [], 'handovers': []}
                self.state['cases'].append(case)
                if alert: alert['status'] = 'assigned'; alert['case'] = case['id']
            else:
                case = self.get_case(data.get('case'))
                if data.get('version') != case['version']:
                    raise ValueError('Case changed; read it again and pass its current --version')
                if action == 'note':
                    note = text(data.get('text'))
                    if len(case['notes']) >= 80: raise ValueError('Case note limit reached')
                    evidence = None
                    if data.get('event'):
                        evidence = next((e for e in events if e['id'] == data['event']), None)
                        if evidence is None: raise ValueError('Event no longer retained; attach it while it is available')
                    case['notes'].append({'time': now(), 'text': note, 'event': data.get('event')})
                    if evidence and not any(e['id'] == evidence['id'] for e in case['evidence']):
                        case['evidence'].append(evidence)
                elif action == 'status':
                    status = data.get('status')
                    if status not in STATUSES: raise ValueError('Invalid case status')
                    case['status'] = status
                elif action == 'handover':
                    if len(case['handovers']) >= 12: raise ValueError('Handover limit reached')
                    report = {key: text(data.get(key)) for key in ('summary', 'actions', 'next_steps')}
                    report['time'] = now(); case['handovers'].append(report)
                else: raise ValueError('Unknown workspace action')
                case['version'] += 1; case['updated'] = now()
            self.audit(action, {'case': case['id'], 'version': case['version']})
            self.save()
            if action == 'handover':
                report = case['handovers'][-1]
                markdown = '# '+case['id']+': '+case['title']+'\n\nStatus: '+case['status']+'\n'
                for key in ('summary', 'actions', 'next_steps'):
                    markdown += '\n## '+key.replace('_',' ').title()+'\n\n'+report[key]+'\n'
                markdown += '\n## Evidence\n\n'+''.join('- '+e['id']+' | '+e['host']+' | '+e['source']+'\n' for e in case['evidence'])
                (self.directory/(case['id']+'-handover.md')).write_text(markdown)
            return json.loads(json.dumps(case))
