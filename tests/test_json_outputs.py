from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from sporttery_national.export.json_exporter import write_predictions_json
from sporttery_national.utils.json_io import write_json


class JsonOutputTests(unittest.TestCase):
    def test_safe_json_writer_rejects_nan_and_infinity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_json(Path(tmp) / "nan.json", {"value": math.nan})
            with self.assertRaises(ValueError):
                write_json(Path(tmp) / "inf.json", {"value": math.inf})

    def test_predictions_json_preserves_ids_and_number_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "predictions.json"
            write_predictions_json(path, [{
                "issue_id": "0007",
                "match_id": "001",
                "base_home_win_prob": 0.6,
                "top1_pick": 3,
            }])
            rows = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["issue_id"], "0007")
            self.assertEqual(rows[0]["match_id"], "001")
            self.assertIsInstance(rows[0]["base_home_win_prob"], float)
            self.assertIsInstance(rows[0]["top1_pick"], int)


if __name__ == "__main__":
    unittest.main()
