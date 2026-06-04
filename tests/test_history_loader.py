from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sporttery_national.ingest.history_loader import import_history
from sporttery_national.utils.storage import read_records


class HistoryLoaderTests(unittest.TestCase):
    def test_import_filters_youth_and_normalizes_teams(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "matches.csv"
            raw.write_text(
                "date,home_team,away_team,home_score,away_score,competition,neutral,venue\n"
                "2024-01-01,德国,美国,2,1,Friendly,false,Berlin\n"
                "2024-01-02,Germany U23,France,1,1,Friendly,false,Berlin\n",
                encoding="utf-8",
            )
            out = root / "national_matches.parquet"
            count = import_history(raw, out)
            rows = read_records(out)
            self.assertEqual(count, 1)
            self.assertEqual(rows[0]["home_team"], "Germany")
            self.assertEqual(rows[0]["away_team"], "United States")
            self.assertEqual(rows[0]["result"], 3)
            self.assertGreaterEqual(rows[0]["home_score"], 0)


if __name__ == "__main__":
    unittest.main()
