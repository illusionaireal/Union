"""Retired installer entry point; no host configuration or service mutations."""
import json


def main():
    print(json.dumps({
        'decision': 'retired',
        'reason': (
            'Legacy development controller installation is retired. '
            'Use scripts/kanban-operations.mjs and a task-branch PR to rewrite/charter-v1 '
            'for new development. Existing host services and history require separate '
            'operator review; this command does not read or change them.'
        ),
    }, indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
