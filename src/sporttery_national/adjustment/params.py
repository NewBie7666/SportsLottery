from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PARAMS = {
    "experiment_name": "default_adjustment",
    "draw_bias": 0.0,
    "upset_bias": 0.0,
    "market_weight": 0.0,
    "temperature": 1.0,
}

RANGES = {
    "draw_bias": (-0.10, 0.10),
    "upset_bias": (0.0, 0.10),
    "market_weight": (0.0, 1.0),
    "temperature": (0.70, 1.50),
}


def load_adjustment_params(path: str | Path) -> dict:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid adjustment params JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Adjustment params must be a JSON object")
    return validate_adjustment_params(raw)


def load_params(path: str | Path) -> dict:
    return load_adjustment_params(path)


def validate_adjustment_params(params: dict | None) -> dict:
    if params is None:
        return dict(DEFAULT_PARAMS)
    unknown = sorted(set(params) - set(DEFAULT_PARAMS))
    if unknown:
        raise ValueError(f"Unknown adjustment params: {', '.join(unknown)}")
    normalized = dict(DEFAULT_PARAMS)
    normalized.update(params)
    if not isinstance(normalized["experiment_name"], str) or not normalized["experiment_name"].strip():
        raise ValueError("experiment_name must be a non-empty string")
    normalized["experiment_name"] = normalized["experiment_name"].strip()
    for key, (low, high) in RANGES.items():
        try:
            value = float(normalized[key])
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be a number") from None
        if value < low or value > high:
            raise ValueError(f"{key} must be between {low} and {high}")
        normalized[key] = value
    return normalized


def normalize_params(params: dict | None) -> dict:
    return validate_adjustment_params(params)
