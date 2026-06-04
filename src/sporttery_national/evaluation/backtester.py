from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sporttery_national.constants import BACKTEST_DETAIL_FIELDS, LABEL_AWAY, LABEL_DRAW, LABEL_HOME, LABELS, LABEL_NAMES
from sporttery_national.features.feature_builder import FeatureBuilder
from sporttery_national.models.prediction_explain import confidence_from_prediction, rank_outcomes
from sporttery_national.models.predictor import _probabilities
from sporttery_national.models.trainer import FEATURE_VERSION, MODEL_VERSION
from sporttery_national.utils.storage import read_records

FORBIDDEN_BACKTEST_WORDS = ["必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"]
CALIBRATION_BINS = [
    ("0.30-0.40", 0.30, 0.40),
    ("0.40-0.50", 0.40, 0.50),
    ("0.50-0.60", 0.50, 0.60),
    ("0.60-0.70", 0.60, 0.70),
    ("0.70+", 0.70, None),
]


def backtest(data_path: str | Path, output_dir: str | Path, min_history: int = 20) -> dict:
    matches = sorted(read_records(data_path), key=lambda row: row["date"])
    builder = FeatureBuilder()
    details = []
    for index, match in enumerate(matches):
        if index >= min_history:
            features = builder.build_before_match(match)
            probs_raw = _probabilities(features)
            ranking = rank_outcomes(probs_raw)
            actual = int(match["result"])
            top1_pick = int(ranking["top1_pick"])
            actual_prob = _prob_for_label(probs_raw, actual)
            detail = {
                "synthetic_backtest_id": f"BT{len(details) + 1:06d}",
                "date": match["date"],
                "competition": match.get("competition", ""),
                "home_team": match.get("home_team", ""),
                "away_team": match.get("away_team", ""),
                "neutral": bool(match.get("neutral", False)),
                "actual_result": actual,
                "actual_label": LABEL_NAMES[actual],
                "base_home_win_prob": probs_raw["home"],
                "base_draw_prob": probs_raw["draw"],
                "base_away_win_prob": probs_raw["away"],
                "top1_pick": top1_pick,
                "top1_label": LABEL_NAMES[top1_pick],
                "top1_prob": ranking["top1_prob"],
                "second_pick": int(ranking["second_pick"]),
                "second_prob": ranking["second_prob"],
                "probability_gap": ranking["probability_gap"],
                "confidence": confidence_from_prediction(
                    ranking["top1_prob"],
                    ranking["second_prob"],
                    competition=match.get("competition", ""),
                    neutral=bool(match.get("neutral", False)),
                ),
                "hit": top1_pick == actual,
                "actual_prob": actual_prob,
                "log_loss": compute_log_loss(actual_prob),
                "brier": compute_brier_score(probs_raw, actual),
                "model_version": MODEL_VERSION,
                "feature_version": FEATURE_VERSION,
            }
            details.append(detail)
        builder.update_after_match(match)

    summary = summarize_backtest_details(details, matches, min_history)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_details_csv(target / "backtest_details.csv", details)
    _write_json(target / "backtest_details.json", [{field: row.get(field) for field in BACKTEST_DETAIL_FIELDS} for row in details])
    _write_json(target / "backtest_summary.json", summary)
    _write_markdown_report(target / "backtest_report.md", summary, details)
    return summary


