import unittest
from datetime import date

from signal_lab.dossier import build_dossiers
from signal_lab.records import Observation


class DossierTests(unittest.TestCase):
    def test_groups_signals_with_coverage(self):
        rows = [
            Observation("a", "desk-1", date(2026, 11, 1), "topic", 2,
                        region="east-asia", signal="reporting"),
            Observation("b", "desk-2", date(2026, 11, 3), "topic", 3,
                        region="global", signal="reporting"),
            Observation("c", "inbox", date(2026, 11, 5), "topic", 4,
                        region="global", signal="audience-questions"),
        ]
        (dossier,) = build_dossiers(rows)
        self.assertEqual(dossier.topic, "topic")
        self.assertEqual(dossier.signal_names, ("audience-questions", "reporting"))
        reporting = dossier.signals[1]
        self.assertEqual(reporting.total, 5)
        self.assertEqual(reporting.observations, 2)
        self.assertEqual(reporting.source_ids, ("desk-1", "desk-2"))
        self.assertEqual(reporting.regions, ("east-asia", "global"))
        self.assertEqual(reporting.first_observed, "2026-11-01")
        self.assertEqual(reporting.last_observed, "2026-11-03")

    def test_signal_total_returns_none_for_missing_signal(self):
        rows = [Observation("a", "desk", date(2026, 11, 1), "topic", 2)]
        (dossier,) = build_dossiers(rows)
        self.assertEqual(dossier.signal_total("reporting"), 2)
        self.assertIsNone(dossier.signal_total("audience-questions"))


if __name__ == "__main__":
    unittest.main()
