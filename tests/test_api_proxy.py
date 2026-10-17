"""Proxy selection and TLS boundaries; no external requests or actual credentials."""
import base64
import http.client
import os
import ssl
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from ai_union.model_api import api_connection


class APIProxyTests(unittest.TestCase):
    def test_https_uses_configured_connect_proxy_and_verifies_destination_tls(self):
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy.example:8080"}, clear=True):
            connection = api_connection(urlsplit("https://provider.example:8443/api/v1"), 7)
        self.addCleanup(connection.close)
        self.assertEqual((connection.host, connection.port), ("proxy.example", 8080))
        self.assertEqual((connection._tunnel_host, connection._tunnel_port), ("provider.example", 8443))
        self.assertNotIn("Authorization", connection._tunnel_headers)
        self.assertNotIn("Proxy-Authorization", connection._tunnel_headers)
        self.assertEqual(connection.timeout, 7)
        self.assertEqual(connection._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(connection._context.check_hostname)

    def test_no_proxy_and_unconfigured_hosts_use_direct_verified_https(self):
        for env in ({}, {"https_proxy": "http://proxy.example:8080", "no_proxy": "provider.example"}):
            with self.subTest(env=list(env)), patch.dict(os.environ, env, clear=True):
                connection = api_connection(urlsplit("https://provider.example/v1"), 4)
            connection.close()
            self.assertEqual(connection.host, "provider.example")
            self.assertIsNone(connection._tunnel_host)
            self.assertTrue(connection._context.check_hostname)

    def test_local_http_doubles_never_receive_an_external_proxy(self):
        with patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.example:8080", "HTTPS_PROXY": "http://proxy.example:8080"}, clear=True):
            connection = api_connection(urlsplit("http://127.0.0.1:12345/v1"), 3)
        self.addCleanup(connection.close)
        self.assertIsInstance(connection, http.client.HTTPConnection)
        self.assertEqual((connection.host, connection.port), ("127.0.0.1", 12345))
        self.assertIsNone(connection._tunnel_host)

    def test_proxy_credentials_are_scoped_only_to_connect(self):
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://user:escaped%40password@proxy.example:8080"}, clear=True):
            connection = api_connection(urlsplit("https://provider.example/v1"), 5)
        self.addCleanup(connection.close)
        expected = "Basic " + base64.b64encode(b"user:escaped@password").decode()
        self.assertEqual(connection._tunnel_headers["Proxy-Authorization"], expected)
        self.assertNotIn("Authorization", connection._tunnel_headers)
        self.assertEqual(connection.host, "proxy.example")
        self.assertEqual(connection._tunnel_host, "provider.example")

    def test_unsupported_proxy_is_rejected_without_direct_fallback(self):
        for proxy in ("socks5://proxy.example:1080", "http://proxy.example:invalid", "http://proxy.example/private"):
            with self.subTest(proxy=proxy), patch.dict(os.environ, {"HTTPS_PROXY": proxy}, clear=True):
                with self.assertRaisesRegex(OSError, "proxy configuration"):
                    api_connection(urlsplit("https://provider.example/v1"), 5)
