"""Private business text in the caller's GovernanceStore transaction."""
import hashlib

from ..domain import materials
from ..errors import require


class MaterialStore:
    @staticmethod
    def save(cx, item, content):
        cx.execute('CREATE TABLE IF NOT EXISTS work_materials(id TEXT PRIMARY KEY, content TEXT NOT NULL)')
        cx.execute('INSERT INTO work_materials VALUES(?,?)', (item['id'], content))

    @staticmethod
    def read(cx, item):
        row = cx.execute('SELECT content FROM work_materials WHERE id=?', (item['id'],)).fetchone()
        require(row is not None, '业务资料正文缺失；保留原引用，不能重新导入代替')
        raw = row[0].encode('utf-8')
        require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'],
                '业务资料摘要校验失败；不能继续读取')
        return row[0]

    @staticmethod
    def validate(cx, state):
        materials.validate_state(state)
        items = materials.records(state)
        if not items:
            return
        require(cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='work_materials'").fetchone() is not None,
                '业务资料正文存储缺失')
        require(cx.execute('SELECT COUNT(*) FROM work_materials').fetchone()[0] == len(items), '业务资料正文归属不一致')
        for item in items.values():
            MaterialStore.read(cx, item)
