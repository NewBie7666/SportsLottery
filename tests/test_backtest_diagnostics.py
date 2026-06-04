from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME
from sporttery_national.evaluation import backtester
from sporttery_national.evaluation.backtester import summarize_backtest_details


class BacktestDiagnosticsTests(unittest.TestCase):
    def test_summary_distributions_recalls_bias_and_confusion(self) -> None:
        details = [
            _detail("2024-01-01", LABEL_HOME, LABEL_HOME, 0.60, 0.25, 0.15, "high", "A"),
            _detail("2024-01-02", LABEL_DRAW, LABEL_HOME, 0.55, 0.30, 0.15, "medium", "A"),
            _detail("2024-01-03", LABEL_DRAW, LABEL_DRAW, 0.30, 0.45, 0.25, "medium", "B"),
            _detail("2024-01-04", LABEL_AWAY, LABEL_HOME, 0.70, 0.20, 0.10, "high", "B"),
        ]
        summary = summarize_backtest_details(details, min_history=2)

        self.assertEqual(summary["result_distribution"], {"3": 1, "1": 2, "0": 1})
        self.assertEqual(summary["top1_distribution"], {"3": 3, "1": 1, "0": 0})
        self.assertAlmostEqual(summary["draw_recall"], 0.5)
        self.assertAlmostEqual(summary["home_win_recall"], 1.0)
        self.assertAlmostEqual(summary["away_win_recall"], 0.0)
        self.assertEqual(summary["confusion_matrix"]["1"]["3"], 1)
        self.assertEqual(summary["confusion_matrix"]["1"]["1"], 1)
        self.assertEqual(summary["confusion_matrix"]["0"]["3"], 1)
        self.assertIn("high", summary["by_confidence"])
        self.assertIn("2024", summary["by_year"])
        self.assertIn("A", summary["by_competition"])
        self.assertIn("False", summary["by_neutral"])

        draw_bias = summary["draw_bias_diagnostics"]
        self.assertAlmostEqual(draw_bias["draw_actual_rate"], 0.5)
        self.assertAlmostEqual(draw_bias["draw_top1_rate"], 0.25)
        self.assertAlmostEqual(draw_bias["draw_under_prediction_gap"], 0.25)
        self.assertAlmostEqual(draw_bias["avg_draw_prob_when_actual_draw"], 0.375)
        self.assertAlmostEqual(draw_bias["avg_draw_prob_all"], 0.30)

        prediction_bias = summary["prediction_bias"]
        self.assertAlmostEqual(prediction_bias["distribution_gap"]["3"], 0.5)
        self.assertAlmostEqual(prediction_bias["distribution_gap"]["1"], -0.25)
        self.assertAlmostEqual(prediction_bias["distribution_gap"]["0"], -0.25)

    def test_recent_windows_empty_metrics_are_null(self) -> None:
        details = [_detail("1999-01-01", LABEL_HOME, LABEL_HOME, 0.60, 0.25, 0.15, "high", "A")]
        summary = summarize_backtest_details(details)
        self.assertEqual(summary["recent_windows"]["since_2000"]["matches"], 0)
        self.assertIsNone(summary["recent_windows"]["since_2000"]["accuracy"])
        self.assertIsNone(summary["recent_windows"]["since_2000"]["avg_log_loss"])
        self.assertIsNone(summary["recent_windows"]["since_2000"]["avg_brier"])
        self.assertIsNone(summary["recent_windows"]["since_2000"]["draw_recall"])

    def test_calibration_bins_have_avg_top1_prob(self) -> None:
        details = [
            _detail("2024-01-01", LABEL_HOME, LABEL_HOME, 0.35, 0.34, 0.31, "low", "A"),
            _detail("2024-01-02", LABEL_HOME, LABEL_HOME, 0.65, 0.20, 0.15, "high", "A"),
            _detail("2024-01-03", LABEL_AWAY, LABEL_HOME, 0.75, 0.15, 0.10, "high", "A"),
        ]
        bins = summarize_backtest_details(details)["calibration_bins"]
        by_name = {row["bin"]: row for row in bins}
        self.assertIn("avg_top1_prob", by_name["0.30-0.40"])
        self.assertAlmostEqual(by_name["0.30-0.40"]["avg_top1_prob"], 0.35)
        self.assertEqual(by_name["0.70+"]["matches"], 1)
        self.assertEqual(by_name["0.70+"]["confidence_distribution"], {"high": 1})

    def test_markdown_limits_competitions_and_high_confidence_errors(self) -> None:
        details = []
        for index in range(25):
            details.append(_detail(f"2024-01-{(index % 28) + 1:02d}", LABEL_AWAY, LABEL_HOME, 0.80, 0.10, 0.10, "high", f"C{index:02d}"))
        summary = summarize_backtest_details(details)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "backtest_report.md"
            backtester._write_markdown_report(path, summary, details)
            content = path.read_text(encoding="utf-8")
            competition_section = content.split("## Competition 分组", 1)[1].split("## 概率校准分桶", 1)[0]
            error_section = content.split("## 高置信错误样例", 1)[1]
            self.assertLessEqual(competition_section.count("| C"), 20)
            self.assertLessEqual(error_section.count("| 2024-01-"), 20)
            for word in ("必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"):
                self.assertNotIn(word, content)

    def test_backtest_details_include_top_prob_fields(self) -> None:
        row = _detail("2024-01-01", LABEL_HOME, LABEL_HOME, 0.60, 0.25, 0.15, "high", "A")
        self.assertEqual(row["top1_prob"], 0.60)
        self.assertEqual(row["second_prob"], 0.25)
        self.assertAlmostEqual(row["probability_gap"], 0.35)

    def test_summary_json_contains_metadata(self) -> None:
        details = [_detail("2024-01-01", LABEL_HOME, LABEL_HOME, 0.60, 0.25, 0.15, "high", "A")]
        summary = summarize_backtest_details(details, [{"date": "2023-01-01"}, {"date": "2024-01-01"}], min_history=7)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["metadata"]["data_start_date"], "2023-01-01")
        self.assertEqual(loaded["metadata"]["data_end_date"], "2024-01-01")
        self.assertEqual(loaded["metadata"]["backtest_start_date"], "2024-01-01")
        self.assertEqual(loaded["metadata"]["min_history"], 7)
        self.assertIn("model_version", loaded["metadata"])
        self.assertIn("feature_version", loaded["metadata"])


