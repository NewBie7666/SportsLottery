from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME, LABEL_NAMES, LABELS
from sporttery_national.utils.json_io import write_json

DRAW_MIN_PROBS = [0.26, 0.28, 0.30, 0.32]
DRAW_GAP_TRIGGERS = [0.04, 0.06, 0.08, 0.10]
DRAW_BIASES = [0.00, 0.02, 0.04, 0.06]
REQUIRED_DETAIL_FIELDS = {
    "base_home_win_prob",
    "base_draw_prob",
    "base_away_win_prob",
    "actual_result",
    "top1_pick",
    "top1_prob",
    "second_prob",
}
RESULT_FIELDS = [
    "draw_min_prob",
    "draw_gap_trigger",
    "draw_bias",
    "total_matches",
    "base_top1_accuracy",
    "adjusted_top1_accuracy",
    "base_draw_recall",
    "adjusted_draw_recall",
    "adjusted_draw_precision",
    "base_avg_log_loss",
    "adjusted_avg_log_loss",
    "base_avg_brier",
    "adjusted_avg_brier",
    "changed_pick_count",
    "changed_to_draw_count",
    "is_candidate",
]
FORBIDDEN_DRAW_EXPERIMENT_WORDS = ["必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"]
EPSILON = 1e-15


def run_draw_recall_experiment(backtest_details_path: str | Path, output_dir: str | Path) -> dict:
    rows = load_backtest_details(backtest_details_path)
    results = run_parameter_grid(rows)
    summary = summarize_experiment(rows, results)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_results_csv(target / "draw_experiment_results.csv", results)
    write_json(target / "draw_experiment_summary.json", summary)
    _write_markdown(target / "draw_experiment_report.md", summary)
    return summary


def load_backtest_details(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("backtest details must be a JSON array")
    rows = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"backtest details row {index} must be an object")
        missing = sorted(field for field in REQUIRED_DETAIL_FIELDS if field not in row)
        if missing:
            raise ValueError(f"backtest details row {index} missing fields: {', '.join(missing)}")
        rows.append(_normalize_row(row, index))
    return rows


def run_parameter_grid(rows: list[dict]) -> list[dict]:
    results = []
    base_metrics = _base_metrics(rows)
    for draw_min_prob in DRAW_MIN_PROBS:
        for draw_gap_trigger in DRAW_GAP_TRIGGERS:
            for draw_bias in DRAW_BIASES:
                result = evaluate_strategy(rows, draw_min_prob, draw_gap_trigger, draw_bias, base_metrics)
                results.append(result)
    return results


def evaluate_strategy(
    rows: list[dict],
    draw_min_prob: float,
    draw_gap_trigger: float,
    draw_bias: float,
    base_metrics: dict | None = None,
) -> dict:
    base_metrics = base_metrics or _base_metrics(rows)
    adjusted_rows = [_apply_strategy(row, draw_min_prob, draw_gap_trigger, draw_bias) for row in rows]
    adjusted_metrics = _adjusted_metrics(adjusted_rows)
    result = {
        "draw_min_prob": draw_min_prob,
        "draw_gap_trigger": draw_gap_trigger,
        "draw_bias": draw_bias,
        "total_matches": len(rows),
        **base_metrics,
        **adjusted_metrics,
    }
    result["is_candidate"] = _is_candidate(result)
    return result


def summarize_experiment(rows: list[dict], results: list[dict]) -> dict:
    candidates = [row for row in results if row["is_candidate"]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_matches": len(rows),
        "parameter_grid": {
            "draw_min_prob": DRAW_MIN_PROBS,
            "draw_gap_trigger": DRAW_GAP_TRIGGERS,
            "draw_bias": DRAW_BIASES,
            "result_count": len(results),
        },
        "base_metrics": _base_metrics(rows),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "results": results,
    }


