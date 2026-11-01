"""Deterministic catalog tests: schema, tri-state answers and snapshot loading.

These tests hold no credentials and make no network calls.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from ai_union.catalog import EMPTY, SCHEMA_VERSION, Catalog, load, validate_record
from ai_union.engine import Rejected

RECORD = {"provider": "example", "model": "example-chat-1", "context_window": 128000,
          "max_output_tokens": 8192, "tool_call": True, "reasoning": False,
          "input_modalities": ["text", "image"], "cost": {"input": 1.5, "output": 6}}


class RecordTests(unittest.TestCase):
    def test_accepts_complete_record(self):
        self.assertEqual(validate_record(dict(RECORD))["model"], "example-chat-1")

    def test_requires_provider_and_model(self):
        for missing in ("provider", "model"):
            with self.subTest(missing=missing), self.assertRaises(Rejected):
                validate_record({k: v for k, v in RECORD.items() if k != missing})

    def test_rejects_credentials_in_catalog(self):
        for field in ("api_key", "access_token", "password", "Authorization"):
            with self.subTest(field=field), self.assertRaises(Rejected):
                validate_record(dict(RECORD, **{field: "x"}))

    def test_rejects_output_larger_than_context(self):
        with self.assertRaises(Rejected):
            validate_record(dict(RECORD, context_window=4096, max_output_tokens=8192))

    def test_rejects_unsupported_modality(self):
        with self.assertRaises(Rejected):
            validate_record(dict(RECORD, input_modalities=["text", "hologram"]))

    def test_rejects_negative_cost(self):
        with self.assertRaises(Rejected):
            validate_record(dict(RECORD, cost={"input": -1}))

    def test_rejects_unknown_field(self):
        with self.assertRaises(Rejected):
            validate_record(dict(RECORD, verified=True))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        other = dict(RECORD, provider="second", model="example-chat-1")
        self.catalog = Catalog([RECORD, other, dict(RECORD, model="solo-1")])

    def test_lookup_by_provider_and_model(self):
        self.assertEqual(self.catalog.get("example-chat-1", "example")["provider"], "example")
        self.assertEqual(self.catalog.get("example-chat-1", "SECOND")["provider"], "second")

    def test_bare_model_is_unknown_when_ambiguous(self):
        self.assertIsNone(self.catalog.get("example-chat-1"))
        self.assertEqual(self.catalog.get("solo-1")["provider"], "example")

    def test_unknown_model_stays_unknown(self):
        self.assertIsNone(self.catalog.get("never-heard-of-it", "example"))
        self.assertIsNone(self.catalog.get(None), "unknown model id")

    def test_capability_is_tri_state(self):
        self.assertTrue(self.catalog.capability("solo-1", "tool_call"))
        self.assertFalse(self.catalog.capability("solo-1", "reasoning"))
        self.assertTrue(self.catalog.capability("solo-1", "image"))
        self.assertFalse(self.catalog.capability("solo-1", "audio"))
        self.assertIsNone(self.catalog.capability("absent", "tool_call"))
        self.assertIsNone(self.catalog.capability("solo-1", "unrelated"))

    def test_capability_unstated_is_unknown(self):
        partial = Catalog([{"provider": "p", "model": "m"}])
        self.assertIsNone(partial.capability("m", "tool_call"))

    def test_duplicate_provider_model_rejected(self):
        with self.assertRaises(Rejected):
            Catalog([RECORD, dict(RECORD)])

    def test_provider_models_sorted(self):
        self.assertEqual(Catalog([RECORD]).provider_models("EXAMPLE"), ["example-chat-1"])

    def test_records_are_returned_as_copies(self):
        found = self.catalog.get("solo-1")
        found["model"] = "tampered"
        self.assertEqual(self.catalog.get("solo-1")["model"], "solo-1")


class LoadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "catalog.json"
        self.saved = os.environ.pop("UNION_MODEL_CATALOG", None)
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ.pop("UNION_MODEL_CATALOG", None)
        if self.saved is not None:
            os.environ["UNION_MODEL_CATALOG"] = self.saved

    def write(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")

    def test_no_snapshot_means_empty_catalog(self):
        self.assertIs(load(), EMPTY)
        self.assertIsNone(EMPTY.get("solo-1"))

    def test_loads_explicit_path(self):
        self.write({"version": SCHEMA_VERSION, "models": [RECORD]})
        self.assertEqual(len(load(self.path)), 1)

    def test_loads_from_environment(self):
        self.write({"version": SCHEMA_VERSION, "models": [RECORD]})
        os.environ["UNION_MODEL_CATALOG"] = str(self.path)
        self.assertEqual(load().get("example-chat-1", "example")["provider"], "example")

    def test_missing_file_is_rejected(self):
        with self.assertRaises(Rejected):
            load(Path(self.folder.name) / "absent.json")

    def test_malformed_snapshot_is_rejected(self):
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(Rejected):
            load(self.path)

    def test_unexpected_shape_is_rejected(self):
        self.write({"version": SCHEMA_VERSION, "models": [], "extra": True})
        with self.assertRaises(Rejected):
            load(self.path)

    def test_unsupported_version_is_rejected(self):
        self.write({"version": 99, "models": []})
        with self.assertRaises(Rejected):
            load(self.path)

    def test_unreadable_snapshot_is_unknown_but_not_fatal(self):
        from ai_union.catalog import metadata
        os.environ["UNION_MODEL_CATALOG"] = str(Path(self.folder.name) / "absent.json")
        self.assertIsNone(metadata("solo-1"))
        with self.assertRaises(Rejected):
            load()


class ConnectionMetadataTests(unittest.TestCase):
    """The console only ever sees metadata, never the credential."""

    CONFIG = {"name": "样例连接", "base_url": "https://example.invalid/v1", "model": "solo-1",
              "token_limit_field": "max_tokens", "max_output_tokens": 8192,
              "timeout_seconds": 30, "enabled": True}

    def setUp(self):
        self.saved = os.environ.pop("UNION_MODEL_CATALOG", None)
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ.pop("UNION_MODEL_CATALOG", None)
        if self.saved is not None:
            os.environ["UNION_MODEL_CATALOG"] = self.saved

    def row(self):
        return {"id": "primary", "revision": 3, "config": json.dumps(self.CONFIG),
                "api_key": "secret-value", "updated_at": "2026-11-01T00:00:00+00:00"}

    def test_unknown_model_reports_explicit_null(self):
        from ai_union.model_api import public_connection
        result = public_connection(self.row())
        self.assertIsNone(result["catalog"])
        self.assertTrue(result["has_api_key"])
        self.assertNotIn("secret-value", json.dumps(result, ensure_ascii=False))

    def test_known_model_adds_catalog_metadata(self):
        from ai_union.model_api import public_connection
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / "catalog.json"
            snapshot.write_text(json.dumps({"version": SCHEMA_VERSION,
                                            "models": [{"provider": "p", "model": "solo-1",
                                                        "context_window": 128000, "tool_call": True}]}),
                                encoding="utf-8")
            os.environ["UNION_MODEL_CATALOG"] = str(snapshot)
            result = public_connection(self.row())
        self.assertEqual(result["catalog"]["context_window"], 128000)
        self.assertTrue(result["catalog"]["tool_call"])
        self.assertNotIn("secret-value", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
