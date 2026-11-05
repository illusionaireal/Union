"""Existing Console legacy creation, including its company/controller contract."""
import os
import secrets

from ..domain.creation import FIELDS, validate_creation
from ..engine import Engine, require


class LegacyAUStore:
    def create(self, directory, data, **_):
        require(set(data) - {"company", "controller_ref"} == FIELDS, "创建字段不完整或含不支持的字段")
        if "controller_ref" in data:
            from ..au_contract import validate_descriptor
            validate_descriptor(data["controller_ref"])
        if "company" in data:
            from ..company import validate_config, create
            validate_config(data["company"])
            require({"submit_chapter", "review_cycle"} <= set(data["charter"]["allowed_operations"]), "小说公司章程须授权模拟投稿与经营复盘")
        validate_creation({key: data[key] for key in FIELDS})
        require(not directory.exists(), "分配目录已存在；请核对原创建请求")
        directory.mkdir(parents=True, mode=0o700)
        key = secrets.token_urlsafe(48)
        fd = os.open(directory / "board.key", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(key)
        engine = Engine.create(directory, data["name"], data["goal"], data["charter"], data["resources"], data["board_name"], key)
        with engine.transaction() as cx:
            cx.execute("CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, payload TEXT NOT NULL, receipt TEXT NOT NULL)")
            state = engine._state(cx)
            if "company" in data:
                state["company"] = create(data["company"])
                engine._save(cx, state)
            if "controller_ref" in data:
                from ..au_contract import configure_descriptor
                configure_descriptor(engine, key, data["controller_ref"], "initial controller description", state["version"])
        return state
