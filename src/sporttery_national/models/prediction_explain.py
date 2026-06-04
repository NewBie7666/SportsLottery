from __future__ import annotations

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME

OUTCOME_KEYS = {
    LABEL_HOME: "home",
    LABEL_DRAW: "draw",
    LABEL_AWAY: "away",
}
IMPLIED_KEYS = {
    LABEL_HOME: "implied_home_win_prob",
    LABEL_DRAW: "implied_draw_prob",
    LABEL_AWAY: "implied_away_win_prob",
}
FORBIDDEN_RISK_WORDS = ["必中", "稳赚", "保证中奖", "推荐下注", "稳胆", "必买"]
DISCLAIMER = "仅供概率研究，不承诺中奖或盈利。"


def rank_outcomes(probs: dict[str, float]) -> dict:
    ranked = sorted(
        ((label, probs[key]) for label, key in OUTCOME_KEYS.items()),
        key=lambda item: (-item[1], item[0]),
    )
    top_label, top_prob = ranked[0]
    second_label, second_prob = ranked[1]
    return {
        "top1_pick": top_label,
        "top1_prob": top_prob,
        "second_pick": second_label,
        "second_prob": second_prob,
        "probability_gap": top_prob - second_prob,
    }


def confidence_from_prediction(max_prob: float, second_prob: float, competition: str = "", neutral: bool = False) -> str:
    gap = max_prob - second_prob
    if max_prob >= 0.55 and gap >= 0.18:
        confidence = "high"
    elif max_prob >= 0.45 and gap >= 0.10:
        confidence = "medium"
    else:
        confidence = "low"
    if confidence == "high" and (_is_friendly(competition) or neutral):
        return "medium"
    return confidence


def build_risk_note(
    *,
    top1_pick: int,
    top1_prob: float,
    second_prob: float,
    competition: str = "",
    neutral: bool = False,
    fixture: dict | None = None,
    base_probs: dict[str, float] | None = None,
) -> str:
    fixture = fixture or {}
    base_probs = base_probs or {}
    gap = top1_prob - second_prob
    notes: list[str] = []

    if gap < 0.08:
        notes.append("胜平负概率接近，结果不确定性较高")
    elif gap > 0.18:
        notes.append("首选结果相对明确")

    comp = competition or ""
    comp_lower = comp.lower()
    if _is_friendly(comp):
        notes.append("友谊赛轮换和战意不确定性较高")
    elif "qualifier" in comp_lower or "qualification" in comp_lower or "预选" in comp:
        notes.append("正式比赛，历史强弱和近期状态参考价值相对更高")
    elif "cup" in comp_lower or "continental" in comp_lower or "杯" in comp:
        notes.append("杯赛场景可能受淘汰赛/中立场影响")

    if neutral:
        notes.append("中立场比赛可能削弱常规主场优势")

    implied_key = IMPLIED_KEYS[top1_pick]
    implied_prob = fixture.get(implied_key)
    if implied_prob is None:
        notes.append("未提供官方奖金，无法进行市场概率对比")
    else:
        model_prob = base_probs.get(OUTCOME_KEYS[top1_pick], top1_prob)
        diff = model_prob - implied_prob
        if diff > 0.08:
            notes.append("模型概率明显高于官方隐含概率")
        elif diff < -0.08:
            notes.append("模型概率明显低于官方隐含概率")
        else:
            notes.append("模型概率与官方隐含概率接近")

    notes.append(DISCLAIMER)
    content = "；".join(dict.fromkeys(notes))
    if any(word in content for word in FORBIDDEN_RISK_WORDS):
        raise ValueError("Risk note contains forbidden wording")
    return content


def _is_friendly(competition: str) -> bool:
    comp = competition or ""
    return "friendly" in comp.lower() or "友谊赛" in comp
