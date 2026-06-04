from __future__ import annotations

import math

from sporttery_national.adjustment.params import validate_adjustment_params

PROB_KEYS = ("home", "draw", "away")
EPSILON = 1e-15
MARKET_SKIPPED_NOTE = "未提供官方奖金，market_weight 未生效"


def apply_adjustment(base_probs: dict, params: dict | None = None, implied_probs: dict | None = None) -> dict:
    base = _validate_probs(base_probs, "base_probs")
    if params is None:
        return {**base, "note": ""}

    normalized_params = validate_adjustment_params(params)
    notes: list[str] = []
    probs = dict(base)

    if abs(normalized_params["temperature"] - 1.0) >= 1e-12:
        probs = _temperature_scale(probs, normalized_params["temperature"])
        notes.append("temperature 已应用")

    if normalized_params["draw_bias"]:
        probs["draw"] += normalized_params["draw_bias"]
        probs = _normalize_positive(probs)
        notes.append("draw_bias 已应用")

    if normalized_params["upset_bias"]:
        probs = _apply_upset_bias(probs, normalized_params["upset_bias"])
        notes.append("upset_bias 已应用")

    market_weight = normalized_params["market_weight"]
    if market_weight > 0:
        try:
            implied = _validate_probs(implied_probs, "implied_probs")
        except ValueError:
            notes.append(MARKET_SKIPPED_NOTE)
        else:
            probs = {
                key: probs[key] * (1 - market_weight) + implied[key] * market_weight
                for key in PROB_KEYS
            }
            probs = _normalize_positive(probs)
            notes.append("market_weight 已应用")

    adjusted = _normalize_positive(probs)
    return {**adjusted, "note": "；".join(notes)}


def apply_adjustment_with_notes(base_probs: dict, params: dict | None = None, implied_probs: dict | None = None) -> tuple[dict, list[str]]:
    adjusted = apply_adjustment(base_probs, params, implied_probs)
    probs = _prob_only(adjusted)
    notes = [note for note in str(adjusted.get("note", "")).split("；") if note]
    return probs, notes


def _temperature_scale(probs: dict[str, float], temperature: float) -> dict[str, float]:
    if abs(temperature - 1.0) < 1e-12:
        return dict(probs)
    powered = {key: math.exp(math.log(max(probs[key], EPSILON)) / temperature) for key in PROB_KEYS}
    return _normalize_positive(powered)


def _apply_upset_bias(probs: dict[str, float], upset_bias: float) -> dict[str, float]:
    top_key = max(PROB_KEYS, key=lambda key: probs[key])
    adjusted = dict(probs)
    if top_key == "home":
        adjusted["away"] += upset_bias
    elif top_key == "away":
        adjusted["home"] += upset_bias
    else:
        adjusted["home"] += upset_bias / 2
        adjusted["away"] += upset_bias / 2
    return _normalize_positive(adjusted)


def _validate_probs(probs: dict, source: str) -> dict[str, float]:
    if not isinstance(probs, dict):
        raise ValueError(f"{source} must be a probability dict")
    missing = [key for key in PROB_KEYS if key not in probs]
    if missing:
        raise ValueError(f"{source} missing probabilities: {', '.join(missing)}")
    parsed = {}
    for key in PROB_KEYS:
        try:
            value = float(probs[key])
        except (TypeError, ValueError):
            raise ValueError(f"{source}.{key} must be a number") from None
        if value < 0 or value > 1:
            raise ValueError(f"{source}.{key} must be between 0 and 1")
        parsed[key] = value
    return _normalize_positive(parsed)


def _prob_only(probs: dict) -> dict[str, float]:
    return {key: float(probs[key]) for key in PROB_KEYS}


def _normalize_positive(probs: dict[str, float]) -> dict[str, float]:
    clipped = {key: max(float(probs[key]), EPSILON) for key in PROB_KEYS}
    total = sum(clipped.values())
    if total <= 0:
        raise ValueError("Probability total must be positive")
    normalized = {key: clipped[key] / total for key in PROB_KEYS}
    for key, value in normalized.items():
        if value < 0 or value > 1:
            raise ValueError(f"Adjusted probability out of range for {key}")
    return normalized
