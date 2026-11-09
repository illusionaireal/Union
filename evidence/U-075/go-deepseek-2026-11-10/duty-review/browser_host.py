import json
import sys
from http_probe import IndependentCancelledHistory

case = IndependentCancelledHistory()
try:
    case.setUp()
    case.stopped()
    def info():
        return {'origin':case.server.origin,'cookie_name':case.server.cookie_name,'token':case.token,
                'organization_id':case.au_id,'check_id':case.check_id,'attempt_id':case.attempt_id,
                'principal_id':case.principal,'requests':len(case.provider.requests),
                'reserved':case.models()['resources']['reserved_calls']}
    print(json.dumps(info()), flush=True)
    for line in sys.stdin:
        op=json.loads(line)['op']
        if op=='stop':break
        if op=='restart':case.stop();case.start()
        elif op=='revoke':case.provider.revoked=True
        elif op!='status':raise AssertionError('Unexpected fixture operation')
        print(json.dumps(info()), flush=True)
finally:
    case.doCleanups()