def summarize_backtest_details(details: list[dict], matches: list[dict] | None = None, min_history: int = 20) -> dict:
    matches = matches or []
    generated_at = datetime.now(timezone.utc).isoformat()
    total = len(details)
    avg_log_loss = _avg(details, "log_loss")
    avg_brier = _avg(details, "brier")
    accuracy = _accuracy(details)
    result_distribution = _count_labels(details, "actual_result")
    top1_distribution = _count_labels(details, "top1_pick")
    metadata = {
        "data_start_date": matches[0]["date"] if matches else (details[0]["date"] if details else None),
        "data_end_date": matches[-1]["date"] if matches else (details[-1]["date"] if details else None),
        "backtest_start_date": details[0]["date"] if details else None,
        "backtest_end_date": details[-1]["date"] if details else None,
        "min_history": min_history,
        "generated_at": generated_at,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
    }
    summary = {
        "metadata": metadata,
        "total_matches": total,
        "top1_accuracy": accuracy,
        "avg_log_loss": avg_log_loss,
        "avg_brier": avg_brier,
        "result_distribution": result_distribution,
        "top1_distribution": top1_distribution,
        "draw_recall": _recall(details, LABEL_DRAW),
        "home_win_recall": _recall(details, LABEL_HOME),
        "away_win_recall": _recall(details, LABEL_AWAY),
        "draw_bias_diagnostics": _draw_bias(details),
        "prediction_bias": _prediction_bias(details),
        "recent_windows": _recent_windows(details, metadata["backtest_end_date"]),
        "confusion_matrix": _confusion_matrix(details),
        "by_year": _group_by(details, lambda row: str(row["date"])[:4]),
        "by_competition": _group_by(details, lambda row: str(row.get("competition") or "unknown")),
        "by_confidence": _group_by(details, lambda row: str(row.get("confidence") or "unknown")),
        "by_neutral": _group_by(details, lambda row: str(row.get("neutral"))),
        "calibration_bins": _calibration_bins(details),
    }
    summary.update({
        "matches": total,
        "log_loss": avg_log_loss,
        "brier_score": avg_brier,
        "calibration_buckets": summary["calibration_bins"],
    })
    return summary


def compute_log_loss(prob: float) -> float:
    return -math.log(max(float(prob), 1e-15))


def compute_brier_score(probs: dict[str, float], actual_result: int) -> float:
    expected = {
        "home": 1.0 if actual_result == LABEL_HOME else 0.0,
        "draw": 1.0 if actual_result == LABEL_DRAW else 0.0,
        "away": 1.0 if actual_result == LABEL_AWAY else 0.0,
    }
    return sum((float(probs[key]) - expected[key]) ** 2 for key in ("home", "draw", "away"))


def _prob_for_label(probs: dict[str, float], label: int) -> float:
    if label == LABEL_HOME:
        return probs["home"]
    if label == LABEL_DRAW:
        return probs["draw"]
    return probs["away"]


