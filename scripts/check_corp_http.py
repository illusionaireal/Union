"""Read-only HTTP acceptance for a freshly prepared company; no model requests."""
import argparse
import http.cookiejar
import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".union/ai-union-corp")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    access = json.loads((Path(args.root) / "local-access.json").read_text())
    url = urlsplit(access["board"])
    assert url.scheme == "http" and url.hostname == "127.0.0.1"
    origin = f"http://127.0.0.1:{url.port}"
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    def client():
        return build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(opener, path, *, method="GET", data=None, headers=None):
        req = Request(origin + path, method=method, data=data, headers={"Origin": origin, **(headers or {})})
        try:
            response = opener.open(req, timeout=5)
        except HTTPError as error:
            response = error
        return response.code, response.headers, response.read()

    board = client()
    code, headers, document = request(board, "/")
    check("Actual React document and CSP are served", code == 200 and b'type="module"' in document and "default-src 'none'" in headers.get("Content-Security-Policy", ""))
    for asset in re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', document):
        check("Built asset is served: " + asset.decode(), request(board, asset.decode())[0] == 200)
    check("Private host files are not static assets", request(board, "/board.key")[0] == 404)
    check("Snapshot requires a session", request(board, "/api/snapshot")[0] == 401)
    for role in ("board", "observer"):
        opener = board if role == "board" else client()
        ticket = parse_qs(urlsplit(access[role]).fragment)["launch"][0]
        code, _, data = request(opener, "/api/session", method="POST", data=b"", headers={"X-Union-Launch": ticket})
        session = json.loads(data)
        check(role + " launch exchanges for the correct role", code == 200 and session["role"] == role)
        check(role + " cannot reuse the one-time launch", request(opener, "/api/session", method="POST", data=b"", headers={"X-Union-Launch": ticket})[0] == 401)
        check(role + " has no fixture or Codex execution option", session["executors"] == ["api"])
        if role == "board":
            check("Actual company appears in the catalog", len(session["organizations"]) == 1 and session["organizations"][0]["name"] == "ai-union-corp")
            organization = session["organizations"][0]["id"]
            code, _, data = request(opener, "/api/snapshot?organization_id=" + organization)
            snapshot = json.loads(data)
            check("No startup, members or model calls are manufactured", code == 200 and snapshot["source"] == "not_run" and snapshot["budget"]["calls_reserved"] == 0 and not snapshot["organization"]["members"] and not snapshot["runs"])
            code, _, data = request(opener, "/api/model-connections?organization_id=" + organization)
            check("Missing model connection is represented accurately", code == 200 and json.loads(data)["connections"] == [])
        else:
            check("Observer command attempt is rejected", request(opener, "/api/commands", method="POST", data=b"{}", headers={"Content-Type": "application/json"})[0] == 403)
    for route in ("overview", "models", "members", "tasks", "artifacts", "activity", "resources", "settings"):
        check("SPA route is served: " + route, request(board, "/" + route)[0] == 200)
    result = {"status": "passed", "checks": checks, "model_calls": 0, "autonomous_operation_verified": False, "scope": "actual HTTP transport and React build assets; browser rendering not validated"}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "passed", "checks": len(checks), "model_calls": 0}))


if __name__ == "__main__":
    main()
