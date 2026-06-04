from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sporttery_national.features.feature_builder import FeatureBuilder
from sporttery_national.utils.storage import read_records

MODEL_VERSION = "elo-softmax-v1"
FEATURE_VERSION = "national-feature-v1"


def train(data_path: str | Path, model_dir: str | Path) -> dict:
    matches = sorted(read_records(data_path), key=lambda row: row["date"])
    builder = FeatureBuilder()
    for match in matches:
        builder.update_after_match(match)

    target = Path(model_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "elo_state.json").write_text(json.dumps(builder.elo.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_start": matches[0]["date"] if matches else None,
        "training_end": matches[-1]["date"] if matches else None,
        "training_samples": len(matches),
        "label_distribution": dict(Counter(str(row["result"]) for row in matches)),
    }
    (target / "training_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "feature_config.json").write_text(json.dumps({"form_window": 10, "labels": [3, 1, 0]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "model.pkl").write_text(json.dumps({"type": MODEL_VERSION}, indent=2), encoding="utf-8")
    (target / "calibrator.pkl").write_text(json.dumps({"type": "identity"}, indent=2), encoding="utf-8")
    return metadata
