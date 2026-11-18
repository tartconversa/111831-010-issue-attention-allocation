import unittest
from datetime import date

from signal_lab.analysis import compare_periods
from signal_lab.records import Observation


class PeriodComparisonTests(unittest.TestCase):
    def test_compares_values_and_counts_observed_sources(self):
        rows = [
            Observation("a", "desk-1", date(2026, 11, 1), "topic", 2),
            Observation("b", "desk-2", date(2026, 11, 8), "topic", 3),
        ]
        result = compare_periods(rows, (2026, 11), (2026, 11))
        self.assertEqual(result["topic"]["start_value"], 5)
        self.assertEqual(result["topic"]["start_sources"], 2)

    def test_ignores_observations_outside_the_selected_periods(self):
        rows = [Observation("a", "desk", date(2026, 10, 1), "topic", 9)]
        result = compare_periods(rows, (2026, 11), (2026, 12))
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
