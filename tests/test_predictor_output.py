from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sporttery_national.constants import PREDICTION_FIELDS
from sporttery_national.ingest.fixture_loader import load_fixtures
from sporttery_national.models.predictor import predict_fixtures


class PredictorOutputTests(unittest.TestCase):
    def test_prediction_fields_and_adjusted_equals_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = root / "models"
            model_dir.mkdir()
            (model_dir / "elo_state.json").write_text(
                json.dumps({"default": 1500, "k": 24, "ratings": {"Germany": 1600, "United States": 1500}}),
                encoding="utf-8",
            )
            fixtures = root / "fixtures.csv"
            fixtures.write_text(
                "match_id,date,kickoff,home_team,away_team,odds_home,odds_draw,odds_away\n"
                "001,2026-06-01,20:00,Germany,United States,1.8,3.2,4.0\n",
                encoding="utf-8",
            )
            rows = predict_fixtures(load_fixtures(fixtures), model_dir)
            row = rows[0]
            for field in PREDICTION_FIELDS:
                self.assertIn(field, row)
            self.assertAlmostEqual(row["base_home_win_prob"] + row["base_draw_prob"] + row["base_away_win_prob"], 1.0)
            self.assertEqual(row["base_home_win_prob"], row["adjusted_home_win_prob"])
            self.assertIn(row["top1_pick"], {3, 1, 0})


if __name__ == "__main__":
    unittest.main()
