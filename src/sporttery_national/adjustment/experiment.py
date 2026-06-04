from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sporttery_national.adjustment.adjuster import MARKET_SKIPPED_NOTE, apply_adjustment
from sporttery_national.adjustment.params import load_params
from sporttery_national.constants import ADJUSTED_PREDICTION_FIELDS, LABEL_NAMES, PREDICTION_FIELDS
from sporttery_national.models.prediction_explain import confidence_from_prediction, rank_outcomes
from sporttery_national.utils.validation import require_columns

FORBIDDEN_ADJUSTMENT_WORDS = ["必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"]


def run_adjustment_experiment(predictions_path: str | Path, params_path: str | Path, output_dir: str | Path) -> dict:
    params = load_params(params_path)
    rows = load_prediction_rows(predictions_path)
    adjusted_rows = adjust_prediction_rows(rows, params)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_csv(output / "adjusted_predictions.csv", adjusted_rows)
    _write_json(output / "adjusted_predictions.json", adjusted_rows)
    summary = summarize_adjustments(adjusted_rows, params)
    _write_markdown(output / "adjustment_report.md", summary, adjusted_rows)
    return summary


def load_prediction_rows(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        require_columns(set(reader.fieldnames or []), set(PREDICTION_FIELDS), str(path))
        return [dict(row) for row in reader]


def adjust_prediction_rows(rows: list[dict], params: dict) -> list[dict]:
    created_at = datetime.now(timezone.utc).isoformat()
    output = []
    for row in rows:
        original = dict(row)
        base_probs = {
            "home": _parse_float(row.get("base_home_win_prob"), "base_home_win_prob"),
            "draw": _parse_float(row.get("base_draw_prob"), "base_draw_prob"),
            "away": _parse_float(row.get("base_away_win_prob"), "base_away_win_prob"),
        }
        implied_probs = _implied_probs(row)
        adjusted_result = apply_adjustment(base_probs, params, implied_probs)
        adjusted = _prob_only(adjusted_result)
        ranking = rank_outcomes(adjusted)
        original.update({
            "adjusted_home_win_prob": adjusted["home"],
            "adjusted_draw_prob": adjusted["draw"],
            "adjusted_away_win_prob": adjusted["away"],
            "experiment_name": params["experiment_name"],
            "adjustment_params": json.dumps(params, ensure_ascii=False, sort_keys=True),
            "adjusted_top1_pick": ranking["top1_pick"],
            "adjusted_top1_label": LABEL_NAMES[ranking["top1_pick"]],
            "adjusted_second_pick": ranking["second_pick"],
            "adjusted_probability_gap": ranking["probability_gap"],
            "adjusted_confidence": confidence_from_prediction(
                ranking["top1_prob"],
                ranking["second_prob"],
                competition=row.get("competition", ""),
                neutral=_parse_bool(row.get("neutral")),
            ),
            "adjustment_note": adjusted_result.get("note", ""),
            "adjusted_created_at": created_at,
        })
        output.append(original)
    return output


def summarize_adjustments(rows: list[dict], params: dict) -> dict:
    changed = [row for row in rows if str(row.get("top1_pick")) != str(row.get("adjusted_top1_pick"))]
    changed_limited = changed[:20]
    market_skipped = sum(MARKET_SKIPPED_NOTE in str(row.get("adjustment_note", "")) for row in rows)
    shifts = [_prob_shifts(row) for row in rows]
    avg_home_shift = _avg_values([item["home"] for item in shifts])
    avg_draw_shift = _avg_values([item["draw"] for item in shifts])
    avg_away_shift = _avg_values([item["away"] for item in shifts])
    avg_prob_shift = _avg_values([(item["home"] + item["draw"] + item["away"]) / 3 for item in shifts])
    return {
        "experiment_name": params["experiment_name"],
        "adjustment_params": params,
        "total_matches": len(rows),
        "base_top1_distribution": dict(Counter(str(row.get("top1_pick")) for row in rows)),
        "adjusted_top1_distribution": dict(Counter(str(row.get("adjusted_top1_pick")) for row in rows)),
        "changed_pick_count": len(changed),
        "changed_top1_count": len(changed),
        "changed_picks": [_changed_pick_summary(row) for row in changed_limited],
        "market_skipped_count": market_skipped,
        "market_weight_skipped_count": market_skipped,
        "avg_abs_home_shift": avg_home_shift,
        "avg_abs_draw_shift": avg_draw_shift,
        "avg_abs_away_shift": avg_away_shift,
        "avg_abs_prob_shift": avg_prob_shift,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ADJUSTED_PREDICTION_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict]) -> None:
    cleaned = [{field: row.get(field) for field in ADJUSTED_PREDICTION_FIELDS} for row in rows]
    path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path: Path, summary: dict, rows: list[dict]) -> None:
    lines = [
        "# 参数实验报告",
        "",
        "仅供概率研究，不承诺中奖或盈利。",
        "",
        f"- 实验名称: {summary['experiment_name']}",
        f"- 总场次: {summary['total_matches']}",
        f"- top1 变化场次: {summary['changed_top1_count']}",
        f"- odds 缺失导致 market_weight 未生效场次: {summary['market_weight_skipped_count']}",
        f"- home 平均绝对概率变动: {summary['avg_abs_home_shift']:.6f}",
        f"- draw 平均绝对概率变动: {summary['avg_abs_draw_shift']:.6f}",
        f"- away 平均绝对概率变动: {summary['avg_abs_away_shift']:.6f}",
        f"- 三项平均绝对概率变动: {summary['avg_abs_prob_shift']:.6f}",
        "",
        "## 参数",
        "",
        "| 参数 | 值 |",
        "|---|---:|",
    ]
    for key, value in summary["adjustment_params"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "## Top1 分布",
        "",
        f"- base: {json.dumps(summary['base_top1_distribution'], ensure_ascii=False, sort_keys=True)}",
        f"- adjusted: {json.dumps(summary['adjusted_top1_distribution'], ensure_ascii=False, sort_keys=True)}",
        "",
        "## Changed Picks",
        "",
        "| match_id | 主队 | 客队 | base top1 | adjusted top1 | base probabilities | adjusted probabilities |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in summary["changed_picks"]:
        base_probs = row["base_probabilities"]
        adjusted_probs = row["adjusted_probabilities"]
        lines.append(
            f"| {row.get('match_id', '')} | {row.get('home_team', '')} | {row.get('away_team', '')} | "
            f"{row.get('top1_label', '')} | {row.get('adjusted_top1_label', '')} | {base_probs} | {adjusted_probs} |"
        )
    content = "\n".join(lines) + "\n"
    if any(word in content for word in FORBIDDEN_ADJUSTMENT_WORDS):
        raise ValueError("adjustment markdown contains forbidden wording")
    path.write_text(content, encoding="utf-8")


def _implied_probs(row: dict) -> dict | None:
    values = {
        "home": _optional_float(row.get("implied_home_win_prob")),
        "draw": _optional_float(row.get("implied_draw_prob")),
        "away": _optional_float(row.get("implied_away_win_prob")),
    }
    if any(value is None for value in values.values()):
        return None
    return values


def _prob_only(result: dict) -> dict[str, float]:
    return {key: float(result[key]) for key in ("home", "draw", "away")}


def _prob_shifts(row: dict) -> dict[str, float]:
    return {
        "home": abs(_parse_float(row.get("adjusted_home_win_prob"), "adjusted_home_win_prob") - _parse_float(row.get("base_home_win_prob"), "base_home_win_prob")),
        "draw": abs(_parse_float(row.get("adjusted_draw_prob"), "adjusted_draw_prob") - _parse_float(row.get("base_draw_prob"), "base_draw_prob")),
        "away": abs(_parse_float(row.get("adjusted_away_win_prob"), "adjusted_away_win_prob") - _parse_float(row.get("base_away_win_prob"), "base_away_win_prob")),
    }


def _avg_values(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _changed_pick_summary(row: dict) -> dict:
    return {
        "issue_id": row.get("issue_id", ""),
        "match_id": row.get("match_id", ""),
        "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""),
        "top1_pick": row.get("top1_pick", ""),
        "top1_label": row.get("top1_label", ""),
        "adjusted_top1_pick": row.get("adjusted_top1_pick", ""),
        "adjusted_top1_label": row.get("adjusted_top1_label", ""),
        "base_probabilities": f"{_fmt(row.get('base_home_win_prob'))}/{_fmt(row.get('base_draw_prob'))}/{_fmt(row.get('base_away_win_prob'))}",
        "adjusted_probabilities": f"{_fmt(row.get('adjusted_home_win_prob'))}/{_fmt(row.get('adjusted_draw_prob'))}/{_fmt(row.get('adjusted_away_win_prob'))}",
    }


def _parse_float(value: object, field: str) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number") from None


def _optional_float(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).strip())


def _parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _fmt(value: object) -> str:
    return f"{float(value):.3f}"
