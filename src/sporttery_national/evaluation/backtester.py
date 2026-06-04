from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME, LABELS
from sporttery_national.evaluation.calibration import calibration_buckets
from sporttery_national.evaluation.metrics import brier_score, log_loss, top1_accuracy
from sporttery_national.features.feature_builder import FeatureBuilder
from sporttery_national.models.predictor import _probabilities
from sporttery_national.utils.storage import read_records


def backtest(data_path: str | Path, output_dir: str | Path, min_history: int = 20) -> dict:
    matches = sorted(read_records(data_path), key=lambda row: row["date"])
    builder = FeatureBuilder()
    rows = []
    competition_rows: dict[str, list[dict]] = defaultdict(list)
    for index, match in enumerate(matches):
        if index >= min_history:
            features = builder.build_before_match(match)
            probs_raw = _probabilities(features)
            probs = {LABEL_HOME: probs_raw["home"], LABEL_DRAW: probs_raw["draw"], LABEL_AWAY: probs_raw["away"]}
            predicted = max(LABELS, key=lambda label: probs[label])
            row = {"actual": int(match["result"]), "predicted": predicted, "probs": probs}
            rows.append(row)
            competition_rows[match.get("competition", "")].append(row)
        builder.update_after_match(match)

    confusion = Counter((row["actual"], row["predicted"]) for row in rows)
    summary = {
        "matches": len(rows),
        "log_loss": log_loss(rows),
        "brier_score": brier_score(rows),
        "top1_accuracy": top1_accuracy(rows),
        "calibration_buckets": calibration_buckets(rows),
        "confusion_matrix": {f"{actual}->{predicted}": count for (actual, predicted), count in confusion.items()},
        "by_competition": {
            competition: {"matches": len(items), "log_loss": log_loss(items), "brier_score": brier_score(items), "top1_accuracy": top1_accuracy(items)}
            for competition, items in competition_rows.items()
        },
    }
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "backtest_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
