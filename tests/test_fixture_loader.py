from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sporttery_national.ingest.fixture_loader import load_fixtures


class FixtureLoaderTests(unittest.TestCase):
    def test_missing_columns_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixtures.csv"
            path.write_text("match_id,date\n1,2026-06-01\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                load_fixtures(path)

    def test_odds_can_be_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixtures.csv"
            path.write_text(
                "match_id,date,kickoff,home_team,away_team,odds_home,odds_draw,odds_away\n"
                "001,2026-06-01,20:00,德国,美国,,,\n",
                encoding="utf-8",
            )
            row = load_fixtures(path)[0]
            self.assertIsNone(row["implied_home_win_prob"])
            self.assertEqual(row["home_team"], "Germany")


if __name__ == "__main__":
    unittest.main()
