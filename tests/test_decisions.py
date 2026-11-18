import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from signal_lab.decisions import DecisionLedger, snapshot_hash
from signal_lab.ranking import Weighting
from signal_lab.records import Observation

WEIGHTING = Weighting(
    "均衡", {"reporting": 1.0, "audience-questions": 1.0}, min_support=0.5
)
ROWS = [
    Observation("a", "desk", date(2026, 11, 1), "alpha", 4, signal="reporting"),
    Observation("b", "inbox", date(2026, 11, 2), "alpha", 6,
                signal="audience-questions"),
    Observation("c", "desk", date(2026, 11, 3), "beta", 3, signal="reporting"),
]


class LedgerTests(unittest.TestCase):
    def test_record_persists_snapshot_weighting_and_rationale(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DecisionLedger(tmp)
            record = ledger.record("2026-11", "2026-11", WEIGHTING, ROWS,
                                   selected=("alpha",), rationale="受众提问集中")
            self.assertEqual(record.snapshot, snapshot_hash(ROWS))
            loaded = ledger.get("2026-11")
            self.assertEqual(loaded.rationale, "受众提问集中")
            self.assertEqual(loaded.selected, ("alpha",))
            self.assertEqual(loaded.weighting, WEIGHTING)
            self.assertEqual([e["topic"] for e in loaded.ranked], ["alpha", "beta"])

    def test_ledger_is_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DecisionLedger(tmp)
            ledger.record("2026-11", "2026-11", WEIGHTING, ROWS, (), "首次")
            with self.assertRaises(FileExistsError):
                ledger.record("2026-11", "2026-11", WEIGHTING, ROWS, (), "改写")

    def test_decision_id_must_be_filename_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DecisionLedger(tmp)
            with self.assertRaises(ValueError):
                ledger.record("../escape", "2026-11", WEIGHTING, ROWS, (), "x")

    def test_verify_passes_for_untouched_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DecisionLedger(tmp)
            ledger.record("2026-11", "2026-11", WEIGHTING, ROWS, (), "首次")
            result = ledger.verify("2026-11")
            self.assertTrue(result.ok)
            self.assertEqual(result.problems, ())

    def test_verify_detects_tampered_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DecisionLedger(tmp)
            ledger.record("2026-11", "2026-11", WEIGHTING, ROWS, (), "首次")
            path = Path(tmp) / "2026-11.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["observations"][0]["value"] = 99
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = DecisionLedger(tmp).verify("2026-11")
            self.assertFalse(result.ok)
            self.assertTrue(any("快照" in problem for problem in result.problems))

    def test_recompute_pending_does_not_rewrite_archived_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = DecisionLedger(tmp)
            ledger.record("2026-11", "2026-11", WEIGHTING, ROWS, (), "首次")
            archived = (Path(tmp) / "2026-11.json").read_bytes()
            backfilled = ROWS + [
                Observation("d", "wire", date(2026, 11, 4), "beta", 8,
                            signal="audience-questions"),
            ]
            ranking = ledger.recompute_pending(backfilled)
            # 待决策名单按新数据重算，beta 反超。
            self.assertEqual([e.topic for e in ranking.ranked], ["beta", "alpha"])
            # 但已留档的决定一个字节都没有变。
            self.assertEqual((Path(tmp) / "2026-11.json").read_bytes(), archived)
            self.assertTrue(ledger.verify("2026-11").ok)


if __name__ == "__main__":
    unittest.main()
