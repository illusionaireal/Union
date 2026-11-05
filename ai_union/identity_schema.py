"""Versioned core identity/catalog storage and explicit, stopped-service upgrades."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from .errors import Rejected, require
from .locking import file_lock

CURRENT = {"auth": 2, "catalog": 1}
UPGRADE_RECEIPT = "core-identity-upgrade.json"
LEGACY_COLUMNS = {
    "organizations": {"id", "folder"},
    "creations": {"id", "payload", "receipt", "folder"},
    "owner_account": {"username", "salt", "password_hash", "recovery_hash", "platform_admin"},
    "login_sessions": {"digest", "username", "data", "expires", "deadline"},
    "login_limit": {"id", "failures", "until"},
}
NEW_COLUMNS = {
    "organizations": {"profile"},
    "creations": {"profile", "creator_principal_id", "allocated_au_id"},
    "owner_account": {"principal_id"},
}


def _columns(cx, table):
    return {row[1] for row in cx.execute(f"PRAGMA table_info({table})")}


def _versions(cx):
    tables = {row[0] for row in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not tables:
        return None
    require(LEGACY_COLUMNS.keys() <= tables, "核心身份目录不完整；请保留记录核对")
    if "core_schema" not in tables:
        require(all(_columns(cx, table) == columns for table, columns in LEGACY_COLUMNS.items()),
                "未标记的核心身份目录含未知结构；请保留记录核对")
        return {"auth": 0, "catalog": 0}
    marker = _columns(cx, "core_schema")
    require({"id", "auth_version", "catalog_version"} <= marker, "核心身份版本缺少必要列")
    rows = cx.execute("SELECT auth_version,catalog_version FROM core_schema WHERE id=1").fetchall()
    require(len(rows) == 1 and all(type(n) is int and n >= 1 for n in rows[0]), "核心身份版本无效")
    versions = dict(zip(("auth", "catalog"), rows[0]))
    if versions in ({"auth": 1, "catalog": 1}, CURRENT):
        require({"write_revision", "upgrade_receipt"} <= marker, "核心身份版本缺少必要列")
        markers = cx.execute("SELECT id,write_revision FROM core_schema").fetchall()
        require(len(markers) == 1 and markers[0][0] == 1
                and type(markers[0][1]) is int and markers[0][1] >= 0, "核心身份写入版本无效")
        for table, columns in LEGACY_COLUMNS.items():
            require(columns | NEW_COLUMNS.get(table, set()) <= _columns(cx, table), "核心身份目录缺少必要列")
        for row in cx.execute("SELECT principal_id FROM owner_account"):
            try:
                require(str(uuid.UUID(row[0])) == row[0], "核心主体标识无效")
            except (ValueError, TypeError, AttributeError) as error:
                raise Rejected("核心主体标识无效") from error
        if versions["auth"] == 2:
            require("account_kind" in _columns(cx, "owner_account"), "核心账户缺少权限类别")
            require({"username", "failures", "until"} <= _columns(cx, "account_login_limit"), "核心账户缺少独立登录限流记录")
            kinds = [row[0] for row in cx.execute("SELECT account_kind FROM owner_account")]
            require(all(kind in ("owner", "core") for kind in kinds) and kinds.count("owner") <= 1,
                    "核心账户权限类别无效")
            require(cx.execute("SELECT 1 FROM owner_account WHERE account_kind='core' AND platform_admin!=0").fetchone() is None,
                    "普通核心账户不能拥有宿主平台权限")
    return versions


def versions(database):
    database = Path(database)
    if not database.exists():
        return None
    require(database.is_file() and not database.is_symlink(), "核心身份目录必须是普通数据库")
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as cx:
        cx.execute("PRAGMA query_only=ON")
        cx.execute("BEGIN")
        return _versions(cx)


def _revision_triggers(cx):
    # Even an insert subsequently deleted invalidates an upgrade-time backup.
    # Other catalog changes are additionally covered by the full logical digest.
    for table in (*LEGACY_COLUMNS, "account_login_limit"):
        for action in ("INSERT", "UPDATE", "DELETE"):
            cx.execute(f"CREATE TRIGGER IF NOT EXISTS core_revision_{table}_{action.lower()} AFTER {action} ON {table} "
                       "BEGIN UPDATE core_schema SET write_revision=write_revision+1 WHERE id=1; END")


def _marker(cx):
    cx.execute("CREATE TABLE core_schema(id INTEGER PRIMARY KEY CHECK(id=1), auth_version INTEGER NOT NULL, catalog_version INTEGER NOT NULL, write_revision INTEGER NOT NULL, upgrade_receipt TEXT)")
    cx.execute("INSERT INTO core_schema VALUES(1,?,?,0,NULL)", (CURRENT["auth"], CURRENT["catalog"]))
    _revision_triggers(cx)


def ensure_current(database):
    """Initialize only an empty store; reject an old store without mutating it."""
    database = Path(database)
    current = versions(database)
    if current is not None:
        require(current == CURRENT,
                "核心身份目录需要显式升级；停止服务后运行 python scripts/upgrade_core_identity.py --root <服务目录> --services-stopped")
        return
    if not database.exists():
        fd = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    with closing(sqlite3.connect(database)) as cx, cx:
        cx.execute("BEGIN IMMEDIATE")
        require(_versions(cx) is None, "核心身份目录在初始化前发生变化")
        cx.execute("CREATE TABLE organizations(id TEXT PRIMARY KEY, folder TEXT NOT NULL, profile TEXT NOT NULL DEFAULT 'legacy_v0')")
        cx.execute("CREATE TABLE creations(id TEXT PRIMARY KEY, payload TEXT NOT NULL, receipt TEXT NOT NULL, folder TEXT NOT NULL, profile TEXT NOT NULL DEFAULT 'legacy_v0', creator_principal_id TEXT, allocated_au_id TEXT)")
        cx.execute("CREATE TABLE owner_account(username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL, recovery_hash TEXT NOT NULL, platform_admin INTEGER NOT NULL, principal_id TEXT NOT NULL UNIQUE, account_kind TEXT NOT NULL DEFAULT 'owner' CHECK(account_kind IN ('owner','core')))")
        cx.execute("CREATE UNIQUE INDEX core_single_owner ON owner_account(account_kind) WHERE account_kind='owner'")
        cx.execute("CREATE TABLE login_sessions(digest TEXT PRIMARY KEY, username TEXT NOT NULL, data TEXT NOT NULL, expires REAL NOT NULL, deadline REAL NOT NULL)")
        cx.execute("CREATE TABLE login_limit(id INTEGER PRIMARY KEY, failures INTEGER NOT NULL, until REAL NOT NULL)")
        cx.execute("CREATE TABLE account_login_limit(username TEXT PRIMARY KEY, failures INTEGER NOT NULL, until REAL NOT NULL)")
        _marker(cx)
    database.chmod(0o600)


def _digest_in(cx):
    schema = list(cx.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"))
    contents = []
    for kind, name, _, _ in schema:
        if kind != "table":
            continue
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [row[1] for row in cx.execute("PRAGMA table_info(" + quoted + ")")]
        # The receipt contains this digest. Its catalog value owns recovery;
        # excluding that one field avoids a self-referential hash.
        if name == "core_schema":
            columns.remove("upgrade_receipt")
        selection = ",".join('"' + column.replace('"', '""') + '"' for column in columns)
        rows = [[(type(value).__name__, repr(value)) for value in row]
                for row in cx.execute("SELECT " + selection + " FROM " + quoted)]
        contents.append((name, columns, sorted(rows)))
    return hashlib.sha256(json.dumps((schema, contents), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _logical_digest(database):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as cx:
        cx.execute("BEGIN")
        return _digest_in(cx)


def _write_receipt(root, receipt):
    target = root / UPGRADE_RECEIPT
    require(not target.is_symlink(), "升级收据不能是链接")
    temporary = root / (".identity-upgrade-" + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def _upgrade(root, database):
    target = root / UPGRADE_RECEIPT
    require(not target.is_symlink() and (not target.exists() or target.is_file()), "升级收据路径不可写；请先核对冲突")
    current = versions(database)
    if current == CURRENT:
        with closing(sqlite3.connect(database)) as cx:
            saved = cx.execute("SELECT upgrade_receipt FROM core_schema WHERE id=1").fetchone()[0]
        if saved:
            receipt = json.loads(saved)
            _write_receipt(root, receipt)
            return receipt | {"already_current": True}
        return {"schema": CURRENT, "already_current": True, "backup": None}
    require(current in ({"auth": 0, "catalog": 0}, {"auth": 1, "catalog": 1}), "只能显式升级已知旧版身份目录")
    backup = root / ("console.pre-core-v1." + uuid.uuid4().hex + ".sqlite3")
    fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
    with closing(sqlite3.connect(database)) as cx, cx:
        cx.execute("BEGIN IMMEDIATE")
        require(_versions(cx) == current, "升级前身份目录版本发生变化")
        if current["auth"] == 0:
            cx.execute("ALTER TABLE owner_account ADD COLUMN principal_id TEXT")
            for (username,) in cx.execute("SELECT username FROM owner_account").fetchall():
                cx.execute("UPDATE owner_account SET principal_id=? WHERE username=?", (str(uuid.uuid4()), username))
            cx.execute("CREATE UNIQUE INDEX core_owner_principal ON owner_account(principal_id)")
            cx.execute("ALTER TABLE organizations ADD COLUMN profile TEXT NOT NULL DEFAULT 'legacy_v0'")
            cx.execute("ALTER TABLE creations ADD COLUMN profile TEXT NOT NULL DEFAULT 'legacy_v0'")
            cx.execute("ALTER TABLE creations ADD COLUMN creator_principal_id TEXT")
            cx.execute("ALTER TABLE creations ADD COLUMN allocated_au_id TEXT")
        cx.execute("ALTER TABLE owner_account ADD COLUMN account_kind TEXT NOT NULL DEFAULT 'owner' CHECK(account_kind IN ('owner','core'))")
        cx.execute("CREATE UNIQUE INDEX core_single_owner ON owner_account(account_kind) WHERE account_kind='owner'")
        cx.execute("CREATE TABLE account_login_limit(username TEXT PRIMARY KEY, failures INTEGER NOT NULL, until REAL NOT NULL)")
        cx.execute("DELETE FROM login_sessions")
        if current["auth"] == 0:
            _marker(cx)
        else:
            cx.execute("UPDATE core_schema SET auth_version=2,upgrade_receipt=NULL WHERE id=1")
            _revision_triggers(cx)
        receipt = {"protocol": "core.identity.upgrade.v1", "from_schema": current, "schema": CURRENT, "backup": backup.name,
                   "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(), "after_sha256": _digest_in(cx)}
        cx.execute("UPDATE core_schema SET upgrade_receipt=? WHERE id=1", (json.dumps(receipt, sort_keys=True),))
    _write_receipt(root, receipt)
    return receipt


def _rollback(root, database):
    require(versions(database) == CURRENT, "当前身份目录不是可回退的升级版本")
    with closing(sqlite3.connect(database)) as cx:
        saved = cx.execute("SELECT upgrade_receipt FROM core_schema WHERE id=1").fetchone()[0]
    require(saved is not None, "缺少可核对的升级收据")
    receipt = json.loads(saved)
    require(receipt.get("protocol") == "core.identity.upgrade.v1" and receipt.get("schema") == CURRENT, "升级收据版本不兼容")
    require(isinstance(receipt.get("backup"), str) and re.fullmatch(r"console\.pre-core-v1\.[0-9a-f]{32}\.sqlite3", receipt["backup"]), "升级备份标识无效")
    backup = root / receipt["backup"]
    require(backup.is_file() and not backup.is_symlink(), "升级备份不存在或不是普通文件")
    require(hashlib.sha256(backup.read_bytes()).hexdigest() == receipt["backup_sha256"], "升级备份已变化；不能回退")
    require(versions(database) == CURRENT and _logical_digest(database) == receipt["after_sha256"],
            "升级后已有写入或目录变化；禁止用旧备份抹去新事实")
    with closing(sqlite3.connect(backup)) as source, closing(sqlite3.connect(database)) as target:
        source.backup(target)
    return {"schema": receipt["from_schema"], "rolled_back": True, "backup": backup.name}


def upgrade(root, *, services_stopped=False, rollback=False):
    require(services_stopped, "必须先停止服务并确认 --services-stopped")
    original = Path(root).expanduser().absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (original, *original.parents)), "升级目录不能含链接")
    root = original.resolve()
    database = root / "console.sqlite3"
    require(root.is_dir() and database.is_file() and not database.is_symlink(), "核心身份目录不存在")
    with file_lock(root / "console.lock"):
        return _rollback(root, database) if rollback else _upgrade(root, database)
