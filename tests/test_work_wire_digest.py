"""Actual modeld canonical oracle, with no runtime Node dependency in Python core."""
import json
import math
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import unittest

from ai_union.adapters.work_execution_store import wire_digest
from ai_union.errors import Rejected
from tests.test_work_recovery import WorkRecoveryTests

NODE = os.environ.get("UNION_TEST_NODE") or shutil.which("node")


@unittest.skipUnless(NODE, "Node is required only for the actual modeld canonical test oracle")
class ModeldWireDigestOracleTests(unittest.TestCase):
    def oracle(self, value):
        source = (Path(__file__).resolve().parents[1] / "services/modeld/src/journal.ts").read_text(encoding="utf-8")
        start = source.index("export function canonical(")
        end = source.index("\nconst digest", start)
        canonical = source[start:end].replace("export function canonical(value: any): string",
                                              "function canonical(value)")
        script = canonical + "\nconst v=JSON.parse(require('node:fs').readFileSync(0,'utf8'));" + \
            "process.stdout.write(require('node:crypto').createHash('sha256').update(canonical(v)).digest('hex'));"
        completed = subprocess.run([NODE, "-e", script], input=json.dumps(value, ensure_ascii=True, allow_nan=False),
                                   text=True, encoding="utf-8", capture_output=True, timeout=10, check=True)
        return completed.stdout

    def test_all_native_number_boundaries_match_actual_modeld_after_wire_json_parse(self):
        numbers = [1.0, -0.0, 1e-7, 1e-6, 1e20, 1e21, -1e-7, -1e21, 0.5,
                   sys.float_info.max, -sys.float_info.max, sys.float_info.min,
                   math.nextafter(0, 1), -math.nextafter(0, 1),
                   2 ** 53 - 1, 2 ** 53, 2 ** 53 + 1, 2 ** 53 + 3, 2 ** 64 - 1,
                   1000000000000000128, 1.2345678901234567, 333333333.3333333]
        value = {"messages": [{"role": "assistant", "_native": {"message": {
            "role": "assistant", "content": [{"type": "reasoning", "text": "bounded native fact",
                                               "providerMetadata": {"numbers": numbers}}]}}}]}
        self.assertEqual(wire_digest(value), self.oracle(value))

    def test_utf16_key_order_and_json_string_escaping_match_actual_modeld(self):
        value = {"\ue000": "BMP", "\U00010000": "astral before BMP under UTF16", "\U0001f600": "emoji",
                 "controls": "\x00\b\t\n\f\r\x1f\"\\/中文\u2028\u2029"}
        self.assertEqual(wire_digest(value), self.oracle(value))

    def test_seeded_finite_binary64_values_match_actual_modeld(self):
        randomizer = random.Random(92)
        numbers = []
        while len(numbers) < 512:
            value = struct.unpack("!d", randomizer.getrandbits(64).to_bytes(8, "big"))[0]
            if math.isfinite(value): numbers.append(value)
        self.assertEqual(wire_digest({"native": numbers}), self.oracle({"native": numbers}))


class WireDigestInvalidInputTests(unittest.TestCase):
    def rejected(self, value):
        try:
            wire_digest(value)
        except Exception as error:
            self.assertIsInstance(error, Rejected, "unsupported wire values need an explicit pre-dispatch refusal")
        else:
            self.fail("unsupported wire value was accepted")

    def test_non_finite_or_unrepresentable_wire_numbers_are_rejected(self):
        for value in (math.inf, -math.inf, math.nan, 10 ** 400):
            with self.subTest(value=type(value).__name__): self.rejected({"native": value})

    def test_isolated_surrogates_non_string_keys_and_non_json_values_are_rejected(self):
        for value in ({"native": "\ud800"}, {"\udfff": "invalid UTF8 key"}, {1: "non-JSON key"}, {"native": b"bytes"}):
            with self.subTest(kind=type(value).__name__): self.rejected(value)

    def test_cyclic_or_excessively_nested_wire_input_is_rejected(self):
        cyclic = []; cyclic.append(cyclic)
        self.rejected(cyclic)
        value = None
        for _ in range(100): value = [value]
        self.rejected(value)


class WorkWireDigestReservationTests(WorkRecoveryTests):
    def test_invalid_native_wire_rolls_back_same_sqlite_reservation_before_post(self):
        request = self.arrange()
        client = self.wire()
        from ai_union.application import work_dispatch
        from ai_union.domain import work
        for unsupported in ("\ud800", math.inf, 10 ** 400):
            before = self.dump()
            state = self.state()
            with self.assertRaises(Rejected):
                with self.app.work.store.transaction(self.directory) as cx:
                    plan = work.step_plan(state, state["charter"], "work-overview", self.app.instance)
                    plan["sources"] = []
                    plan["messages"].append({"role": "assistant", "_native": {"value": unsupported}})
                    work_dispatch.prepare(self.app.work.store, cx, state, request, self.principal, plan,
                                           self.app.instance, self.app.work.transport)
            self.assertEqual(self.dump(), before)
            self.assertEqual(client.posts, [])


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(ModeldWireDigestOracleTests)
    suite.addTests(loader.loadTestsFromTestCase(WireDigestInvalidInputTests))
    suite.addTest(WorkWireDigestReservationTests("test_invalid_native_wire_rolls_back_same_sqlite_reservation_before_post"))
    return suite
