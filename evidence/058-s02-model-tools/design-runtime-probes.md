# Runtime 纯内存探针

2026-11-06；独立 runtime_chain_audit 执行；基点 c31bf0e 上的 S02 工作树。以下为原报告的探针代码和结果。

## 7. 最小只读探针与结果

执行方式：固定 .venv/Scripts/python.exe，以 PYTHONUTF8=1、PYTHONIOENCODING=utf-8、PYTHONDONTWRITEBYTECODE=1 从 stdin 执行。退出码 0。没有创建 Console/AU/模型客户端、没有访问模型、没有线程真正启动、没有数据库或正式代码写入。

~~~python
import json, threading
from types import SimpleNamespace
from unittest.mock import patch
from ai_union.application.model_access import ModelAccessService
from ai_union.runner import step

service = ModelAccessService.__new__(ModelAccessService)
service.app = SimpleNamespace(mutex=threading.RLock(), jobs=[])
service.running = set()
with patch(
    "ai_union.application.model_access.threading.Thread.start",
    side_effect=RuntimeError("synthetic thread-start failure"),
):
    try:
        service.spawn(lambda *_: None, "au-probe", "check-probe")
    except RuntimeError:
        pass
with patch("ai_union.application.model_access.threading.Thread.start") as restarted:
    service.spawn(lambda *_: None, "au-probe", "check-probe")
    spawn_probe = {
        "key_remains_registered": ("au-probe", "check-probe") in service.running,
        "explicit_reconcile_would_start_thread": restarted.called,
    }

class IndependentReady:
    def paused(self): return False
    def wake_due(self): return 0
    def ready_work(self): return ["unrelated-ready-work"]
    def state(self): return {"phase": "active"}
    def runs(self):
        return [{"status": "unknown", "work_id": "different-work"}]

print(json.dumps({
    "thread_start_probe": spawn_probe,
    "runner_independent_work_probe": step(IndependentReady(), object()),
}, ensure_ascii=False))
~~~

实际 stdout：

~~~json
{
  "thread_start_probe": {
    "key_remains_registered": true,
    "explicit_reconcile_would_start_thread": false
  },
  "runner_independent_work_probe": {
    "action": "blocked",
    "reason": "未知或在途执行需要核对"
  }
}
~~~

这是直接函数路径/异常清理的验证；并非全量回归、模型服务实际网络验收或真实多 AU 并发能力证明。
