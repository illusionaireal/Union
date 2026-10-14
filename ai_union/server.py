"""Same-origin local HTTP transport. No endpoint accepts a host path or board key."""
import argparse
import json
import os
import re
import sqlite3
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .console import Console
from .engine import Rejected, encoded, require
from .observation import artifact

REPO = Path(__file__).resolve().parents[1]


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, app, port=0, document=None):
        self.app = app
        self.document = document or REPO / "ai-union-console.html"
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.cookie_name = "union_" + app.instance[-12:]


class Handler(BaseHTTPRequestHandler):
    server_version = "ai-union-local"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *args):
        pass  # Never log launch credentials, payloads or private asset contents.

    def send(self, status, value, mime="application/json; charset=utf-8", headers=None):
        data = value if isinstance(value, bytes) else encoded(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for key, val in (headers or {}).items():
            self.send_header(key, val)
        try:
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            # A client timeout does not undo a committed command or justify replay.
            self.close_connection = True

    def token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            item = cookie.get(self.server.cookie_name)
            return item.value if item else None
        except Exception:
            return None

    def transport(self, write=False):
        require(self.headers.get("Host") == urlsplit(self.server.origin).netloc, "请求主机不允许")
        require(self.headers.get("Sec-Fetch-Site", "same-origin") in ("same-origin", "none"), "请求来源不允许")
        origin = self.headers.get("Origin")
        require(origin == self.server.origin if write else origin in (None, self.server.origin), "请求来源不允许")

    def handle_api(self, write=False):
        try:
            self.transport(write)
        except Rejected as error:
            return self.send(403, {"error": str(error)})
        app = self.server.app
        path = urlsplit(self.path)
        query = parse_qs(path.query)
        if not write and path.path == "/":
            try:
                content = self.server.document.read_bytes()
                match = re.search(rb'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', content)
                headers = {"Content-Security-Policy": match[1].decode() + "; frame-ancestors 'none'"} if match else {}
                return self.send(200, content, "text/html; charset=utf-8", headers)
            except OSError:
                return self.send(503, {"error": "前端尚未生成；运行 scripts/build_console.py"})
        if write and path.path == "/api/session":
            try:
                require(self.headers.get("Content-Length", "0") == "0", "会话交换不接收请求体")
                token = app.exchange(self.headers.get("X-Union-Launch", ""))
                return self.send(200, app.session_info(token), headers={"Set-Cookie": f"{self.server.cookie_name}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800"})
            except Rejected as error:
                return self.send(401, {"error": str(error)})
        token = self.token()
        try:
            app.session(token)
        except Rejected as error:
            return self.send(401, {"error": str(error)})
        try:
            if write:
                if path.path != "/api/commands":
                    return self.send(404, {"error": "接口不存在"})
                require(app.session(token)["role"] == "board", "观察者不能提交操作")
                require(self.headers.get("Content-Type", "").split(";")[0] == "application/json", "命令需要 application/json")
                length = int(self.headers.get("Content-Length", "0"))
                require(0 < length <= 200000, "请求体大小不允许")
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                receipt = app.command(token, request)
                return self.send(202 if receipt["status"] == "accepted" else 200, {"receipt": receipt})
            if path.path == "/api/session":
                return self.send(200, app.session_info(token))
            org_id = query.get("organization_id", [None])[0]
            if path.path == "/api/model-connections":
                return self.send(200, app.model_connections(token, org_id))
            if path.path == "/api/snapshot":
                return self.send(200, app.observe(token, org_id, int(query.get("offset", [0])[0])))
            if path.path == "/api/receipts":
                return self.send(200, {"receipt": app.receipt(token, org_id, query.get("id", [None])[0])})
            if path.path == "/api/artifact":
                result = artifact(app.engine(token, org_id), query.get("id", [None])[0])
                if query.get("download") == ["1"]:
                    from urllib.parse import quote
                    return self.send(200, result["content"].encode("utf-8"), "text/plain; charset=utf-8",
                                     {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(result["name"], safe="")})
                return self.send(200, result)
            return self.send(404, {"error": "接口不存在"})
        except Rejected as error:
            return self.send(403 if "会话" in str(error) or "观察者" in str(error) else 409, {"error": str(error)})
        except (ValueError, TypeError, KeyError):
            return self.send(400, {"error": "请求格式无效"})
        except (OSError, sqlite3.Error):
            return self.send(503, {"error": "本地记录或资产暂不可读取；保留请求标识后重试查询"})

    def do_GET(self):
        self.handle_api()

    def do_POST(self):
        self.handle_api(write=True)

    def do_OPTIONS(self):
        self.send(403, {"error": "不允许跨来源访问"})


def main(argv=None):
    p = argparse.ArgumentParser(description="ai-union 本地组织工作台")
    p.add_argument("--root", default=".union/console", help="私有服务目录，独立保存组织及回执")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--fixture", default=str(REPO / "examples/fixture.json"))
    p.add_argument("--enable-codex", action="store_true", help="允许网页选择 Codex；不会自动调用")
    p.add_argument("--disable-api", action="store_true", help="禁用 API 配置和调用入口")
    p.add_argument("--open", action="store_true", help="在本机浏览器打开一次性发起人会话")
    args = p.parse_args(argv)
    app = Console(args.root, json.loads(Path(args.fixture).read_text(encoding="utf-8")), args.enable_codex, enable_api=not args.disable_api)
    server = Server(app, args.port)
    access = {role: server.origin + "/#launch=" + app.ticket(role) for role in ("board", "observer")}
    path = app.root / "local-access.json"
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(encoded(access))
    print(f"工作台：{server.origin}；本机一次性会话链接（10 分钟有效）保存在 {path}", flush=True)
    if args.open:
        webbrowser.open(access["board"])
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()


if __name__ == "__main__":
    main()
