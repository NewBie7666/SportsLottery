from __future__ import annotations

import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME
from sporttery_national.evaluation.settlement import (
    compute_brier_score,
    compute_log_loss,
    derive_actual_result,
    load_predictions_csv,
    load_results_csv,
    settle_predictions,
    summarize_settlement,
    write_settlement_outputs,
)


class SettlementTests(unittest.TestCase):
    def test_derive_actual_result(self) -> None:
        self.assertEqual(derive_actual_result(2, 1), LABEL_HOME)
        self.assertEqual(derive_actual_result(1, 1), LABEL_DRAW)
        self.assertEqual(derive_actual_result(0, 2), LABEL_AWAY)

    def test_metrics(self) -> None:
        self.assertAlmostEqual(compute_log_loss(0.5), -math.log(0.5))
        self.assertAlmostEqual(compute_log_loss(0.0), -math.log(1e-15))
        self.assertAlmostEqual(
            compute_brier_score({LABEL_HOME: 0.7, LABEL_DRAW: 0.2, LABEL_AWAY: 0.1}, LABEL_HOME),
            (0.7 - 1.0) ** 2 + 0.2**2 + 0.1**2,
        )

    def test_settlement_merges_by_string_key_and_hits(self) -> None:
        rows = settle_predictions([_prediction()], [_result()])
        row = rows[0]
        self.assertEqual(row["issue_id"], "0007")
        self.assertEqual(row["match_id"], "001")
        self.assertTrue(row["base_hit"])
        self.assertTrue(row["adjusted_hit"])
        self.assertEqual(row["actual_result"], 3)
        self.assertEqual(row["top1_pick"], 3)
        self.assertAlmostEqual(row["base_actual_prob"], 0.6)

    def test_duplicate_keys_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate.*0007\\+001"):
            settle_predictions([_prediction(), _prediction()], [_result()])
        with self.assertRaisesRegex(ValueError, "duplicate.*0007\\+001"):
            settle_predictions([_prediction()], [_result(), _result()])

    def test_missing_results_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing results.*0007\\+001"):
            settle_predictions([_prediction()], [])

    def test_invalid_pick_raises(self) -> None:
        prediction = _prediction()
        prediction["top1_pick"] = "2"
        with self.assertRaisesRegex(ValueError, "top1_pick"):
            settle_predictions([prediction], [_result()])
        result = _result()
        result["actual_result"] = "2"
        with self.assertRaisesRegex(ValueError, "actual_result"):
            settle_predictions([_prediction()], [result])

    def test_loaders_preserve_leading_zeroes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            predictions = Path(tmp) / "predictions.csv"
            results = Path(tmp) / "results.csv"
            _write_csv(predictions, [_prediction()])
            _write_csv(results, [_result()])
            self.assertEqual(load_predictions_csv(predictions)[0]["match_id"], "001")
            self.assertEqual(load_results_csv(results)[0]["issue_id"], "0007")

    def test_summary_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = settle_predictions([_prediction()], [_result()])
            summary = write_settlement_outputs(tmp, rows)
            self.assertEqual(summary["total_matches"], 1)
            self.assertEqual(summary["error_count"], 0)
            summary_json = json.loads((Path(tmp) / "settlement_summary.json").read_text(encoding="utf-8"))
            for field in (
                "total_matches",
                "base_top1_accuracy",
                "adjusted_top1_accuracy",
                "base_avg_log_loss",
                "adjusted_avg_log_loss",
                "base_avg_brier",
                "adjusted_avg_brier",
                "by_confidence",
                "by_competition",
                "error_count",
            ):
                self.assertIn(field, summary_json)
            content = (Path(tmp) / "settlements.md").read_text(encoding="utf-8")
            self.assertIn("Top1 Accuracy", content)
            self.assertIn("Log Loss", content)
            self.assertIn("Brier Score", content)
            self.assertIn("Confidence", content)
            self.assertIn("错误样例", content)
            for word in ("必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"):
                self.assertNotIn(word, content)

    def test_summarize_counts_errors(self) -> None:
        prediction = _prediction()
        result = _result()
        result["home_score"] = 0
        result["away_score"] = 1
        result["actual_result"] = 0
        rows = settle_predictions([prediction], [result])
        summary = summarize_settlement(rows)
        self.assertFalse(rows[0]["base_hit"])
        self.assertFalse(rows[0]["adjusted_hit"])
        self.assertEqual(summary["error_count"], 1)


def _prediction() -> dict:
    return {
        "issue_id": "0007",
        "match_id": "001",
        "home_team": "Germany",
        "away_team": "France",
        "competition": "Friendly",
        "top1_pick": "3",
        "top1_label": "主胜",
        "second_pick": "1",
        "confidence": "medium",
        "probability_gap": "0.20",
        "base_home_win_prob": "0.60",
        "base_draw_prob": "0.25",
        "base_away_win_prob": "0.15",
        "adjusted_home_win_prob": "0.60",
        "adjusted_draw_prob": "0.25",
        "adjusted_away_win_prob": "0.15",
        "model_version": "test-model",
        "feature_version": "test-feature",
    }


def _result() -> dict:
    return {
        "issue_id": "0007",
        "match_id": "001",
        "home_score": 2,
        "away_score": 1,
        "actual_result": 3,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