def _detail(date: str, actual: int, top1: int, home: float, draw: float, away: float, confidence: str, competition: str) -> dict:
    probs = {LABEL_HOME: home, LABEL_DRAW: draw, LABEL_AWAY: away}
    ranked = sorted(probs.items(), key=lambda item: (-item[1], item[0]))
    top1_prob = probs[top1]
    second_pick, second_prob = ranked[1] if ranked[0][0] == top1 else ranked[0]
    actual_prob = probs[actual]
    return {
        "synthetic_backtest_id": f"BT{abs(hash((date, competition))) % 1000000:06d}",
        "date": date,
        "competition": competition,
        "home_team": "Home",
        "away_team": "Away",
        "neutral": False,
        "actual_result": actual,
        "actual_label": str(actual),
        "base_home_win_prob": home,
        "base_draw_prob": draw,
        "base_away_win_prob": away,
        "top1_pick": top1,
        "top1_label": str(top1),
        "top1_prob": top1_prob,
        "second_pick": second_pick,
        "second_prob": second_prob,
        "probability_gap": top1_prob - second_prob,
        "confidence": confidence,
        "hit": actual == top1,
        "actual_prob": actual_prob,
        "log_loss": backtester.compute_log_loss(actual_prob),
        "brier": backtester.compute_brier_score({"home": home, "draw": draw, "away": away}, actual),
        "model_version": "test",
        "feature_version": "test",
    }


if __name__ == "__main__":
    unittest.main()
