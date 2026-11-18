import unittest
from datetime import date

from signal_lab.explain import explain_changes
from signal_lab.ranking import Weighting
from signal_lab.records import Observation

WEIGHTING = Weighting(
    "均衡",
    {"reporting": 1.0, "regional-coverage": 1.0, "audience-questions": 1.0},
    min_support=0.5,
)


class ExplainChangesTests(unittest.TestCase):
    def test_backfill_from_new_source_is_called_out(self):
        old = [
            Observation("a", "desk", date(2026, 11, 1), "alpha", 2,
                        signal="reporting"),
        ]
        new = old + [
            Observation("b", "wire", date(2026, 11, 2), "alpha", 5,
                        region="south-asia", signal="regional-coverage"),
        ]
        (change,) = explain_changes(old, new, WEIGHTING)
        self.assertEqual(change.driver, "backfill")
        self.assertEqual(change.sources_added, ("wire",))
        self.assertEqual(change.regions_added, ("south-asia",))
        self.assertEqual(change.value_from_added, 5)
        # 旧版支撑度 1/3 为待补，新版 2/3 进入排序。
        self.assertIsNone(change.old_rank)
        self.assertEqual(change.new_rank, 1)

    def test_revision_is_distinguished_from_backfill(self):
        old = [
            Observation("a", "desk", date(2026, 11, 1), "alpha", 2,
                        signal="reporting"),
            Observation("b", "wire", date(2026, 11, 1), "alpha", 2,
                        signal="regional-coverage"),
        ]
        new = [
            Observation("a", "desk", date(2026, 11, 1), "alpha", 9,
                        signal="reporting"),
            Observation("b", "wire", date(2026, 11, 1), "alpha", 2,
                        signal="regional-coverage"),
        ]
        (change,) = explain_changes(old, new, WEIGHTING)
        self.assertEqual(change.driver, "revision")
        self.assertEqual(change.value_from_revisions, 7)
        self.assertEqual(change.added_observations, 0)
        self.assertEqual(change.sources_added, ())

    def test_same_source_growth_reads_as_signal_change(self):
        old = [
            Observation("a", "desk", date(2026, 11, 1), "alpha", 2,
                        signal="reporting"),
            Observation("b", "wire", date(2026, 11, 1), "alpha", 2,
                        signal="regional-coverage"),
        ]
        new = old + [
            Observation("c", "desk", date(2026, 11, 8), "alpha", 4,
                        signal="reporting"),
        ]
        (change,) = explain_changes(old, new, WEIGHTING)
        self.assertEqual(change.driver, "signal-change")
        self.assertEqual(change.sources_added, ())


if __name__ == "__main__":
    unittest.main()