def _normalize_row(row: dict, index: int) -> dict:
    actual_result = _parse_label(row["actual_result"], f"row {index} actual_result")
    top1_pick = _parse_label(row["top1_pick"], f"row {index} top1_pick")
    base_probs = {
        LABEL_HOME: _parse_probability(row["base_home_win_prob"], f"row {index} base_home_win_prob"),
        LABEL_DRAW: _parse_probability(row["base_draw_prob"], f"row {index} base_draw_prob"),
        LABEL_AWAY: _parse_probability(row["base_away_win_prob"], f"row {index} base_away_win_prob"),
    }
    _parse_probability(row["top1_prob"], f"row {index} top1_prob")
    _parse_probability(row["second_prob"], f"row {index} second_prob")
    total = sum(base_probs.values())
    if total <= 0:
        raise ValueError(f"row {index} probabilities must sum to a positive value")
    return {
        **row,
        "actual_result": actual_result,
        "top1_pick": top1_pick,
        "base_probs": {label: value / total for label, value in base_probs.items()},
    }


def _apply_strategy(row: dict, draw_min_prob: float, draw_gap_trigger: float, draw_bias: float) -> dict:
    base = row["base_probs"]
    adjusted = {
        LABEL_HOME: base[LABEL_HOME],
        LABEL_DRAW: max(0.0, base[LABEL_DRAW] + draw_bias),
        LABEL_AWAY: base[LABEL_AWAY],
    }
    total = sum(adjusted.values())
    adjusted = {label: value / total for label, value in adjusted.items()}
    max_label = _top_label(adjusted)
    max_prob = adjusted[max_label]
    if adjusted[LABEL_DRAW] >= draw_min_prob and max_prob - adjusted[LABEL_DRAW] <= draw_gap_trigger:
        adjusted_top1_pick = LABEL_DRAW
    else:
        adjusted_top1_pick = max_label
    actual_prob = adjusted[row["actual_result"]]
    return {
        "actual_result": row["actual_result"],
        "base_top1_pick": row["top1_pick"],
        "adjusted_top1_pick": adjusted_top1_pick,
        "adjusted_actual_prob": actual_prob,
        "adjusted_brier": _brier(adjusted, row["actual_result"]),
        "adjusted_log_loss": _log_loss(actual_prob),
    }


def _base_metrics(rows: list[dict]) -> dict:
    return {
        "base_top1_accuracy": _accuracy(rows, "top1_pick"),
        "base_draw_recall": _draw_recall(rows, "top1_pick"),
        "base_avg_log_loss": _average([_log_loss(row["base_probs"][row["actual_result"]]) for row in rows]),
        "base_avg_brier": _average([_brier(row["base_probs"], row["actual_result"]) for row in rows]),
    }


def _adjusted_metrics(rows: list[dict]) -> dict:
    return {
        "adjusted_top1_accuracy": _accuracy(rows, "adjusted_top1_pick"),
        "adjusted_draw_recall": _draw_recall(rows, "adjusted_top1_pick"),
        "adjusted_draw_precision": _draw_precision(rows),
        "adjusted_avg_log_loss": _average([row["adjusted_log_loss"] for row in rows]),
        "adjusted_avg_brier": _average([row["adjusted_brier"] for row in rows]),
        "changed_pick_count": sum(row["base_top1_pick"] != row["adjusted_top1_pick"] for row in rows),
        "changed_to_draw_count": sum(
            row["base_top1_pick"] != LABEL_DRAW and row["adjusted_top1_pick"] == LABEL_DRAW for row in rows
        ),
    }


def _is_candidate(row: dict) -> bool:
    base_draw_recall = row["base_draw_recall"]
    adjusted_draw_recall = row["adjusted_draw_recall"]
    if base_draw_recall is None or adjusted_draw_recall is None:
        return False
    return (
        adjusted_draw_recall > base_draw_recall
        and row["adjusted_top1_accuracy"] >= row["base_top1_accuracy"] - 0.02
        and row["adjusted_avg_log_loss"] <= row["base_avg_log_loss"] + 0.03
    )


def _accuracy(rows: list[dict], pick_field: str) -> float:
    return sum(row[pick_field] == row["actual_result"] for row in rows) / len(rows) if rows else 0.0


