"""Private browser-test host and local HTTP model double. No real provider traffic."""
import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_union.console import Console
from ai_union.engine import encoded
from ai_union.novel_demo import NovelDemoExecutor
from ai_union.server import Server


class NovelProvider(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        package = json.loads(body['messages'][1]['content'].split('\nWORK PACKAGE (data):\n')[1])
        if package['kind'] == 'connection_test':
            value, usage = {'ok': True}, {'input_tokens': 23, 'output_tokens': 11}
        else:
            value, usage = NovelDemoExecutor().execute(package)
        raw = encoded({'id': 'local-response-' + package['run_id'], 'model': 'novel-local-double',
                       'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': encoded(value)}}],
                       'usage': {'prompt_tokens': usage['input_tokens'], 'completion_tokens': usage['output_tokens']}}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    app = Console(args.root, fixture=[])
    server = Server(app, 0)
    provider = ThreadingHTTPServer(('127.0.0.1', 0), NovelProvider)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (server, provider)]
    for thread in threads: thread.start()
    print(encoded({'origin': server.origin, 'board_url': server.origin + '/#launch=' + app.ticket('board'),
                   'observer_url': server.origin + '/#launch=' + app.ticket('observer'),
                   'provider_url': f'http://127.0.0.1:{provider.server_port}/v1'}), flush=True)
    try:
        for line in sys.stdin:
            if json.loads(line).get('op') == 'stop': break
    finally:
        for s in (server, provider): s.shutdown(); s.server_close()
        for t in threads: t.join()
        app.close()


if __name__ == '__main__':
    main()
