"""Private browser host: explicit local New API/model double, never a supplier."""
import argparse
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_union.console import Console
from ai_union.engine import encoded
from ai_union.server import Server
from tests.novel_browser_host import NovelProvider
from tests.support import CHARTER, RESOURCES


class GatewayDouble(NovelProvider):
    def do_GET(self):
        raw = encoded({'success': True, 'data': {'version': 'local-double-v1'}}).encode()
        self.send_response(200 if self.path == '/api/status' else 404)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers(); self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--root', required=True)
    args = parser.parse_args()
    app = Console(args.root)
    board = app.new_session('board')
    receipt = app.command(board, dict(id='gateway-browser-create', organization_id=None, base_version=None, kind='create',
        data=dict(name='网关受控验收公司',goal='只验证网关连接与模拟工具往返，不执行真实业务',board_name='local browser test',charter=CHARTER,resources=RESOURCES)))
    server = Server(app)
    provider = ThreadingHTTPServer(('127.0.0.1', 0), GatewayDouble)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (server, provider)]
    for thread in threads: thread.start()
    print(encoded(dict(origin=server.origin, organization_id=receipt['organization_id'],
        admin_url=server.origin+'/#launch='+app.ticket('board',platform_admin=True),
        board_url=server.origin+'/#launch='+app.ticket('board'),
        provider_url=f'http://127.0.0.1:{provider.server_port}')),flush=True)
    try:
        for line in sys.stdin:
            if json.loads(line).get('op') == 'stop': break
    finally:
        for s in (server,provider): s.shutdown(); s.server_close()
        for thread in threads: thread.join()
        app.close()


if __name__ == '__main__': main()
