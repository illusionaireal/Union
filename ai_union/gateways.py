"""Platform gateway registry. No upstream credentials or deployment authority here."""
import copy
import hashlib
import json
import re
import subprocess
import sys
import threading
from urllib.parse import urlsplit

from .engine import Rejected, encoded, identifier, now, require, text
from .model_api import api_connection, is_loopback


def address(value):
    require(isinstance(value, str) and 0 < len(value) <= 2000 and
            all(32 < ord(c) < 127 for c in value), "网关地址格式无效")
    try:
        p = urlsplit(value)
        require(p.hostname and not p.username and not p.password and not p.query and not p.fragment,
                "网关地址不能含认证、查询参数或片段")
        require(p.scheme == "https" or (p.scheme == "http" and is_loopback(p.hostname)),
                "网关使用 HTTPS；仅回环地址允许 HTTP")
        require(p.port is None or 1 <= p.port <= 65535, "网关端口无效")
    except ValueError as error:
        if isinstance(error, Rejected):
            raise
        raise Rejected("网关地址格式无效") from None
    return value.rstrip("/")


def configuration(value):
    require(isinstance(value, dict) and set(value) ==
            {"name", "service_url", "api_base_url", "admin_url", "mode"}, "网关配置字段无效")
    value = copy.deepcopy(value)
    text(value["name"], "网关名称", 100)
    require(value["mode"] in ("external", "managed"), "网关接入方式无效")
    for field in ("service_url", "api_base_url", "admin_url"):
        value[field] = address(value[field])
    return value


def probe(config):
    """The subprocess deadline also bounds DNS and slow-drip HTTP responses."""
    try:
        completed = subprocess.run([sys.executable, "-m", "ai_union.gateways"], input=encoded(config),
                                   capture_output=True, text=True, timeout=4, check=True)
        return json.loads(completed.stdout)
    except (subprocess.SubprocessError, OSError, ValueError):
        return {"health": "unavailable", "version": None, "message": "无法在时限内读取网关状态；部署状态未知"}


def _fetch_status(config):
    """Bounded, credential-free GET; never follow redirects or expose remote bodies."""
    p = urlsplit(config["service_url"])
    connection = api_connection(p, 2)
    try:
        connection.request("GET", (p.path.rstrip("/") or "") + "/api/status",
                           headers={"Accept": "application/json"})
        response = connection.getresponse()
        body = response.read(65537)
        if response.status != 200 or len(body) > 65536:
            return {"health": "unavailable", "version": None, "message": "状态接口未返回有效响应"}
        value = json.loads(body)
        if not isinstance(value, dict) or value.get("success") is not True or not isinstance(value.get("data"), dict):
            return {"health": "unavailable", "version": None, "message": "状态接口格式不匹配"}
        version = value["data"].get("version")
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+/-]{0,127}", version):
            version = None
        return {"health": "healthy", "version": version, "message": "网关状态接口正常；模型能力尚需单独测试"}
    except (OSError, ValueError, TypeError):
        return {"health": "unavailable", "version": None, "message": "无法读取网关状态；部署状态未知"}
    finally:
        connection.close()


