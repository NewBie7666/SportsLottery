from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sporttery_national.ingest.openfootball_parser import parse_file


class OpenFootballParserTests(unittest.TestCase):
    def test_parse_supported_score_formats_and_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world-cup-2024.txt"
            path.write_text(
                "# comment\n"
                "\n"
                "= World Cup\n"
                "[2024-06-01] Germany 2-1 France\n"
                "[2024-06-02] Germany v France 1-1\n"
                "[2024-06-03] Germany - France 0-2\n"
                "[2024-06-04] Germany vs France\n",
                encoding="utf-8",
            )
            records, errors = parse_file(path)
            self.assertEqual(len(records), 3)
            self.assertEqual(len(errors), 1)
            self.assertEqual(records[0]["result"], 3)
            self.assertEqual(records[1]["result"], 1)
            self.assertEqual(records[2]["result"], 0)
            for record in records:
                self.assertIn("source_file", record)
                self.assertIn("source_line", record)
                self.assertEqual(record["competition"], "World Cup 2024")

    def test_parse_month_date_with_year_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "2024"
            root.mkdir()
            path = root / "cup.txt"
            path.write_text("[Jun 1] Germany 2-1 France\n", encoding="utf-8")
            records, errors = parse_file(path)
            self.assertEqual(errors, [])
            self.assertEqual(records[0]["date"], "2024-06-01")

    def test_parse_real_openfootball_date_and_venue_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "1956_afc_asian_cup.txt"
            path.write_text(
                "= AFC Asian Cup 1956\n"
                "Sat Sep 1\n"
                "  Hong Kong              2-3 Israel                   @ So Kon Po, Hong Kong\n",
                encoding="utf-8",
            )
            records, errors = parse_file(path)
            self.assertEqual(errors, [])
            self.assertEqual(records[0]["date"], "1956-09-01")
            self.assertEqual(records[0]["home_team"], "Hong Kong")
            self.assertEqual(records[0]["away_team"], "Israel")


if __name__ == "__main__":
    unittest.main()
