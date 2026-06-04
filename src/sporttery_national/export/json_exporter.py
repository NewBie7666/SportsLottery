from __future__ import annotations

import json
from pathlib import Path

from sporttery_national.constants import PREDICTION_FIELDS


def write_predictions_json(path: str | Path, rows: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    cleaned = [{field: row.get(field) for field in PREDICTION_FIELDS} for row in rows]
    target.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
