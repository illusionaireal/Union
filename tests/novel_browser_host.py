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
from tests.api_messages import fixture_message, historical_package
from tests.test_agent_conversation import PLAN, tool


def harness_message(body, package):
    """Explicit staged outputs for browser Harness acceptance, never a real model."""
    calls = [c for m in body['messages'] for c in m.get('tool_calls', [])]
    names = [c['function']['name'] for c in calls]
    if package.get('actor') == 'bootstrap':
        if 'prepare_member' in names:
            return tool('activate_organization', {})
        items = [('prepare_member', m) for m in PLAN['members']] + [('arrange_work', t) for t in PLAN['tasks']] + [('configure_bootstrap', {'coordinator': PLAN['coordinator']})]
        result = {'role': 'assistant', 'content': '保存本地测试草案。', 'tool_calls': []}
        for index, (name, args) in enumerate(items):
            call = tool(name, args)['tool_calls'][0]
            call['id'] = f'draft-{index}'
            result['tool_calls'].append(call)
        return result
    if package['kind'] == 'work' and not package['context']['task']['dependencies']:
        if 'read_file' in names:
            return {'role': 'assistant', 'content': '# 资料交付\n这是从虚拟工作区继续完善的本地测试资料。'}
        if 'write_file' in names:
            return tool('read_file', {'file_path': '/draft.md'})
        return tool('write_file', {'file_path': '/draft.md', 'content': '本地测试资料，等待下一轮读取并交付。'})
    return {'role': 'assistant', 'content': '# 成稿交付\n第二名成员使用前一成员的资料完成本地测试正文。'}


class NovelProvider(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        package = json.loads(body['messages'][1]['content'].split('\nWORK PACKAGE (data):\n')[1])
        # Negative-path browser scenario, isolated to this explicit test host.
        if body['model'] == 'reject-response-format':
            raw = encoded({'error': {'param': 'response_format', 'message': 'unsupported ' + self.headers.get('Authorization', '')}}).encode()
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if body['model'] == 'harness-draft-double' and package['kind'] != 'connection_test':
            value, usage = None, {'input_tokens': 20, 'output_tokens': 10}
        elif package['kind'] == 'connection_test':
            value, usage = {'ok': True}, {'input_tokens': 23, 'output_tokens': 11}
        else:
            value, usage = NovelDemoExecutor().execute(historical_package(package, getattr(self.server, 'bootstrap', None)))
        message = harness_message(body, package) if value is None else fixture_message(package, value, getattr(self.server, 'bootstrap', None))
        probe_tools = [t['function']['name'] for t in body.get('tools', [])]
        if 'connection_echo' in probe_tools:
            message = {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'probe', 'type': 'function', 'function': {'name': 'connection_echo', 'arguments': '{}'}}]}
        elif package['kind'] == 'connection_test' and any(m['role'] == 'tool' for m in body['messages']):
            message = {'role': 'assistant', 'content': next(m['content'] for m in body['messages'] if m['role'] == 'tool')}
        if package.get('actor') == 'bootstrap' and value is not None:
            self.server.bootstrap = value
        raw = encoded({'id': 'explicit-local-response', 'model': 'novel-local-double',
                       'choices': [{'finish_reason': 'tool_calls' if message.get('tool_calls') else 'stop', 'message': message}],
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
