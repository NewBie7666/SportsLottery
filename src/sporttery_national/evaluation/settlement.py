from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sporttery_national.constants import LABELS, LABEL_AWAY, LABEL_DRAW, LABEL_HOME, LABEL_NAMES, SETTLEMENT_FIELDS
from sporttery_national.utils.json_io import write_json
from sporttery_national.utils.validation import require_columns

REQUIRED_RESULT_COLUMNS = {"issue_id", "match_id", "home_score", "away_score"}
REQUIRED_PREDICTION_COLUMNS = {
    "issue_id",
    "match_id",
    "home_team",
    "away_team",
    "top1_pick",
    "second_pick",
    "probability_gap",
    "base_home_win_prob",
    "base_draw_prob",
    "base_away_win_prob",
    "adjusted_home_win_prob",
    "adjusted_draw_prob",
    "adjusted_away_win_prob",
}
FORBIDDEN_SETTLEMENT_WORDS = ["必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"]
EPSILON = 1e-15


def load_predictions_csv(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        require_columns(set(reader.fieldnames or []), REQUIRED_PREDICTION_COLUMNS, str(path))
        rows = []
        for row in reader:
            row["issue_id"] = _as_key_part(row.get("issue_id"))
            row["match_id"] = _as_key_part(row.get("match_id"))
            row["top1_pick"] = _parse_label(row.get("top1_pick"), "top1_pick")
            row["second_pick"] = _parse_label(row.get("second_pick"), "second_pick")
            if row.get("adjusted_top1_pick") not in (None, ""):
                _require_adjusted_prob_fields(row)
                row["adjusted_top1_pick"] = _parse_label(row.get("adjusted_top1_pick"), "adjusted_top1_pick")
            for field in (
                "probability_gap",
                "base_home_win_prob",
                "base_draw_prob",
                "base_away_win_prob",
                "adjusted_home_win_prob",
                "adjusted_draw_prob",
                "adjusted_away_win_prob",
            ):
                row[field] = _parse_float(row.get(field), field)
            rows.append(row)
    _ensure_unique_keys(rows, "predictions")
    return rows


def load_results_csv(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        require_columns(set(reader.fieldnames or []), REQUIRED_RESULT_COLUMNS, str(path))
        rows = []
        for row in reader:
            home_score = _parse_score(row.get("home_score"), "home_score")
            away_score = _parse_score(row.get("away_score"), "away_score")
            rows.append({
                "issue_id": _as_key_part(row.get("issue_id")),
                "match_id": _as_key_part(row.get("match_id")),
                "home_score": home_score,
                "away_score": away_score,
                "actual_result": derive_actual_result(home_score, away_score),
                "result_status": row.get("result_status", ""),
                "notes": row.get("notes", ""),
            })
    _ensure_unique_keys(rows, "results")
    return rows


def derive_actual_result(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return LABEL_HOME
    if home_score == away_score:
        return LABEL_DRAW
    return LABEL_AWAY


def settle_predictions(predictions: list[dict], results: list[dict]) -> list[dict]:
    _ensure_unique_keys(predictions, "predictions")
    _ensure_unique_keys(results, "results")
    results_by_key = {_key(row): row for row in results}
    missing = [_format_key(_key(row)) for row in predictions if _key(row) not in results_by_key]
    if missing:
        raise ValueError(f"missing results for: {', '.join(missing)}")

    settled_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for prediction in predictions:
        result = results_by_key[_key(prediction)]
        actual_result = _parse_label(result["actual_result"], "actual_result")
        top1_pick = _parse_label(prediction["top1_pick"], "top1_pick")
        second_pick = _parse_label(prediction["second_pick"], "second_pick")
        if prediction.get("adjusted_top1_pick") not in (None, ""):
            _require_adjusted_prob_fields(prediction)
            adjusted_top1_pick = _parse_label(prediction["adjusted_top1_pick"], "adjusted_top1_pick")
        else:
            adjusted_top1_pick = top1_pick
        base_probs = {
            LABEL_HOME: _parse_float(prediction["base_home_win_prob"], "base_home_win_prob"),
            LABEL_DRAW: _parse_float(prediction["base_draw_prob"], "base_draw_prob"),
            LABEL_AWAY: _parse_float(prediction["base_away_win_prob"], "base_away_win_prob"),
        }
        adjusted_probs = {
            LABEL_HOME: _parse_float(prediction["adjusted_home_win_prob"], "adjusted_home_win_prob"),
            LABEL_DRAW: _parse_float(prediction["adjusted_draw_prob"], "adjusted_draw_prob"),
            LABEL_AWAY: _parse_float(prediction["adjusted_away_win_prob"], "adjusted_away_win_prob"),
        }
        base_actual_prob = base_probs[actual_result]
        adjusted_actual_prob = adjusted_probs[actual_result]
        row = {
            "issue_id": _as_key_part(prediction.get("issue_id")),
            "match_id": _as_key_part(prediction.get("match_id")),
            "home_team": prediction.get("home_team", ""),
            "away_team": prediction.get("away_team", ""),
            "competition": prediction.get("competition", ""),
            "home_score": result["home_score"],
            "away_score": result["away_score"],
            "actual_result": actual_result,
            "actual_label": LABEL_NAMES[actual_result],
            "top1_pick": top1_pick,
            "top1_label": prediction.get("top1_label", LABEL_NAMES[top1_pick]),
            "second_pick": second_pick,
            "confidence": prediction.get("confidence", ""),
            "probability_gap": _parse_float(prediction.get("probability_gap", 0.0), "probability_gap"),
            "base_home_win_prob": base_probs[LABEL_HOME],
            "base_draw_prob": base_probs[LABEL_DRAW],
            "base_away_win_prob": base_probs[LABEL_AWAY],
            "adjusted_home_win_prob": adjusted_probs[LABEL_HOME],
            "adjusted_draw_prob": adjusted_probs[LABEL_DRAW],
            "adjusted_away_win_prob": adjusted_probs[LABEL_AWAY],
            "base_hit": top1_pick == actual_result,
            "adjusted_hit": adjusted_top1_pick == actual_result,
            "base_actual_prob": base_actual_prob,
            "adjusted_actual_prob": adjusted_actual_prob,
            "base_log_loss": compute_log_loss(base_actual_prob),
            "adjusted_log_loss": compute_log_loss(adjusted_actual_prob),
            "base_brier": compute_brier_score(base_probs, actual_result),
            "adjusted_brier": compute_brier_score(adjusted_probs, actual_result),
            "model_version": prediction.get("model_version", ""),
            "feature_version": prediction.get("feature_version", ""),
            "settled_at": settled_at,
        }
        rows.append(row)
    return rows


def compute_log_loss(prob: float) -> float:
    return -math.log(max(float(prob), EPSILON))


def compute_brier_score(probs: dict[int, float], actual_result: int) -> float:
    actual = _parse_label(actual_result, "actual_result")
    return sum((float(probs[label]) - (1.0 if label == actual else 0.0)) ** 2 for label in LABELS)


def summarize_settlement(rows: list[dict]) -> dict:
    total = len(rows)
    errors = [row for row in rows if not row["base_hit"]]
    return {
        "total_matches": total,
        "base_top1_accuracy": _avg_bool(rows, "base_hit"),
        "adjusted_top1_accuracy": _avg_bool(rows, "adjusted_hit"),
        "base_avg_log_loss": _avg(rows, "base_log_loss"),
        "adjusted_avg_log_loss": _avg(rows, "adjusted_log_loss"),
        "base_avg_brier": _avg(rows, "base_brier"),
        "adjusted_avg_brier": _avg(rows, "adjusted_brier"),
        "by_confidence": _group_summary(rows, "confidence"),
        "by_competition": _group_summary(rows, "competition"),
        "error_count": len(errors),
    }


def write_settlement_outputs(output: str | Path, rows: list[dict]) -> dict:
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = summarize_settlement(rows)
    _write_csv(target / "settlements.csv", rows)
    _write_json(target / "settlements.json", [{field: row.get(field) for field in SETTLEMENT_FIELDS} for row in rows])
    _write_json(target / "settlement_summary.json", summary)
    _write_markdown(target / "settlements.md", rows, summary)
    return summary


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SETTLEMENT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, data: object) -> None:
    write_json(path, data)


def _write_markdown(path: Path, rows: list[dict], summary: dict) -> None:
    lines = [
        "# 赛后结算报告",
        "",
        "本报告只用于赛后评估预测表现，不提供投注建议，不承诺中奖或盈利。",
        "",
        "## 总览",
        "",
        f"- Total Matches: {summary['total_matches']}",
        f"- Base Top1 Accuracy: {summary['base_top1_accuracy']:.4f}",
        f"- Adjusted Top1 Accuracy: {summary['adjusted_top1_accuracy']:.4f}",
        f"- Base Average Log Loss: {summary['base_avg_log_loss']:.4f}",
        f"- Adjusted Average Log Loss: {summary['adjusted_avg_log_loss']:.4f}",
        f"- Base Average Brier Score: {summary['base_avg_brier']:.4f}",
        f"- Adjusted Average Brier Score: {summary['adjusted_avg_brier']:.4f}",
        "",
        "## Confidence 分组",
        "",
        "| confidence | 场次 | 命中率 | 平均 Log Loss |",
        "|---|---:|---:|---:|",
    ]
    for name, item in summary["by_confidence"].items():
        lines.append(f"| {name} | {item['matches']} | {item['accuracy']:.4f} | {item['avg_log_loss']:.4f} |")
    lines.extend([
        "",
        "## Competition 分组",
        "",
        "| competition | 场次 | 命中率 | 平均 Log Loss |",
        "|---|---:|---:|---:|",
    ])
    for name, item in summary["by_competition"].items():
        lines.append(f"| {name} | {item['matches']} | {item['accuracy']:.4f} | {item['avg_log_loss']:.4f} |")
    lines.extend([
        "",
        "## 错误样例",
        "",
        "| 比赛 | 主队 | 客队 | 比分 | 首选 | 实际 | confidence |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        if row["base_hit"]:
            continue
        lines.append(
            f"| {row['issue_id']}-{row['match_id']} | {row['home_team']} | {row['away_team']} | "
            f"{row['home_score']}:{row['away_score']} | {row['top1_label']} | {row['actual_label']} | {row['confidence']} |"
        )
    content = "\n".join(lines) + "\n"
    if any(word in content for word in FORBIDDEN_SETTLEMENT_WORDS):
        raise ValueError("settlement markdown contains forbidden wording")
    path.write_text(content, encoding="utf-8")


def _group_summary(rows: list[dict], field: str) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field) or "unknown")].append(row)
    return {
        name: {
            "matches": len(items),
            "accuracy": _avg_bool(items, "base_hit"),
            "avg_log_loss": _avg(items, "base_log_loss"),
        }
        for name, items in sorted(groups.items())
    }


def _ensure_unique_keys(rows: list[dict], source: str) -> None:
    counts = Counter(_key(row) for row in rows)
    duplicates = [_format_key(key) for key, count in counts.items() if count > 1]
    if duplicates:
        raise ValueError(f"{source} contains duplicate issue_id + match_id: {', '.join(duplicates)}")


def _key(row: dict) -> tuple[str, str]:
    return (_as_key_part(row.get("issue_id")), _as_key_part(row.get("match_id")))


def _format_key(key: tuple[str, str]) -> str:
    return f"{key[0]}+{key[1]}"


def _as_key_part(value: object) -> str:
    return "" if value is None else str(value).strip()


def _parse_score(value: object, field: str) -> int:
    try:
        score = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a non-negative integer") from None
    if score < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return score


def _parse_label(value: object, field: str) -> int:
    try:
        label = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be one of 3/1/0") from None
    if label not in LABELS:
        raise ValueError(f"{field} must be one of 3/1/0")
    return label


def _parse_float(value: object, field: str) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number") from None


def _require_adjusted_prob_fields(row: dict) -> None:
    required = ("adjusted_home_win_prob", "adjusted_draw_prob", "adjusted_away_win_prob")
    missing = [field for field in required if row.get(field) in (None, "")]
    if missing:
        raise ValueError(f"adjusted_top1_pick requires adjusted probability fields: {', '.join(missing)}")
    for field in required:
        _parse_float(row.get(field), field)


def _avg(rows: list[dict], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows) if rows else 0.0


def _avg_bool(rows: list[dict], field: str) -> float:
    return sum(bool(row[field]) for row in rows) / len(rows) if rows else 0.0
