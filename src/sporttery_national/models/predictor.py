from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from sporttery_national.adjustment.interface import apply_adjustment
from sporttery_national.constants import LABELS, LABEL_NAMES
from sporttery_national.features.elo import EloRatings
from sporttery_national.features.feature_builder import FeatureBuilder
from sporttery_national.models.trainer import FEATURE_VERSION, MODEL_VERSION
from sporttery_national.utils.storage import read_records


def load_builder(model_dir: str | Path, history_path: str | Path | None = None) -> FeatureBuilder:
    model_path = Path(model_dir) / "elo_state.json"
    elo = EloRatings.from_json(json.loads(model_path.read_text(encoding="utf-8"))) if model_path.exists() else EloRatings()
    builder = FeatureBuilder(elo=elo)
    if history_path:
        builder.warmup(read_records(history_path))
    return builder


def predict_fixtures(fixtures: list[dict], model_dir: str | Path, history_path: str | Path | None = None) -> list[dict]:
    builder = load_builder(model_dir, history_path)
    rows = []
    created_at = datetime.now(timezone.utc).isoformat()
    for fixture in fixtures:
        features = builder.build_before_match({"home_team": fixture["home_team"], "away_team": fixture["away_team"], "date": fixture["date"], "competition": fixture.get("competition", ""), "neutral": fixture.get("neutral", False)})
        base = _probabilities(features)
        adjusted = apply_adjustment(base)
        top_label = max(LABELS, key=lambda label: adjusted[_key(label)])
        confidence = _confidence(sorted(adjusted.values(), reverse=True))
        row = dict(fixture)
        row.update({
            "base_home_win_prob": base["home"],
            "base_draw_prob": base["draw"],
            "base_away_win_prob": base["away"],
            "adjusted_home_win_prob": adjusted["home"],
            "adjusted_draw_prob": adjusted["draw"],
            "adjusted_away_win_prob": adjusted["away"],
            "top1_pick": top_label,
            "top1_label": LABEL_NAMES[top_label],
            "confidence": confidence,
            "risk_note": "概率分析结果，仅供研究；不承诺中奖或盈利。",
            "prob_diff_home": _diff(adjusted["home"], fixture.get("implied_home_win_prob")),
            "prob_diff_draw": _diff(adjusted["draw"], fixture.get("implied_draw_prob")),
            "prob_diff_away": _diff(adjusted["away"], fixture.get("implied_away_win_prob")),
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "created_at": created_at,
        })
        rows.append(row)
    return rows


def _probabilities(features: dict) -> dict[str, float]:
    diff = features["elo_diff"] + (35 if features["home_advantage"] else 0)
    home_logit = diff / 400
    away_logit = -diff / 400
    draw_logit = -0.15 - abs(diff) / 900
    values = [math.exp(home_logit), math.exp(draw_logit), math.exp(away_logit)]
    total = sum(values)
    return {"home": values[0] / total, "draw": values[1] / total, "away": values[2] / total}


def _key(label: int) -> str:
    return "home" if label == 3 else "draw" if label == 1 else "away"


def _confidence(sorted_probs: list[float]) -> str:
    gap = sorted_probs[0] - sorted_probs[1]
    if gap >= 0.18:
        return "high"
    if gap >= 0.08:
        return "medium"
    return "low"


def _diff(prob: float, implied: float | None) -> float | None:
    return None if implied is None else prob - implied
