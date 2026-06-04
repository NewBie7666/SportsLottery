from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sporttery_national.ingest.history_loader import import_history
from sporttery_national.utils.storage import read_records


class ImportHistoryOpenFootballTests(unittest.TestCase):
    def test_import_openfootball_filters_and_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "openfootball" / "world-cup" / "2024"
            raw.mkdir(parents=True)
            (raw / "cup.txt").write_text(
                "[2024-06-01] Germany 2-1 France\n"
                "[2024-06-02] Germany U23 1-0 France\n"
                "[2024-06-03] Brazil Women 1-1 Argentina\n"
                "[2024-06-04] Japan Club 0-2 Korea Republic\n"
                "[2024-06-05] Unknownland 1-1 Spain\n"
                "[2024-06-06] Germany vs France\n",
                encoding="utf-8",
            )
            output = root / "national_matches.jsonl"
            report_dir = root / "reports"
            summary = import_history(raw.parent.parent, output, source="openfootball", report_dir=report_dir)
            rows = read_records(output)
            self.assertEqual(summary["successful_parsed_matches"], 5)
            self.assertEqual(summary["filtered_matches"], 3)
            self.assertEqual(summary["final_matches"], 2)
            self.assertEqual(summary["parse_error_rows"], 1)
            self.assertEqual(rows[0]["source_line"], 1)
            self.assertEqual(rows[0]["result"], 3)
            self.assertTrue((report_dir / "import_history_summary.md").exists())
            self.assertTrue((report_dir / "import_errors" / "openfootball_parse_errors.csv").exists())
            self.assertTrue((report_dir / "import_errors" / "unknown_teams.csv").exists())


if __name__ == "__main__":
    unittest.main()
