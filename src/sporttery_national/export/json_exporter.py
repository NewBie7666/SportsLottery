from __future__ import annotations

from pathlib import Path

from sporttery_national.constants import PREDICTION_FIELDS
from sporttery_national.utils.json_io import write_json


def write_predictions_json(path: str | Path, rows: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    cleaned = [{field: row.get(field) for field in PREDICTION_FIELDS} for row in rows]
    write_json(target, cleaned)
