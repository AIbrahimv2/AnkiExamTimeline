"""The editor's commands (src/bridge.py), with no Anki: plain Python 3.

    python3 tests/test_bridge.py
"""

import importlib.util
import json
import os
import unittest
from datetime import date

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
spec = importlib.util.spec_from_file_location("exam_timeline_bridge", os.path.join(SRC, "bridge.py"))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

TODAY = date(2026, 11, 9)


class MemoryStore:
    def __init__(self, exams=None, **other):
        self.cfg = {"exams": exams or [], **other}
        self.saves = 0

    def load(self):
        return json.loads(json.dumps(self.cfg))

    def save(self, cfg):
        self.saves += 1
        self.cfg = json.loads(json.dumps(cfg))


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore([{"id": 1, "name": "B&B Exam 3", "date": "2026-11-10"}], other_setting=True)
        self.changes = 0
        self.b = bridge.Bridge(self.store, on_change=self.changed, today=lambda: TODAY)

    def changed(self):
        self.changes += 1

    def call(self, cmd, **args):
        return self.b.handle(json.dumps({"cmd": cmd, **args}))

    def test_load(self):
        r = self.call("load")
        self.assertEqual(r, {"exams": self.store.cfg["exams"], "today": "2026-11-09"})
        self.assertEqual(self.changes, 0)

    def test_add(self):
        r = self.call("add", name="  USMLE   Step 1 ", date="2027-01-22")
        new = [e for e in r["exams"] if e["id"] == r["added"]]
        self.assertEqual(new, [{"id": r["added"], "name": "USMLE Step 1", "date": "2027-01-22"}])
        self.assertEqual(len(self.store.cfg["exams"]), 2)
        self.assertTrue(self.store.cfg["other_setting"], "other config is kept")
        self.assertEqual(self.changes, 1, "the deck screen is told")

    def test_add_twice_quickly_gets_two_ids(self):
        a = self.call("add", name="A", date="2027-01-01")["added"]
        b = self.call("add", name="B", date="2027-01-02")["added"]
        self.assertNotEqual(a, b)

    def test_long_name_is_cut(self):
        r = self.call("add", name="x" * 200, date="2027-01-01")
        self.assertEqual(len(next(e for e in r["exams"] if e["id"] == r["added"])["name"]), bridge.MAX_NAME)

    def test_bad_input(self):
        self.assertEqual(self.call("add", name="  ", date="2027-01-01"), {"error": "Give the exam a name."})
        self.assertEqual(self.call("add", name="A", date=""), {"error": "Pick a date for the exam."})
        self.assertEqual(self.call("add", name="A", date="2026-11-31"), {"error": "Pick a date for the exam."})
        self.assertEqual(self.call("add", name="A", date="Nov 20"), {"error": "Pick a date for the exam."})
        self.assertEqual(self.call("nope"), {"error": "Unknown command: nope"})
        self.assertEqual(self.b.handle("not json")["error"][:6], "Expect")
        self.assertEqual(self.store.saves, 0, "nothing is saved")

    def test_update(self):
        r = self.call("update", id=1, name="B&B Exam 3 (moved)", date="2026-11-12")
        self.assertEqual(r["exams"], [{"id": 1, "name": "B&B Exam 3 (moved)", "date": "2026-11-12"}])
        self.assertEqual(self.call("update", id="1", name="Same id as text", date="2026-11-12")["exams"][0]["name"],
                         "Same id as text", "ids match as text, as the page may send either")
        self.assertIn("error", self.call("update", id=99, name="A", date="2026-11-12"))

    def test_remove(self):
        self.assertEqual(self.call("remove", id="1")["exams"], [], "ids match as text")
        self.assertEqual(self.changes, 1)

    def test_remove_missing_is_harmless(self):
        self.assertEqual(len(self.call("remove", id=99)["exams"]), 1)

    def test_odd_config(self):
        """Hand-edited config: entries that aren't exams are skipped, not fatal."""
        self.store.cfg["exams"].append("not an exam")
        self.assertEqual(len(self.call("load")["exams"]), 1)


if __name__ == "__main__":
    unittest.main()