def _write_details_csv(path: Path, details: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=BACKTEST_DETAIL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(details)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown_report(path: Path, summary: dict, details: list[dict]) -> None:
    lines = [
        "# 回测诊断报告",
        "",
        "本报告用于模型诊断和赛后复盘，不提供投注建议，不承诺中奖或盈利。",
        "",
        "## 总体指标",
        "",
        f"- Total Matches: {summary['total_matches']}",
        f"- Top1 Accuracy: {_fmt(summary['top1_accuracy'])}",
        f"- Average Log Loss: {_fmt(summary['avg_log_loss'])}",
        f"- Average Brier: {_fmt(summary['avg_brier'])}",
        f"- Draw Recall: {_fmt(summary['draw_recall'])}",
        "",
        "## Metadata",
        "",
    ]
    for key, value in summary["metadata"].items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## 平局偏差诊断",
        "",
    ])
    for key, value in summary["draw_bias_diagnostics"].items():
        lines.append(f"- {key}: {_fmt(value)}")

    lines.extend([
        "",
        "## 预测分布偏差",
        "",
        "| 结果 | 实际占比 | Top1占比 | 差值 |",
        "|---|---:|---:|---:|",
    ])
    for label in _label_keys():
        lines.append(
            f"| {LABEL_NAMES[int(label)]} | {_fmt(summary['prediction_bias']['actual_distribution'][label])} | "
            f"{_fmt(summary['prediction_bias']['top1_distribution'][label])} | {_fmt(summary['prediction_bias']['distribution_gap'][label])} |"
        )

    lines.extend([
        "",
        "## 近期窗口",
        "",
        "| 窗口 | 场次 | 命中率 | 平均 Log Loss | 平均 Brier | 平局召回 |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for name, item in summary["recent_windows"].items():
        lines.append(f"| {name} | {item['matches']} | {_fmt(item['accuracy'])} | {_fmt(item['avg_log_loss'])} | {_fmt(item['avg_brier'])} | {_fmt(item['draw_recall'])} |")

    lines.extend([
        "",
        "## 混淆矩阵",
        "",
        "| actual \\ top1 | 主胜 | 平 | 客胜 |",
        "|---|---:|---:|---:|",
    ])
    for actual in _label_keys():
        row = summary["confusion_matrix"][actual]
        lines.append(f"| {LABEL_NAMES[int(actual)]} | {row['3']} | {row['1']} | {row['0']} |")

    _append_group_table(lines, "Confidence 分组", summary["by_confidence"])
    _append_group_table(lines, "Neutral 分组", summary["by_neutral"])
    _append_group_table(lines, "Year 分组", summary["by_year"])
    _append_group_table(lines, "Competition 分组", _markdown_competitions(summary["by_competition"]))

    lines.extend([
        "",
        "## 概率校准分桶",
        "",
        "| 分桶 | 场次 | 平均 Top1 概率 | 命中率 | 平均 Log Loss | confidence 分布 |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for item in summary["calibration_bins"]:
        lines.append(
            f"| {item['bin']} | {item['matches']} | {_fmt(item['avg_top1_prob'])} | {_fmt(item['accuracy'])} | "
            f"{_fmt(item['avg_log_loss'])} | {json.dumps(item['confidence_distribution'], ensure_ascii=False)} |"
        )

    lines.extend([
        "",
        "## 高置信错误样例",
        "",
        "| 日期 | 赛事 | 主队 | 客队 | 实际 | 首选 | 主胜 | 平 | 客胜 | 概率差距 | Log Loss |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in _high_confidence_errors(details):
        lines.append(
            f"| {row['date']} | {row['competition']} | {row['home_team']} | {row['away_team']} | "
            f"{row['actual_label']} | {row['top1_label']} | {row['base_home_win_prob']:.3f} | "
            f"{row['base_draw_prob']:.3f} | {row['base_away_win_prob']:.3f} | {row['probability_gap']:.3f} | {row['log_loss']:.3f} |"
        )
    content = "\n".join(lines) + "\n"
    if any(word in content for word in FORBIDDEN_BACKTEST_WORDS):
        raise ValueError("backtest markdown contains forbidden wording")
    path.write_text(content, encoding="utf-8")


def _append_group_table(lines: list[str], title: str, group: dict) -> None:
    lines.extend(["", f"## {title}", "", "| 分组 | 场次 | 命中率 | 平均 Log Loss | 平均 Brier |", "|---|---:|---:|---:|---:|"])
    for name, item in group.items():
        lines.append(f"| {name} | {item['matches']} | {_fmt(item['accuracy'])} | {_fmt(item['avg_log_loss'])} | {_fmt(item['avg_brier'])} |")


def _markdown_competitions(group: dict) -> dict:
    eligible = {name: item for name, item in group.items() if item["matches"] >= 30}
    source = eligible if eligible else group
    ranked = sorted(source.items(), key=lambda item: (-item[1]["matches"], item[0]))[:20]
    return dict(ranked)


def _high_confidence_errors(details: list[dict]) -> list[dict]:
    rows = [
        row for row in details
        if not row["hit"] and (row["confidence"] == "high" or float(row["probability_gap"]) >= 0.18)
    ]
    return sorted(rows, key=lambda row: float(row["log_loss"]), reverse=True)[:20]


def _group_by(details: list[dict], key_fn) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in details:
        groups[key_fn(row)].append(row)
    return {name: _metric_block(rows) for name, rows in sorted(groups.items())}


def _metric_block(rows: list[dict]) -> dict:
    return {
        "matches": len(rows),
        "accuracy": _accuracy(rows),
        "avg_log_loss": _avg(rows, "log_loss"),
        "avg_brier": _avg(rows, "brier"),
    }


def _recent_windows(details: list[dict], backtest_end_date: str | None) -> dict:
    if not backtest_end_date:
        return {name: _empty_window() for name in ("since_2000", "last_10_years", "last_5_years")}
    end_year = int(backtest_end_date[:4])
    windows = {
        "since_2000": [row for row in details if str(row["date"]) >= "2000-01-01"],
        "last_10_years": [row for row in details if int(str(row["date"])[:4]) >= end_year - 10],
        "last_5_years": [row for row in details if int(str(row["date"])[:4]) >= end_year - 5],
    }
    return {name: _window_block(rows) for name, rows in windows.items()}


def _window_block(rows: list[dict]) -> dict:
    if not rows:
        return _empty_window()
    return {**_metric_block(rows), "draw_recall": _recall(rows, LABEL_DRAW)}


def _empty_window() -> dict:
    return {"matches": 0, "accuracy": None, "avg_log_loss": None, "avg_brier": None, "draw_recall": None}


def _calibration_bins(details: list[dict]) -> list[dict]:
    output = []
    for name, low, high in CALIBRATION_BINS:
        if high is None:
            rows = [row for row in details if float(row["top1_prob"]) >= low]
        else:
            rows = [row for row in details if low <= float(row["top1_prob"]) < high]
        output.append({
            "bin": name,
            "matches": len(rows),
            "avg_top1_prob": _avg(rows, "top1_prob") if rows else None,
            "accuracy": _accuracy(rows) if rows else None,
            "avg_log_loss": _avg(rows, "log_loss") if rows else None,
            "confidence_distribution": dict(Counter(row["confidence"] for row in rows)),
        })
    return output


def _confusion_matrix(details: list[dict]) -> dict:
    matrix = {actual: {predicted: 0 for predicted in _label_keys()} for actual in _label_keys()}
    for row in details:
        matrix[str(row["actual_result"])][str(row["top1_pick"])] += 1
    return matrix


def _draw_bias(details: list[dict]) -> dict:
    total = len(details)
    actual_draws = [row for row in details if row["actual_result"] == LABEL_DRAW]
    draw_actual_rate = len(actual_draws) / total if total else 0.0
    draw_top1_rate = sum(row["top1_pick"] == LABEL_DRAW for row in details) / total if total else 0.0
    return {
        "draw_actual_rate": draw_actual_rate,
        "draw_top1_rate": draw_top1_rate,
        "draw_under_prediction_gap": draw_actual_rate - draw_top1_rate,
        "avg_draw_prob_when_actual_draw": _avg(actual_draws, "base_draw_prob") if actual_draws else None,
        "avg_draw_prob_all": _avg(details, "base_draw_prob") if details else None,
    }


def _prediction_bias(details: list[dict]) -> dict:
    total = len(details)
    actual = {label: _rate(details, "actual_result", int(label), total) for label in _label_keys()}
    top1 = {label: _rate(details, "top1_pick", int(label), total) for label in _label_keys()}
    return {
        "actual_distribution": actual,
        "top1_distribution": top1,
        "distribution_gap": {label: top1[label] - actual[label] for label in _label_keys()},
    }


def _count_labels(details: list[dict], field: str) -> dict:
    counts = Counter(str(row[field]) for row in details)
    return {label: counts.get(label, 0) for label in _label_keys()}


def _recall(details: list[dict], label: int) -> float | None:
    actual_rows = [row for row in details if row["actual_result"] == label]
    if not actual_rows:
        return None
    return sum(row["top1_pick"] == label for row in actual_rows) / len(actual_rows)


def _accuracy(rows: list[dict]) -> float:
    return sum(bool(row["hit"]) for row in rows) / len(rows) if rows else 0.0


def _avg(rows: list[dict], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows) if rows else 0.0


def _rate(rows: list[dict], field: str, label: int, total: int) -> float:
    return sum(row[field] == label for row in rows) / total if total else 0.0


def _label_keys() -> list[str]:
    return [str(label) for label in LABELS]


def _fmt(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
