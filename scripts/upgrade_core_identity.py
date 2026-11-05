"""Explicitly upgrade core identity/catalog storage while the service is stopped."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_union.engine import Rejected
from ai_union.identity_schema import upgrade


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--services-stopped", action="store_true")
    parser.add_argument("--rollback", action="store_true", help="仅回退尚无任何后续写入的升级")
    args = parser.parse_args(argv)
    try:
        result = upgrade(args.root, services_stopped=args.services_stopped, rollback=args.rollback)
    except Rejected as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        print("身份升级未完成；保留数据库与备份，核对服务锁、存储及原请求。", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
