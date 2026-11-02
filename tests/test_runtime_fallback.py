"""Runtime fallback: only a definite failure may move to another connection."""
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ai_union.model_api import APIExecutor


class Double(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        self.server.seen.append({"body": json.loads(raw), "authorization": self.headers.get("Authorization")})
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if self.server.status == 200:
            reply = {"id": "reply-1", "model": self.server.model,
                     "choices": [{"finish_reason": "stop",
                                  "message": {"role": "assistant", "content": "ok"}}],
                     "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
            self.wfile.write(json.dumps(reply).encode())
        else:
            self.wfile.write(b'{"error": {"message": "denied"}}')


class RuntimeFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.servers = []

    def serve(self, status=200, model="served-model"):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Double)
        server.daemon_threads = True
        server.seen, server.status, server.model = [], status, model
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.servers.append(server)
        return server

    def connection(self, name, port, model):
        return {"id": name, "revision": 1, "api_key": name + "-key",
                "config": {"name": name, "base_url": f"http://127.0.0.1:{port}/v1", "model": model,
                           "token_limit_field": "max_tokens", "max_output_tokens": 512,
                           "timeout_seconds": 5, "enabled": True}}

    def job(self, seconds=5):
        return {"folder": Path(self.temp.name), "started": time.monotonic(),
                "deadline": time.monotonic() + seconds, "done": threading.Event(),
                "cancelled": threading.Event(), "response": None, "error": None, "connection": None}

    def body(self):
        return {"model": "primary-model", "stream": False, "max_tokens": 64,
                "messages": [{"role": "user", "content": "hello"}]}

    def test_authentication_failure_moves_to_the_fallback(self):
        primary = self.serve(status=401)
        secondary = self.serve(status=200, model="secondary-model")
        executor = APIExecutor(self.temp.name, self.connection("primary", primary.server_port, "primary-model"),
                               fallbacks=[self.connection("secondary", secondary.server_port, "secondary-model")])
        job = self.job()
        executor._request(job, self.body())
        self.assertIsNone(job["error"])
        self.assertIsNotNone(job["response"])
        self.assertEqual(job["fallback_from"], "primary")
        self.assertEqual(job["connection_used"]["id"], "secondary")
        self.assertEqual(secondary.seen[0]["authorization"], "Bearer secondary-key")
        self.assertEqual(secondary.seen[0]["body"]["model"], "secondary-model")
        self.assertEqual(secondary.seen[0]["body"]["max_tokens"], 512)

    def test_rate_limit_moves_to_the_fallback(self):
        primary = self.serve(status=429)
        secondary = self.serve(status=200)
        executor = APIExecutor(self.temp.name, self.connection("primary", primary.server_port, "primary-model"),
                               fallbacks=[self.connection("secondary", secondary.server_port, "secondary-model")])
        job = self.job()
        executor._request(job, self.body())
        self.assertEqual(job["fallback_from"], "primary")
        self.assertIsNone(job["error"])

    def test_server_error_never_moves(self):
        primary = self.serve(status=500)
        secondary = self.serve(status=200)
        executor = APIExecutor(self.temp.name, self.connection("primary", primary.server_port, "primary-model"),
                               fallbacks=[self.connection("secondary", secondary.server_port, "secondary-model")])
        job = self.job()
        executor._request(job, self.body())
        self.assertIsNotNone(job["error"])
        self.assertTrue(job["error"].unknown)
        self.assertEqual(secondary.seen, [])
        self.assertNotIn("fallback_from", job)

    def dead_port(self):
        import socket
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def test_refused_connection_moves_to_the_fallback(self):
        secondary = self.serve(status=200)
        executor = APIExecutor(self.temp.name, self.connection("primary", self.dead_port(), "primary-model"),
                               fallbacks=[self.connection("secondary", secondary.server_port, "secondary-model")])
        job = self.job()
        executor._request(job, self.body())
        self.assertEqual(job["fallback_from"], "primary")
        self.assertIsNotNone(job["response"])

    def test_without_a_fallback_the_failure_is_reported(self):
        primary = self.serve(status=401)
        executor = APIExecutor(self.temp.name, self.connection("primary", primary.server_port, "primary-model"))
        job = self.job()
        executor._request(job, self.body())
        self.assertIsNotNone(job["error"])
        self.assertFalse(job["error"].unknown)
        self.assertEqual(job["error"].failure["code"], "api_authentication")

    def test_metadata_lists_the_chain_without_credentials(self):
        primary = self.serve()
        secondary = self.serve()
        executor = APIExecutor(self.temp.name, self.connection("primary", primary.server_port, "primary-model"),
                               fallbacks=[self.connection("secondary", secondary.server_port, "secondary-model")])
        self.assertEqual(executor.metadata["fallbacks"], ["secondary"])
        self.assertNotIn("secondary-key", json.dumps(executor.metadata))

    def test_unknown_fallback_receipt_identifies_the_actual_endpoint(self):
        primary=self.serve(status=401);secondary=self.serve(status=500)
        executor=APIExecutor(self.temp.name,self.connection('primary',primary.server_port,'primary-model'),fallbacks=[self.connection('secondary',secondary.server_port,'secondary-model')])
        job=self.job();executor._request(job,self.body());executor.jobs['probe']=job
        from ai_union.executor import ExecutionFailure
        with self.assertRaises(ExecutionFailure) as caught:executor.result('probe')
        self.assertTrue(caught.exception.unknown)
        self.assertEqual(caught.exception.usage['connection_id'],'secondary')
        self.assertEqual(caught.exception.usage['requested_model'],'secondary-model')

    def test_cached_fallback_key_cannot_appear_in_response_or_result_file(self):
        primary=self.serve(status=401);secondary=self.serve(model='secondary-key')
        executor=APIExecutor(self.temp.name,self.connection('primary',primary.server_port,'primary-model'),fallbacks=[self.connection('secondary',secondary.server_port,'secondary-model')])
        job=self.job();job['package']={'kind':'connection_test'};executor._request(job,self.body());executor.jobs['probe']=job
        from ai_union.executor import ExecutionFailure
        with self.assertRaises(ExecutionFailure) as caught:executor.result('probe')
        self.assertEqual(caught.exception.failure['code'],'api_secret_response')
        self.assertFalse((Path(self.temp.name)/'result.json').exists())


if __name__ == "__main__":
    unittest.main()