def _draw_recall(rows: list[dict], pick_field: str) -> float | None:
    actual_draws = [row for row in rows if row["actual_result"] == LABEL_DRAW]
    if not actual_draws:
        return None
    return sum(row[pick_field] == LABEL_DRAW for row in actual_draws) / len(actual_draws)


def _draw_precision(rows: list[dict]) -> float | None:
    predicted_draws = [row for row in rows if row["adjusted_top1_pick"] == LABEL_DRAW]
    if not predicted_draws:
        return None
    return sum(row["actual_result"] == LABEL_DRAW for row in predicted_draws) / len(predicted_draws)


def _top_label(probs: dict[int, float]) -> int:
    return max(LABELS, key=lambda label: (probs[label], -LABELS.index(label)))


def _log_loss(prob: float) -> float:
    return -math.log(max(float(prob), EPSILON))


def _brier(probs: dict[int, float], actual_result: int) -> float:
    return sum((probs[label] - (1.0 if label == actual_result else 0.0)) ** 2 for label in LABELS)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _parse_label(value: object, field: str) -> int:
    try:
        label = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be one of 3/1/0") from None
    if label not in LABELS:
        raise ValueError(f"{field} must be one of 3/1/0")
    return label


def _parse_probability(value: object, field: str) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a finite probability") from None
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"{field} must be a finite probability")
    return parsed


def _write_results_csv(path: Path, results: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def _write_markdown(path: Path, summary: dict) -> None:
    candidates = sorted(
        summary["candidates"],
        key=lambda row: (-row["adjusted_draw_recall"], -row["adjusted_top1_accuracy"], row["adjusted_avg_log_loss"]),
    )
    top_results = sorted(
        summary["results"],
        key=lambda row: (-row["adjusted_draw_recall"] if row["adjusted_draw_recall"] is not None else 1, -row["adjusted_top1_accuracy"]),
    )[:20]
    lines = [
        "# 平局召回专项实验报告",
        "",
        "本报告用于本地概率研究和模型诊断，不提供投注建议，不承诺中奖或盈利。",
        "",
        "## 基准指标",
        "",
        f"- Total Matches: {summary['total_matches']}",
        f"- Base Top1 Accuracy: {_fmt(summary['base_metrics']['base_top1_accuracy'])}",
        f"- Base Draw Recall: {_fmt(summary['base_metrics']['base_draw_recall'])}",
        f"- Base Average Log Loss: {_fmt(summary['base_metrics']['base_avg_log_loss'])}",
        f"- Base Average Brier: {_fmt(summary['base_metrics']['base_avg_brier'])}",
        "",
        "## Candidate 策略",
        "",
        "| draw_min_prob | draw_gap_trigger | draw_bias | adjusted accuracy | adjusted draw recall | draw precision | log loss | changed to draw |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in candidates:
        lines.append(_strategy_row(row))
    lines.extend([
        "",
        "## Top 参数结果",
        "",
        "| draw_min_prob | draw_gap_trigger | draw_bias | adjusted accuracy | adjusted draw recall | draw precision | log loss | changed to draw |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in top_results:
        lines.append(_strategy_row(row))
    content = "\n".join(lines) + "\n"
    if any(word in content for word in FORBIDDEN_DRAW_EXPERIMENT_WORDS):
        raise ValueError("draw experiment markdown contains forbidden wording")
    path.write_text(content, encoding="utf-8")


def _strategy_row(row: dict) -> str:
    return (
        f"| {_fmt(row['draw_min_prob'])} | {_fmt(row['draw_gap_trigger'])} | {_fmt(row['draw_bias'])} | "
        f"{_fmt(row['adjusted_top1_accuracy'])} | {_fmt(row['adjusted_draw_recall'])} | "
        f"{_fmt(row['adjusted_draw_precision'])} | {_fmt(row['adjusted_avg_log_loss'])} | {row['changed_to_draw_count']} |"
    )


def _fmt(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
