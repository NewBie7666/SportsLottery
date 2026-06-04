from __future__ import annotations

import json
from pathlib import Path


def dumps_json(data: object, *, indent: int | None = 2, sort_keys: bool = False) -> str:
    return json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=sort_keys, allow_nan=False)


def write_json(path: str | Path, data: object) -> None:
    Path(path).write_text(dumps_json(data, indent=2), encoding="utf-8")
