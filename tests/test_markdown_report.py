from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sporttery_national.export.markdown_report import write_markdown_report


class MarkdownReportTests(unittest.TestCase):
    def test_report_includes_second_pick_gap_and_risk_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predictions.md"
            write_markdown_report(path, [{
                "match_id": "001",
                "home_team": "Germany",
                "away_team": "France",
                "adjusted_home_win_prob": 0.55,
                "adjusted_draw_prob": 0.25,
                "adjusted_away_win_prob": 0.20,
                "top1_label": "主胜",
                "second_pick": 1,
                "probability_gap": 0.30,
                "confidence": "medium",
                "risk_note": "首选结果相对明确；仅供概率研究，不承诺中奖或盈利。",
            }])
            content = path.read_text(encoding="utf-8")
            self.assertIn("次选", content)
            self.assertIn("概率差距", content)
            self.assertIn("平", content)
            self.assertIn("0.300", content)
            self.assertIn("首选结果相对明确", content)

    def test_report_rejects_forbidden_words(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predictions.md"
            with self.assertRaisesRegex(ValueError, "forbidden"):
                write_markdown_report(path, [{
                    "match_id": "001",
                    "home_team": "Germany",
                    "away_team": "France",
                    "adjusted_home_win_prob": 0.55,
                    "adjusted_draw_prob": 0.25,
                    "adjusted_away_win_prob": 0.20,
                    "top1_label": "主胜",
                    "second_pick": 1,
                    "probability_gap": 0.30,
                    "confidence": "medium",
                    "risk_note": "推荐下注",
                }])


if __name__ == "__main__":
    unittest.main()
