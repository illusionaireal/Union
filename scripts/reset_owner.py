"""Delete the local owner account so an unconfigured deployment can be claimed again.

Stop the console before running this: it rewrites the account tables directly.
Only the account rows are removed; organizations, model connections and
subscription attempts are untouched. After a reset the first visitor can claim
the account again, so run it only when you intend to reopen that window.

Usage (paths are host paths, not container paths):
  python scripts/reset_owner.py .union/console                # show what would be deleted
  python scripts/reset_owner.py .union/console --yes          # delete, with a database backup
  python scripts/reset_owner.py /volume1/docker/union-dev/ui-private/console --yes
"""
import argparse
from contextlib import closing
import sqlite3
import sys
import time
from pathlib import Path

TABLES = ('owner_account', 'login_sessions', 'login_limit')


def reset(root, confirm=False, backup=True):
    db = Path(root).expanduser().resolve() / 'console.sqlite3'
    if not db.is_file():
        raise SystemExit('数据库不存在: %s' % db)
    try:
        cx = sqlite3.connect(db, timeout=5)
    except sqlite3.Error as error:
        raise SystemExit('无法打开数据库: %s' % error)
    try:
        present = {row[0] for row in cx.execute("select name from sqlite_master where type='table'")}
        if 'owner_account' not in present:
            raise SystemExit('不是 UNION 工作台数据库（缺少 owner_account 表）: %s' % db)
        counts = {name: cx.execute('select count(*) from ' + name).fetchone()[0] for name in TABLES if name in present}
        if not confirm:
            print('数据库: %s' % db)
            print('将删除: %s' % counts)
            print('加 --yes 才会执行；执行前请先停止工作台服务。')
            return 0
        copy = None
        if backup:
            copy = db.with_name(db.name + '.bak-' + str(int(time.time())))
            with closing(sqlite3.connect(copy)) as target:
                cx.backup(target)
            copy.chmod(0o600)
        for name in TABLES:
            if name in present:
                cx.execute('delete from ' + name)
        cx.commit()
    except sqlite3.DatabaseError as error:
        raise SystemExit('数据库操作失败（请确认已停止工作台服务，且文件是有效的 SQLite 数据库）: %s' % error)
    finally:
        cx.close()
    print('已重置 %s' % db)
    if copy:
        print('重置前备份: %s' % copy)
    print('重启工作台后，任意第一个访问者都可以重新设置管理员账号。')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('root', help='工作台数据目录，例如 .union/console 或 /volume1/docker/union-dev/ui-private/console')
    parser.add_argument('--yes', action='store_true', help='实际执行删除；不加时只显示将删除的行数')
    parser.add_argument('--no-backup', action='store_true', help='跳过重置前的数据库备份')
    args = parser.parse_args(argv)
    return reset(args.root, args.yes, not args.no_backup)


if __name__ == '__main__':
    raise SystemExit(main())
