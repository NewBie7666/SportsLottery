from __future__ import annotations

from pathlib import Path

from sporttery_national.constants import LABEL_NAMES

FORBIDDEN = ["必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"]


def write_markdown_report(path: str | Path, rows: list[dict]) -> None:
    lines = [
        "# 体育彩票胜平负国家队概率分析",
        "",
        "本报告只提供概率分析，不提供投注建议，不承诺中奖或盈利。",
        "",
        "| 比赛 | 主队 | 客队 | 主胜 | 平 | 客胜 | 首选 | 次选 | 概率差距 | 信心 | 风险说明 |",
        "|---|---|---|---:|---:|---:|---|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('match_id', '')} | {row.get('home_team', '')} | {row.get('away_team', '')} | "
            f"{row.get('adjusted_home_win_prob', 0):.3f} | {row.get('adjusted_draw_prob', 0):.3f} | {row.get('adjusted_away_win_prob', 0):.3f} | "
            f"{row.get('top1_label', '')} | {LABEL_NAMES.get(row.get('second_pick'), '')} | {row.get('probability_gap', 0):.3f} | "
            f"{row.get('confidence', '')} | {row.get('risk_note', '')} |"
        )
    content = "\n".join(lines) + "\n"
    if any(word in content for word in FORBIDDEN):
        raise ValueError("Report contains forbidden guarantee wording")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
