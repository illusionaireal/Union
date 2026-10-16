import json
import unittest

from ai_union.failures import issue, public_failure, runtime_failure


class PublicFailureTests(unittest.TestCase):
    def test_untrusted_diagnostic_text_and_parameters_never_cross_public_boundary(self):
        value = public_failure({"code": "api_request_rejected", "message": "private-secret", "recovery": "private-secret",
                                "parameter": "private-secret", "http_status": "private-secret", "rule": "private-secret"})
        self.assertEqual(value, issue("api_request_rejected"))
        self.assertNotIn("private-secret", json.dumps(value))
        self.assertIsNone(public_failure({"code": "private-secret"}))
        self.assertIsNone(public_failure({"code": []}))
        self.assertNotIn("parameter", public_failure({"code": "api_request_rejected", "parameter": {"private-secret": True}}))

    def test_private_runtime_errors_use_a_generic_hint(self):
        self.assertNotIn("private-secret", json.dumps(runtime_failure(ValueError("private-secret"))))
        self.assertIn("至少两名", runtime_failure(ValueError("启动需要至少两名可区分成员"))["rule"])
