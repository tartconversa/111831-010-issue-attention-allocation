import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

from signal_lab.__main__ import main
from signal_lab.dossier import build_dossiers
from signal_lab.ranking import Weighting, compare_weightings
from signal_lab.records import Observation
from signal_lab.report import render_decision_report

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class RenderTests(unittest.TestCase):
    def test_report_marks_pending_topics_and_states_limits(self):
        rows = [
            Observation("a", "desk", date(2026, 11, 1), "alpha", 4,
                        signal="reporting"),
            Observation("b", "inbox", date(2026, 11, 2), "alpha", 6,
                        signal="audience-questions"),
            Observation("c", "inbox", date(2026, 11, 3), "gamma", 8,
                        signal="audience-questions"),
        ]
        weighting = Weighting(
            "均衡",
            {"reporting": 1.0, "regional-coverage": 1.0, "audience-questions": 1.0},
            min_support=0.5,
        )
        dossiers = build_dossiers(rows)
        text = render_decision_report(dossiers, compare_weightings(dossiers, [weighting]))
        self.assertIn("不构成因果结论", text)
        self.assertIn("待补信息", text)
        gamma_row = next(
            line for line in text.splitlines() if line.startswith("| gamma")
        )
        self.assertIn("待补", gamma_row)


class CliTests(unittest.TestCase):
    def _run(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def test_compare_lists_pending_topics(self):
        code, out = self._run([
            "compare", str(FIXTURES / "candidate_topics.json"),
            "--weights", "均衡:reporting=1,regional-coverage=1,audience-questions=1",
            "--candidates", "food-security",
        ])
        self.assertEqual(code, 0)
        self.assertIn("digital-governance", out)
        self.assertIn("food-security", out)
        self.assertIn("待补", out)

    def test_explain_flags_backfill(self):
        code, out = self._run([
            "explain",
            str(FIXTURES / "candidate_topics.json"),
            str(FIXTURES / "candidate_topics_backfilled.json"),
            "--weights", "reporting=1,regional-coverage=1,audience-questions=1",
        ])
        self.assertEqual(code, 0)
        self.assertIn("覆盖补齐", out)
        self.assertIn("south-asia-wire", out)

    def test_decide_then_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run([
                "decide", str(FIXTURES / "candidate_topics.json"),
                "--ledger", tmp, "--decision-id", "2026-11", "--period", "2026-11",
                "--select", "international-cooperation,climate-adaptation",
                "--rationale", "覆盖与受众提问都稳定",
                "--weights", "reporting=1,regional-coverage=1,audience-questions=1",
            ])
            self.assertEqual(code, 0)
            code, out = self._run(["verify", "--ledger", tmp])
            self.assertEqual(code, 0)
            self.assertIn("2026-11", out)


if __name__ == "__main__":
    unittest.main()