class Gateways:
    def __init__(self, app):
        self.app = app
        self.lock = threading.RLock()
        with app.catalog() as cx:
            cx.execute("CREATE TABLE IF NOT EXISTS gateways(id TEXT PRIMARY KEY, record TEXT NOT NULL)")
            cx.execute("CREATE TABLE IF NOT EXISTS gateway_commands(id TEXT PRIMARY KEY, payload TEXT NOT NULL, receipt TEXT NOT NULL)")
            for row in cx.execute("SELECT id,receipt FROM gateway_commands").fetchall():
                receipt = json.loads(row["receipt"])
                if receipt["status"] == "accepted":
                    receipt.update(status="unknown", message="检测作业被中断；可提交新的只读检测，不重放原请求")
                    cx.execute("UPDATE gateway_commands SET receipt=? WHERE id=?", (encoded(receipt), row["id"]))

    def authorize(self, token):
        session = self.app.session(token)
        require(session.get("platform_admin") is True and session["organizations"] is None,
                "会话没有平台网关管理权限")
        return session

    def list(self, token, org_id=None):
        if org_id is None:
            self.authorize(token)
        else:
            require(self.app.session(token)["role"] == "board", "观察者不能读取网关连接参数")
            self.app.engine(token, org_id)
        with self.app.read_catalog() as cx:
            records = [json.loads(r[0]) for r in cx.execute("SELECT record FROM gateways ORDER BY id")]
        result = {"gateways": [r for r in records if not r["archived"]], "service_instance": self.app.instance}
        if org_id is not None:
            result["gateways"] = [{"id": r["id"], "revision": r["revision"],
                                   "config": {k: r["config"][k] for k in ("name", "api_base_url")}}
                                  for r in result["gateways"]]
        if org_id is None:
            with self.app.read_catalog() as cx:
                result["receipts"] = [json.loads(r[0]) for r in cx.execute("SELECT receipt FROM gateway_commands ORDER BY rowid DESC LIMIT 20")]
        return result

    def reference(self, gateway_id, revision, base_url):
        identifier(gateway_id)
        with self.app.read_catalog() as cx:
            row = cx.execute("SELECT record FROM gateways WHERE id=?", (gateway_id,)).fetchone()
        require(row is not None, "网关不存在")
        record = json.loads(row[0])
        require(not record["archived"] and type(revision) is int and revision == record["revision"],
                "网关登记已变化；刷新后重新选择")
        require(base_url == record["config"]["api_base_url"], "连接地址与所选网关不一致")
        return {"id": gateway_id, "revision": revision}

    def receipt(self, token, request_id):
        self.authorize(token)
        identifier(request_id)
        with self.app.read_catalog() as cx:
            row = cx.execute("SELECT receipt FROM gateway_commands WHERE id=?", (request_id,)).fetchone()
        require(row is not None, "未找到网关请求回执")
        return json.loads(row[0])

    def command(self, token, request):
        session = self.authorize(token)
        require(isinstance(request, dict) and set(request) == {"id", "gateway_id", "base_revision", "kind", "data"}, "网关命令字段无效")
        request = copy.deepcopy(request)
        identifier(request["id"])
        identifier(request["gateway_id"])
        require(request["kind"] in ("save", "archive", "probe"), "此部署控制能力尚未接通")
        require(isinstance(request["data"], dict) and len(encoded(request)) <= 12000, "网关命令数据无效")
        data = request["data"]
        require(set(data) == ({"config"} if request["kind"] == "save" else set()), "网关命令数据字段无效")
        if request["kind"] == "save":
            data["config"] = configuration(data["config"])
        # Persist a digest, not arbitrary command bodies (including unrecognized secrets).
        digest = hashlib.sha256(encoded(request).encode()).hexdigest()
        with self.lock, self.app.catalog() as cx:
            prior = cx.execute("SELECT payload,receipt FROM gateway_commands WHERE id=?", (request["id"],)).fetchone()
            if prior:
                require(prior["payload"] == digest, "请求标识已用于不同参数；查询原回执")
                return json.loads(prior["receipt"])
            row = cx.execute("SELECT record FROM gateways WHERE id=?", (request["gateway_id"],)).fetchone()
            record = json.loads(row[0]) if row else None
            receipt = {"id": request["id"], "gateway_id": request["gateway_id"], "kind": request["kind"],
                       "actor": session["actor"], "created_at": now(), "status": "succeeded", "message": "网关登记已保存"}
            try:
                require(type(request["base_revision"]) is int and request["base_revision"] == (record["revision"] if record else 0), "网关版本冲突；刷新后重新操作")
                if request["kind"] == "save":
                    require(not record or not record["archived"], "已解除登记的 ID 不能复用")
                    record = {"id": request["gateway_id"], "revision": request["base_revision"] + 1,
                              "config": data["config"], "archived": False, "updated_at": now(),
                              "deployment_state": "unknown", "health": "unknown", "version": None,
                              "checked_at": None, "message": "尚未检测", "capabilities": []}
                else:
                    require(record and not record["archived"], "网关不存在或已解除登记")
                    if request["kind"] == "archive":
                        record.update(archived=True, revision=record["revision"] + 1, updated_at=now())
                        receipt["message"] = "已解除登记；现有 AU 独立连接和远端服务保持原状"
                    else:
                        active = [json.loads(r[0]) for r in cx.execute("SELECT receipt FROM gateway_commands")]
                        active = [r for r in active if r["status"] == "accepted"]
                        require(not any(r["gateway_id"] == record["id"] for r in active), "此网关已有检测作业，请查询原回执")
                        require(len(active) < 8, "检测作业繁忙，请稍后重试")
                        record["last_probe_id"] = request["id"]
                        receipt.update(status="accepted", message="健康检测已受理，不调用模型")
                cx.execute("INSERT OR REPLACE INTO gateways VALUES(?,?)", (record["id"], encoded(record)))
            except Rejected as error:
                receipt.update(status="rejected", message=str(error))
            cx.execute("INSERT INTO gateway_commands VALUES(?,?,?)", (request["id"], digest, encoded(receipt)))
        if receipt["status"] == "accepted":
            try:
                thread = threading.Thread(target=self._probe_job, args=(copy.deepcopy(record), copy.deepcopy(receipt)), daemon=False)
                with self.app.mutex:
                    thread.start()
                    self.app.jobs.append(thread)
            except (RuntimeError, OSError):
                receipt.update(status="rejected", message="无法启动检测作业")
                with self.app.catalog() as cx:
                    cx.execute("UPDATE gateway_commands SET receipt=? WHERE id=?", (encoded(receipt), request["id"]))
        return receipt

    def _probe_job(self, record, receipt):
        try:
            result = probe(record["config"])
            with self.lock, self.app.catalog() as cx:
                row = cx.execute("SELECT record FROM gateways WHERE id=?", (record["id"],)).fetchone()
                current = json.loads(row[0])
                # A response for an old endpoint may never overwrite a new revision.
                fresh = current["revision"] == record["revision"] and not current["archived"] and current.get("last_probe_id") == receipt["id"]
                if fresh:
                    current.update(result, checked_at=now())
                    cx.execute("UPDATE gateways SET record=? WHERE id=?", (encoded(current), current["id"]))
                receipt.update(status="succeeded", message=result["message"] if fresh else "登记已变化；旧检测结果未应用", ended_at=now())
                cx.execute("UPDATE gateway_commands SET receipt=? WHERE id=?", (encoded(receipt), receipt["id"]))
        except Exception:
            receipt.update(status="unknown", message="检测作业异常；部署状态未知", ended_at=now())
            with self.app.catalog() as cx:
                cx.execute("UPDATE gateway_commands SET receipt=? WHERE id=?", (encoded(receipt), receipt["id"]))


if __name__ == "__main__":
    print(encoded(_fetch_status(configuration(json.loads(sys.stdin.read(12001))))))
