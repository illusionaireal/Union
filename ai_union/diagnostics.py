"""Bounded host-owned diagnostics for the existing organization decision scope.

Never return raw provider/executor text, prompts, run packages or command output.
This is a read projection, not an execution or reconciliation API.
"""
import json

from .engine import ID, instant, require
from .failures import public_failure


def reference(value):
    return value if isinstance(value, str) and ID.fullmatch(value) else None


def timestamp(value):
    try:
        return instant(value).isoformat() if isinstance(value, str) else None
    except ValueError:
        return None


def usage_summary(value):
    value = value if isinstance(value, dict) else {}
    result = {k: v for k, v in value.items()
              if k in ('input_tokens', 'output_tokens', 'cached_input_tokens')
              and type(v) is int and 0 <= v <= 10**15}
    # Stored cost is not a verified supplier invoice; never infer zero.
    return result | {'cost': None, 'cost_status': 'unknown'}


def decision_diagnostics(engine, cx, state, limit=12):
    require(type(limit) is int and 1 <= limit <= 30, '诊断历史上限须为1至30')
    runs = []
    for row in cx.execute("SELECT id,kind,work_id,status,executor,started_at,ended_at,usage,CASE WHEN json_type(result,'$.failure')='object' THEN json_extract(result,'$.failure') END AS failure FROM runs ORDER BY rowid DESC LIMIT ?", (limit,)):
        r = dict(row)
        failure = public_failure(json.loads(r['failure']) if r['failure'] else None)
        record = {'id': reference(r['id']), 'work_id': reference(r['work_id']),
                  'kind': r['kind'] if r['kind'] in ('work','decision','connection_test') else 'unrecognized',
                  'status': r['status'] if r['status'] in ('running','continued','delivered','failed','blocked','unknown','reconciled') else 'unrecognized',
                  'executor': r['executor'] if r['executor'] in ('api','fixture','codex') else 'unrecognized',
                  'started_at': timestamp(r['started_at']), 'ended_at': timestamp(r['ended_at']),
                  'usage': usage_summary(json.loads(r['usage']) if r['usage'] else {})}
        if failure:
            record['failure'] = failure
        runs.append(record)
    artifacts = sorted(state['artifacts'].values(), key=lambda a: (timestamp(a.get('created_at')) or '', reference(a.get('id')) or ''), reverse=True)
    refs = [{'id': reference(a.get('id')), 'work_id': reference(a.get('work_id')), 'run_id': reference(a.get('run_id')),
             'created_at': timestamp(a.get('created_at'))} for a in artifacts[:limit]]
    count = cx.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
    return {'scope': 'organization_decision', 'verification': 'runtime_records_not_real_execution_attestation',
            'limit': limit, 'run_count': count, 'runs_truncated': count > limit, 'recent_runs': runs,
            'artifact_count': len(artifacts), 'artifacts_truncated': len(artifacts) > limit, 'recent_artifacts': refs}
