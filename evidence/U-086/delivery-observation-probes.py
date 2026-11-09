"""Review only: python delivery-observation-probes.py <exact-source-export>.

Uses the unchanged PR42 fixture included in the author's candidate. No source edits,
real inference or implicit dispatch. Select only this class's two new probes.
"""
import importlib.util
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path
from urllib.parse import urlencode

source = Path(sys.argv[1]).resolve()
fixture = source / "evidence/U-086/cancel-delivery-probes.py"
spec = importlib.util.spec_from_file_location("delivery_fixture", fixture)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # fixture consumes the source argument and binds imports


class DeliveryObservationProbes(module.CancelDeliveryProbes):
    def test_original_post_replay_preserves_delivered_receipt_after_restart(self):
        value = self.scenario()
        original = value["post"]["value"]["receipt"]
        self.assertIs(original["cancel_accepted"], True)
        self.stop()
        self.start()
        status, replay, _ = self.request("/api/v1/work/commands", value["command"])
        self.assertEqual(status, 200, replay)
        self.assertEqual(replay["receipt"], original,
                         "same original POST must return the same durable delivery fact")
        self.assertEqual(len(value["cancellations"]), 1, "replay cannot resend cancellation")

    def test_changed_observation_with_unchanged_hash_is_not_accepted(self):
        value = self.scenario()
        directory, _ = self.app.governance.locate(self.au_id)
        with closing(sqlite3.connect(directory / "state.sqlite3")) as cx:
            row = cx.execute("SELECT observed FROM delivery_observations WHERE id=?",
                             (value["command"]["id"],)).fetchone()
            observed = json.loads(row[0])
            self.assertIs(observed["cancel_accepted"], True)
            observed.update(cancel_accepted=False, message="tampered observation")
            cx.execute("UPDATE delivery_observations SET observed=? WHERE id=?",
                       (json.dumps(observed), value["command"]["id"]))
            cx.commit()
        query = urlencode({"organization_id": self.au_id, "id": value["command"]["id"]})
        status, readback, _ = self.request("/api/v1/governance/receipts?" + query)
        self.assertNotEqual(status, 200,
                            "modified observation passed its stored hash: " + str(readback))


if __name__ == "__main__":
    names = [name for name in DeliveryObservationProbes.__dict__ if name.startswith("test_")]
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(DeliveryObservationProbes(name) for name in names))
    raise SystemExit(not result.wasSuccessful())
