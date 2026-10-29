"""Host-observed committed work transitions; old unknown history stays unknown."""
import copy
from collections import Counter
from .engine import instant


def track_work(previous, current, at):
    for key, work in current.get('work', {}).items():
        old = previous.get('work', {}).get(key)
        if old is not None and old['status'] == work['status']:
            continue
        life = copy.deepcopy(old.get('lifecycle')) if old else None
        if not life:
            life = {'coverage': 'complete' if old is None else 'partial',
                    'created_at': at if old is None else None,
                    'first_started_at': None, 'last_started_at': None, 'last_blocked_at': None,
                    'last_resumed_at': None, 'last_delivered_at': None, 'dispatch_count': 0}
        life['status_since'] = at
        if work['status'] == 'running':
            life['last_started_at'] = at
            life['dispatch_count'] += 1
            if life['coverage'] == 'complete' and life['first_started_at'] is None:
                life['first_started_at'] = at
        if work['status'] == 'blocked':
            life['last_blocked_at'] = at
        if work['status'] == 'pending' and old and old['status'] in ('blocked','failed','paused','needs_review'):
            life['last_resumed_at'] = at
        if work['status'] == 'delivered':
            life['last_delivered_at'] = at
        work['lifecycle'] = life


def seconds(start, end):
    try:
        elapsed = (instant(end) - instant(start)).total_seconds()
        return elapsed if elapsed >= 0 else None
    except (ValueError, TypeError):
        return None


def work_metrics(state, at=None):
    from .engine import now
    at = at or now()
    works = list(state.get('work', {}).values())
    cycles = []
    unknown_cycles = 0
    blocked = []
    for w in works:
        life = w.get('lifecycle') or {}
        if w['status'] == 'delivered':
            value = seconds(life.get('first_started_at'), life.get('last_delivered_at'))
            if value is None: unknown_cycles += 1
            else: cycles.append(value)
        if w['status'] == 'blocked':
            blocked.append({'work_id': w['id'], 'seconds': seconds(life.get('status_since'), at)})
    return {'record_scope': 'work_records_not_business_acceptance', 'work_count': len(works),
            'status_counts': dict(Counter(w['status'] for w in works)),
            'lifecycle_unknown_count': sum(not w.get('lifecycle') for w in works),
            'lifecycle_partial_count': sum((w.get('lifecycle') or {}).get('coverage') == 'partial' for w in works),
            'cycle_seconds': {'definition': 'first_start_to_latest_delivery', 'known_count': len(cycles),
                              'unknown_count': unknown_cycles, 'mean': sum(cycles)/len(cycles) if cycles else None},
            'blocked_age': blocked}
