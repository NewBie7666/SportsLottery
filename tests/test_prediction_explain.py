from __future__ import annotations

import unittest

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME
from sporttery_national.models.prediction_explain import (
    FORBIDDEN_RISK_WORDS,
    build_risk_note,
    confidence_from_prediction,
    rank_outcomes,
)


class PredictionExplainTests(unittest.TestCase):
    def test_confidence_levels(self) -> None:
        self.assertEqual(confidence_from_prediction(0.60, 0.40, "Qualifier", False), "high")
        self.assertEqual(confidence_from_prediction(0.50, 0.39, "Qualifier", False), "medium")
        self.assertEqual(confidence_from_prediction(0.44, 0.36, "Qualifier", False), "low")

    def test_friendly_and_neutral_cap_high_to_medium(self) -> None:
        self.assertEqual(confidence_from_prediction(0.70, 0.20, "Friendly", False), "medium")
        self.assertEqual(confidence_from_prediction(0.70, 0.20, "友谊赛", False), "medium")
        self.assertEqual(confidence_from_prediction(0.70, 0.20, "Qualifier", True), "medium")

    def test_rank_outcomes_returns_second_pick_and_gap(self) -> None:
        ranked = rank_outcomes({"home": 0.51, "draw": 0.24, "away": 0.25})
        self.assertEqual(ranked["top1_pick"], LABEL_HOME)
        self.assertEqual(ranked["second_pick"], LABEL_AWAY)
        self.assertAlmostEqual(ranked["probability_gap"], 0.26)

    def test_risk_note_mentions_missing_odds(self) -> None:
        note = build_risk_note(
            top1_pick=LABEL_HOME,
            top1_prob=0.50,
            second_prob=0.43,
            competition="Friendly",
            neutral=False,
            fixture={},
            base_probs={"home": 0.50, "draw": 0.43, "away": 0.07},
        )
        self.assertIn("未提供官方奖金", note)
        self.assertIn("友谊赛轮换和战意不确定性较高", note)
        self.assertIn("仅供概率研究，不承诺中奖或盈利。", note)

    def test_risk_note_compares_market_probability(self) -> None:
        high = build_risk_note(
            top1_pick=LABEL_HOME,
            top1_prob=0.60,
            second_prob=0.30,
            competition="Qualifier",
            fixture={"implied_home_win_prob": 0.48},
            base_probs={"home": 0.60},
        )
        low = build_risk_note(
            top1_pick=LABEL_DRAW,
            top1_prob=0.30,
            second_prob=0.24,
            competition="World Cup",
            fixture={"implied_draw_prob": 0.42},
            base_probs={"draw": 0.30},
        )
        close = build_risk_note(
            top1_pick=LABEL_AWAY,
            top1_prob=0.38,
            second_prob=0.34,
            competition="Continental Cup",
            fixture={"implied_away_win_prob": 0.40},
            base_probs={"away": 0.38},
        )
        self.assertIn("模型概率明显高于官方隐含概率", high)
        self.assertIn("模型概率明显低于官方隐含概率", low)
        self.assertIn("模型概率与官方隐含概率接近", close)

    def test_risk_note_forbidden_words_absent(self) -> None:
        note = build_risk_note(
            top1_pick=LABEL_HOME,
            top1_prob=0.60,
            second_prob=0.30,
            competition="Qualifier",
            fixture={"implied_home_win_prob": 0.55},
            base_probs={"home": 0.60},
        )
        for word in FORBIDDEN_RISK_WORDS:
            self.assertNotIn(word, note)


if __name__ == "__main__":
    unittest.main()
