"""Disposable actual Console/SQLite/HTTP host with one explicit loopback model double."""
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_core_work_events import WorkEventsTests, RealClient
from tests.test_work_transport_http import ModeldDouble


def main():
    case = WorkEventsTests()
    case.setUp()
    cancellations = []
    old_post = ModeldDouble.do_POST

    def post(handler):
        route = urlsplit(handler.path)
        if not route.path.endswith('/cancel'):
            return old_post(handler)
        request_id = route.path.split('/')[-2]
        au_id = parse_qs(route.query)['au_id'][0]
        expected = case.model_posts()[0][3]
        assert (request_id, au_id) == (expected['id'], expected['au_id'])
        cancellations.append({'id': request_id, 'au_id': au_id})
        case.remote_state = 'interrupted'
        case.remote_authorized = False
        return handler._send(202, {'id': request_id, 'au_id': au_id, 'state': 'cancel_requested'})

    def ready():
        return {'origin': case.server.origin, 'organization_id': case.au_id,
                'cookie_name': case.server.cookie_name, 'token': case.token}

    def inspect():
        card = case.request('/api/v1/work?organization_id=' + case.au_id)[1]['works'][0]
        return {'fake_model_posts': len(case.model_posts()), 'real_model_calls': 0,
                'cancel_posts': len(cancellations), 'budget': card['budget'],
                'steps': [{k: s.get(k) for k in ('step_ref', 'attempt_id', 'model_request_id', 'command_id', 'status')}
                          for s in card['steps']]}
    try:
        case.prepare_work()
        case.remote_state = 'streaming'
        with patch.object(ModeldDouble, 'do_POST', post):
            print(json.dumps(ready()), flush=True)
            for line in sys.stdin:
                command = line.strip()
                if command == 'stop': break
                if command == 'inspect': value = inspect()
                elif command == 'reopen':
                    deadline = time.monotonic() + 15
                    while case.app.work.active_loops and time.monotonic() < deadline: time.sleep(.02)
                    assert not case.app.work.active_loops
                    case.stop(); case.start()
                    case.app.models.backend = lambda: RealClient(str(case.config))
                    value = ready()
                else: raise AssertionError('unknown fixture control')
                print(json.dumps(value), flush=True)
    finally:
        case.remote_state = 'interrupted'
        case.tearDown()


if __name__ == '__main__': main()
