from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def write_records(path: str | Path, records: Iterable[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_records(path: str | Path) -> list[dict]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Data file not found: {source}")
    records: list[dict] = []
    with source.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid record at {source}:{line_no}: {exc}") from exc
    return records
