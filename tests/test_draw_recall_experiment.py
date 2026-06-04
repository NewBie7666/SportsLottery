from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from sporttery_national.experiments.draw_recall import (
    evaluate_strategy,
    load_backtest_details,
    run_draw_recall_experiment,
    run_parameter_grid,
)


class DrawRecallExperimentTests(unittest.TestCase):
    def test_draw_recall_can_improve_from_zero(self) -> None:
        rows = load_backtest_details(_write_details(_details()))
        result = evaluate_strategy(rows, draw_min_prob=0.30, draw_gap_trigger=0.10, draw_bias=0.04)
        self.assertEqual(result["base_draw_recall"], 0.0)
        self.assertGreater(result["adjusted_draw_recall"], result["base_draw_recall"])

    def test_draw_precision_and_changed_to_draw_count(self) -> None:
        rows = load_backtest_details(_write_details(_details()))
        result = evaluate_strategy(rows, draw_min_prob=0.30, draw_gap_trigger=0.10, draw_bias=0.04)
        self.assertAlmostEqual(result["adjusted_draw_precision"], 0.5)
        self.assertEqual(result["changed_pick_count"], 2)
        self.assertEqual(result["changed_to_draw_count"], 2)

    def test_parameter_grid_result_count(self) -> None:
        rows = load_backtest_details(_write_details(_details()))
        results = run_parameter_grid(rows)
        self.assertEqual(len(results), 64)

    def test_candidate_filter(self) -> None:
        rows = load_backtest_details(_write_details(_candidate_details()))
        result = evaluate_strategy(rows, draw_min_prob=0.30, draw_gap_trigger=0.10, draw_bias=0.04)
        self.assertTrue(result["is_candidate"])
        self.assertGreater(result["adjusted_draw_recall"], result["base_draw_recall"])
        self.assertGreaterEqual(result["adjusted_top1_accuracy"], result["base_top1_accuracy"] - 0.02)
        self.assertLessEqual(result["adjusted_avg_log_loss"], result["base_avg_log_loss"] + 0.03)

    def test_outputs_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            details_path = root / "backtest_details.json"
            details_path.write_text(json.dumps(_candidate_details()), encoding="utf-8")
            summary = run_draw_recall_experiment(details_path, root / "out")
            self.assertEqual(summary["parameter_grid"]["result_count"], 64)
            self.assertEqual(len(summary["results"]), 64)
            self.assertTrue((root / "out" / "draw_experiment_results.csv").exists())
            self.assertTrue((root / "out" / "draw_experiment_summary.json").exists())
            self.assertTrue((root / "out" / "draw_experiment_report.md").exists())
            summary_json = json.loads((root / "out" / "draw_experiment_summary.json").read_text(encoding="utf-8"))
            self.assert_no_nan_or_inf(summary_json)
            report = (root / "out" / "draw_experiment_report.md").read_text(encoding="utf-8")
            self.assertIn("平局召回专项实验报告", report)
            for word in ("必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"):
                self.assertNotIn(word, report)

    def assert_no_nan_or_inf(self, value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                self.assert_no_nan_or_inf(item)
        elif isinstance(value, list):
            for item in value:
                self.assert_no_nan_or_inf(item)
        elif isinstance(value, float):
            self.assertFalse(math.isnan(value) or math.isinf(value))


def _details() -> list[dict]:
    return [
        _detail("BT000001", 1, 3, 0.34, 0.29, 0.37),
        _detail("BT000002", 3, 3, 0.45, 0.28, 0.27),
        _detail("BT000003", 0, 0, 0.30, 0.29, 0.41),
        _detail("BT000004", 1, 3, 0.50, 0.25, 0.25),
    ]


def _candidate_details() -> list[dict]:
    return [
        _detail("BT000001", 1, 3, 0.34, 0.29, 0.37),
        _detail("BT000002", 1, 3, 0.35, 0.30, 0.35),
        _detail("BT000003", 3, 3, 0.60, 0.22, 0.18),
        _detail("BT000004", 0, 0, 0.18, 0.22, 0.60),
    ]


def _detail(
    backtest_id: str,
    actual_result: int,
    top1_pick: int,
    home: float,
    draw: float,
    away: float,
) -> dict:
    top1_prob = max(home, draw, away)
    second_prob = sorted([home, draw, away], reverse=True)[1]
    return {
        "synthetic_backtest_id": backtest_id,
        "date": "2026-01-01",
        "competition": "Test",
        "home_team": "Home",
        "away_team": "Away",
        "neutral": False,
        "actual_result": actual_result,
        "actual_label": str(actual_result),
        "base_home_win_prob": home,
        "base_draw_prob": draw,
        "base_away_win_prob": away,
        "top1_pick": top1_pick,
        "top1_label": str(top1_pick),
        "top1_prob": top1_prob,
        "second_pick": 1,
        "second_prob": second_prob,
        "probability_gap": top1_prob - second_prob,
        "confidence": "low",
        "hit": top1_pick == actual_result,
        "actual_prob": {3: home, 1: draw, 0: away}[actual_result],
        "log_loss": 0.0,
        "brier": 0.0,
        "model_version": "test",
        "feature_version": "test",
    }


def _write_details(rows: list[dict]) -> Path:
    tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    with tmp:
        json.dump(rows, tmp)
    return Path(tmp.name)


if __name__ == "__main__":
    unittest.main()
