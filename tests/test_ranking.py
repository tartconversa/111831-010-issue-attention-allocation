import unittest
from datetime import date

from signal_lab.dossier import build_dossiers
from signal_lab.ranking import Weighting, compare_weightings, rank_topics
from signal_lab.records import Observation

WEIGHTING = Weighting(
    "均衡",
    {"reporting": 1.0, "regional-coverage": 1.0, "audience-questions": 1.0},
    min_support=0.5,
)


def _rows():
    return [
        Observation("a", "desk", date(2026, 11, 1), "alpha", 4, signal="reporting"),
        Observation("b", "inbox", date(2026, 11, 2), "alpha", 6,
                    signal="audience-questions"),
        Observation("c", "desk", date(2026, 11, 3), "beta", 9, signal="reporting"),
        Observation("d", "wire", date(2026, 11, 4), "beta", 3,
                    signal="regional-coverage"),
        Observation("e", "inbox", date(2026, 11, 5), "gamma", 8,
                    signal="audience-questions"),
    ]


class RankTopicsTests(unittest.TestCase):
    def test_missing_signal_lowers_support_not_score(self):
        # alpha 缺 regional-coverage：支撑度降到 2/3，
        # 但分数只按已有信号平均，缺失信号不按零分计。
        ranking = rank_topics(build_dossiers(_rows()), WEIGHTING)
        alpha = next(e for e in ranking.ranked if e.topic == "alpha")
        self.assertAlmostEqual(alpha.score, 5.0)
        self.assertAlmostEqual(alpha.support, 2 / 3)

    def test_insufficient_support_is_pending_not_ranked_low(self):
        # gamma 只有 1/3 支撑度：进入待补信息，而不是被排到末尾。
        ranking = rank_topics(build_dossiers(_rows()), WEIGHTING)
        self.assertEqual([e.topic for e in ranking.ranked], ["beta", "alpha"])
        (gamma,) = [e for e in ranking.insufficient if e.topic == "gamma"]
        self.assertEqual(gamma.missing_signals, ("reporting", "regional-coverage"))

    def test_candidate_without_data_is_pending_information(self):
        ranking = rank_topics(build_dossiers(_rows()), WEIGHTING,
                              candidates=("delta",))
        (delta,) = [e for e in ranking.insufficient if e.topic == "delta"]
        self.assertEqual(delta.support, 0.0)
        self.assertEqual(len(delta.missing_signals), 3)

    def test_weighting_validation(self):
        with self.assertRaises(ValueError):
            Weighting("空", {})
        with self.assertRaises(ValueError):
            Weighting("零", {"reporting": 0.0})
        with self.assertRaises(ValueError):
            Weighting("负", {"reporting": -1.0})


class CompareWeightingsTests(unittest.TestCase):
    def test_movements_show_ranks_and_pending_per_weighting(self):
        audience_first = Weighting(
            "重视受众", {"audience-questions": 3.0, "reporting": 1.0},
            min_support=0.5,
        )
        comparison = compare_weightings(
            build_dossiers(_rows()), [WEIGHTING, audience_first]
        )
        movements = {m.topic: m for m in comparison.movements}
        # gamma 在「重视受众」下支撑度达标进入排序，在「均衡」下待补。
        self.assertIsNone(movements["gamma"].ranks["均衡"])
        self.assertEqual(movements["gamma"].ranks["重视受众"], 1)
        # beta 在「重视受众」下反而支撑不足。
        self.assertIsNone(movements["beta"].ranks["重视受众"])
        self.assertEqual(movements["beta"].ranks["均衡"], 1)

    def test_duplicate_weighting_names_rejected(self):
        with self.assertRaises(ValueError):
            compare_weightings([], [WEIGHTING, WEIGHTING])


if __name__ == "__main__":
    unittest.main()
