"""Private immutable input bodies in the caller's GovernanceStore transaction."""
import hashlib

from ..errors import require


class WorkInputStore:
    @staticmethod
    def save(cx, au_id, work_id, item, content):
        cx.execute('CREATE TABLE IF NOT EXISTS work_input_bodies('
                   'au_id TEXT NOT NULL, work_id TEXT NOT NULL, input_id TEXT NOT NULL, content TEXT NOT NULL, '
                   'PRIMARY KEY(au_id,work_id,input_id))')
        cx.execute('INSERT INTO work_input_bodies VALUES(?,?,?,?)', (au_id, work_id, item['id'], content))

    @staticmethod
    def load(cx, au_id, work_id, item):
        require(cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='work_input_bodies'").fetchone(),
                '原输入正文缺失；不能修复或重新派发')
        row = cx.execute('SELECT content FROM work_input_bodies WHERE au_id=? AND work_id=? AND input_id=?',
                         (au_id, work_id, item['id'])).fetchone()
        require(row is not None, '原输入正文缺失或不属于此 AU/Work')
        raw = row[0].encode('utf-8')
        require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'],
                '原输入正文摘要已变化；不能使用')
        return row[0]
