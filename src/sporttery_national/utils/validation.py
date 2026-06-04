from __future__ import annotations


def require_columns(columns: set[str], required: set[str], source: str) -> None:
    missing = sorted(required - columns)
    if missing:
        raise ValueError(f"{source} missing required columns: {', '.join(missing)}")


def parse_bool(value: object, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "neutral", "中立"}


def parse_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
