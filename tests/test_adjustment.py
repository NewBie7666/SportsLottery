from __future__ import annotations

import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

from sporttery_national.adjustment.adjuster import MARKET_SKIPPED_NOTE
from sporttery_national.adjustment.experiment import adjust_prediction_rows, run_adjustment_experiment, summarize_adjustments
from sporttery_national.adjustment.interface import apply_adjustment
from sporttery_national.adjustment.params import normalize_params
from sporttery_national.constants import PREDICTION_FIELDS
from sporttery_national.evaluation.settlement import settle_predictions


class AdjustmentTests(unittest.TestCase):
    def test_none_params_returns_base_copy(self) -> None:
        base = {"home": 0.5, "draw": 0.3, "away": 0.2}
        adjusted = apply_adjustment(base)
        self.assertEqual(_prob_only(adjusted), base)
        self.assertIn("note", adjusted)
        self.assertIsNot(adjusted, base)

    def test_draw_bias_increases_draw_and_normalizes(self) -> None:
        base = {"home": 0.5, "draw": 0.25, "away": 0.25}
        adjusted = apply_adjustment(base, {"draw_bias": 0.05})
        self.assertGreater(adjusted["draw"], base["draw"])
        self.assertAlmostEqual(_prob_sum(adjusted), 1.0)
        self.assertTrue(all(0 <= value <= 1 for value in _prob_only(adjusted).values()))

    def test_draw_bias_can_decrease_draw_and_note_is_not_probability(self) -> None:
        base = {"home": 0.4, "draw": 0.35, "away": 0.25}
        adjusted = apply_adjustment(base, {"draw_bias": -0.04})
        self.assertLess(adjusted["draw"], base["draw"])
        self.assertIsInstance(adjusted["note"], str)
        self.assertAlmostEqual(_prob_sum(adjusted), 1.0)

    def test_market_weight_zero_ignores_implied(self) -> None:
        base = {"home": 0.5, "draw": 0.3, "away": 0.2}
        adjusted = apply_adjustment(base, {"market_weight": 0.0}, {"home": 0.1, "draw": 0.1, "away": 0.8})
        self.assertEqual(_prob_only(adjusted), base)

    def test_market_weight_moves_toward_implied_and_missing_odds_note(self) -> None:
        base = {"home": 0.6, "draw": 0.25, "away": 0.15}
        implied = {"home": 0.3, "draw": 0.3, "away": 0.4}
        adjusted = apply_adjustment(base, {"market_weight": 0.5}, implied)
        self.assertLess(adjusted["home"], base["home"])
        self.assertGreater(adjusted["away"], base["away"])
        self.assertNotIn(MARKET_SKIPPED_NOTE, adjusted["note"])

        skipped = apply_adjustment(base, {"market_weight": 0.5}, None)
        self.assertIn(MARKET_SKIPPED_NOTE, skipped["note"])
        self.assertAlmostEqual(_prob_sum(skipped), 1.0)

    def test_temperature_sharpens_and_smooths(self) -> None:
        base = {"home": 0.6, "draw": 0.25, "away": 0.15}
        sharp = apply_adjustment(base, {"temperature": 0.8})
        smooth = apply_adjustment(base, {"temperature": 1.3})
        self.assertGreater(sharp["home"], base["home"])
        self.assertLess(smooth["home"], base["home"])

    def test_upset_bias_increases_underdog(self) -> None:
        base = {"home": 0.6, "draw": 0.25, "away": 0.15}
        adjusted = apply_adjustment(base, {"upset_bias": 0.05})
        self.assertGreater(adjusted["away"], base["away"])

    def test_invalid_params_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, "draw_bias"):
            normalize_params({"draw_bias": 0.2})
        with self.assertRaisesRegex(ValueError, "Unknown"):
            normalize_params({"bad": 1})
        with self.assertRaisesRegex(ValueError, "experiment_name"):
            normalize_params({"experiment_name": ""})

    def test_adjusted_predictions_preserve_base_and_add_fields(self) -> None:
        row = _prediction_row()
        adjusted = adjust_prediction_rows([row], normalize_params({"draw_bias": 0.03}))[0]
        self.assertEqual(adjusted["base_home_win_prob"], row["base_home_win_prob"])
        self.assertIn("adjusted_top1_pick", adjusted)
        self.assertIn("adjusted_confidence", adjusted)
        self.assertAlmostEqual(
            float(adjusted["adjusted_home_win_prob"]) + float(adjusted["adjusted_draw_prob"]) + float(adjusted["adjusted_away_win_prob"]),
            1.0,
        )

    def test_market_skip_is_per_row(self) -> None:
        row_with_market = _prediction_row()
        row_without_market = _prediction_row(match_id="002")
        row_without_market["implied_home_win_prob"] = ""
        adjusted = adjust_prediction_rows(
            [row_with_market, row_without_market],
            normalize_params({"market_weight": 0.5}),
        )
        self.assertNotIn(MARKET_SKIPPED_NOTE, adjusted[0]["adjustment_note"])
        self.assertIn(MARKET_SKIPPED_NOTE, adjusted[1]["adjustment_note"])
        summary = summarize_adjustments(adjusted, normalize_params({"market_weight": 0.5}))
        self.assertEqual(summary["market_skipped_count"], 1)
        self.assertEqual(summary["market_weight_skipped_count"], 1)

    def test_changed_picks_and_shift_summary(self) -> None:
        unchanged = _adjusted_row(match_id="001", top1_pick="3", adjusted_top1_pick="3", adjusted_home="0.55", adjusted_draw="0.30", adjusted_away="0.15")
        changed = _adjusted_row(match_id="002", top1_pick="3", adjusted_top1_pick="1", adjusted_home="0.30", adjusted_draw="0.55", adjusted_away="0.15")
        summary = summarize_adjustments([unchanged, changed], normalize_params({}))
        self.assertEqual(summary["changed_pick_count"], 1)
        self.assertEqual(summary["changed_top1_count"], 1)
        self.assertEqual(len(summary["changed_picks"]), 1)
        self.assertEqual(summary["changed_picks"][0]["match_id"], "002")
        self.assertAlmostEqual(summary["avg_abs_home_shift"], (0.05 + 0.30) / 2)
        self.assertAlmostEqual(summary["avg_abs_draw_shift"], (0.05 + 0.30) / 2)
        self.assertAlmostEqual(summary["avg_abs_away_shift"], 0.0)
        self.assertAlmostEqual(summary["avg_abs_prob_shift"], (((0.05 + 0.05 + 0.0) / 3) + ((0.30 + 0.30 + 0.0) / 3)) / 2)

    def test_changed_picks_limit_is_20(self) -> None:
        rows = [
            _adjusted_row(match_id=f"{index:03d}", top1_pick="3", adjusted_top1_pick="1", adjusted_home="0.30", adjusted_draw="0.55", adjusted_away="0.15")
            for index in range(25)
        ]
        summary = summarize_adjustments(rows, normalize_params({}))
        self.assertEqual(summary["changed_pick_count"], 25)
        self.assertEqual(len(summary["changed_picks"]), 20)

    def test_experiment_outputs_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            predictions = root / "predictions.csv"
            params = root / "params.json"
            _write_predictions(predictions, [_prediction_row()])
            params.write_text(json.dumps({"experiment_name": "test", "draw_bias": 0.03}), encoding="utf-8")
            summary = run_adjustment_experiment(predictions, params, root / "out")
            self.assertEqual(summary["experiment_name"], "test")
            self.assertTrue((root / "out" / "adjusted_predictions.csv").exists())
            self.assertTrue((root / "out" / "adjusted_predictions.json").exists())
            self.assertTrue((root / "out" / "adjustment_summary.json").exists())
            adjusted_json = json.loads((root / "out" / "adjusted_predictions.json").read_text(encoding="utf-8"))
            adjusted_row = adjusted_json[0]
            self.assertEqual(adjusted_row["issue_id"], "202606")
            self.assertEqual(adjusted_row["match_id"], "001")
            self.assertIsInstance(adjusted_row["top1_pick"], int)
            self.assertIsInstance(adjusted_row["second_pick"], int)
            self.assertIsInstance(adjusted_row["adjusted_top1_pick"], int)
            self.assertIsInstance(adjusted_row["adjusted_second_pick"], int)
            self.assertIsInstance(adjusted_row["odds_home"], float)
            self.assertIsInstance(adjusted_row["base_home_win_prob"], float)
            self.assertIsInstance(adjusted_row["adjusted_home_win_prob"], float)
            self.assertIsInstance(adjusted_row["probability_gap"], float)
            self.assertIsInstance(adjusted_row["adjustment_params"], dict)
            self.assert_no_nan_or_inf(adjusted_json)
            summary_json = json.loads((root / "out" / "adjustment_summary.json").read_text(encoding="utf-8"))
            self.assertIsInstance(summary_json["adjustment_params"], dict)
            self.assertIn("avg_abs_prob_shift", summary_json)
            self.assert_no_nan_or_inf(summary_json)
            report = (root / "out" / "adjustment_report.md").read_text(encoding="utf-8")
            self.assertIn("仅供概率研究，不承诺中奖或盈利。", report)
            for word in ("必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"):
                self.assertNotIn(word, report)

    def test_adjusted_prediction_json_writes_blank_numbers_as_null(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            predictions = root / "predictions.csv"
            params = root / "params.json"
            row = _prediction_row()
            row["odds_away"] = ""
            row["implied_away_win_prob"] = ""
            _write_predictions(predictions, [row])
            params.write_text(json.dumps({"experiment_name": "test", "market_weight": 0.5}), encoding="utf-8")
            run_adjustment_experiment(predictions, params, root / "out")
            adjusted = json.loads((root / "out" / "adjusted_predictions.json").read_text(encoding="utf-8"))[0]
            self.assertIsNone(adjusted["odds_away"])
            self.assertIsNone(adjusted["implied_away_win_prob"])
            self.assertIn(MARKET_SKIPPED_NOTE, adjusted["adjustment_note"])

    def assert_no_nan_or_inf(self, value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                self.assert_no_nan_or_inf(item)
        elif isinstance(value, list):
            for item in value:
                self.assert_no_nan_or_inf(item)
        elif isinstance(value, float):
            self.assertFalse(math.isnan(value) or math.isinf(value))

    def test_settle_reads_adjusted_predictions(self) -> None:
        prediction = _prediction_row()
        prediction.update({
            "top1_pick": "0",
            "adjusted_top1_pick": "3",
            "adjusted_home_win_prob": "0.70",
            "adjusted_draw_prob": "0.20",
            "adjusted_away_win_prob": "0.10",
        })
        result = {"issue_id": "202606", "match_id": "001", "home_score": 2, "away_score": 1, "actual_result": 3}
        rows = settle_predictions([prediction], [result])
        self.assertFalse(rows[0]["base_hit"])
        self.assertTrue(rows[0]["adjusted_hit"])
        self.assertAlmostEqual(rows[0]["adjusted_actual_prob"], 0.70)


def _prediction_row(match_id: str = "001") -> dict:
    row = {field: "" for field in PREDICTION_FIELDS}
    row.update({
        "issue_id": "202606",
        "match_id": match_id,
        "date": "2026-06-10",
        "kickoff": "20:00",
        "competition": "Friendly",
        "venue": "Berlin",
        "neutral": "False",
        "home_team_raw": "Germany",
        "away_team_raw": "France",
        "home_team": "Germany",
        "away_team": "France",
        "odds_home": "2.0",
        "odds_draw": "3.0",
        "odds_away": "4.0",
        "implied_home_win_prob": "0.46",
        "implied_draw_prob": "0.31",
        "implied_away_win_prob": "0.23",
        "base_home_win_prob": "0.60",
        "base_draw_prob": "0.25",
        "base_away_win_prob": "0.15",
        "adjusted_home_win_prob": "0.60",
        "adjusted_draw_prob": "0.25",
        "adjusted_away_win_prob": "0.15",
        "top1_pick": "3",
        "second_pick": "1",
        "probability_gap": "0.35",
        "top1_label": "主胜",
        "confidence": "medium",
        "risk_note": "仅供概率研究，不承诺中奖或盈利。",
        "prob_diff_home": "0.14",
        "prob_diff_draw": "-0.06",
        "prob_diff_away": "-0.08",
        "model_version": "test",
        "feature_version": "test",
        "created_at": "2026-06-01T00:00:00+00:00",
    })
    return row


def _adjusted_row(
    match_id: str,
    top1_pick: str,
    adjusted_top1_pick: str,
    adjusted_home: str,
    adjusted_draw: str,
    adjusted_away: str,
) -> dict:
    row = _prediction_row()
    row.update({
        "match_id": match_id,
        "top1_pick": top1_pick,
        "adjusted_top1_pick": adjusted_top1_pick,
        "adjusted_top1_label": "adjusted",
        "adjusted_home_win_prob": adjusted_home,
        "adjusted_draw_prob": adjusted_draw,
        "adjusted_away_win_prob": adjusted_away,
        "adjustment_note": "",
    })
    return row


def _prob_only(result: dict) -> dict:
    return {key: result[key] for key in ("home", "draw", "away")}


def _prob_sum(result: dict) -> float:
    return sum(float(result[key]) for key in ("home", "draw", "away"))


def _write_predictions(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
