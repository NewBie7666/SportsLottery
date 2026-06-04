from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sporttery_national.evaluation.backtester import backtest
from sporttery_national.utils.storage import write_records


class BacktestTests(unittest.TestCase):
    def test_backtest_outputs_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            teams = ["Germany", "France", "Spain", "Italy"]
            for index in range(30):
                home = teams[index % len(teams)]
                away = teams[(index + 1) % len(teams)]
                rows.append({
                    "date": f"2024-01-{(index % 28) + 1:02d}",
                    "home_team": home,
                    "away_team": away,
                    "home_score": 1 + (index % 3),
                    "away_score": index % 2,
                    "competition": "Friendly",
                    "neutral": False,
                    "result": 3 if 1 + (index % 3) > index % 2 else 1,
                })
            data = root / "national_matches.parquet"
            write_records(data, rows)
            summary = backtest(data, root / "reports", min_history=5)
            self.assertIn("log_loss", summary)
            self.assertIn("brier_score", summary)
            self.assertIn("top1_accuracy", summary)
            self.assertGreater(summary["matches"], 0)


if __name__ == "__main__":
    unittest.main()
