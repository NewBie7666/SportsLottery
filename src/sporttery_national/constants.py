LABEL_HOME = 3
LABEL_DRAW = 1
LABEL_AWAY = 0
LABELS = [LABEL_HOME, LABEL_DRAW, LABEL_AWAY]
LABEL_NAMES = {LABEL_HOME: "主胜", LABEL_DRAW: "平", LABEL_AWAY: "客胜"}

PREDICTION_FIELDS = [
    "issue_id", "match_id", "date", "kickoff", "competition", "venue", "neutral",
    "home_team_raw", "away_team_raw", "home_team", "away_team",
    "odds_home", "odds_draw", "odds_away",
    "implied_home_win_prob", "implied_draw_prob", "implied_away_win_prob",
    "base_home_win_prob", "base_draw_prob", "base_away_win_prob",
    "adjusted_home_win_prob", "adjusted_draw_prob", "adjusted_away_win_prob",
    "top1_pick", "second_pick", "probability_gap", "top1_label", "confidence", "risk_note",
    "prob_diff_home", "prob_diff_draw", "prob_diff_away",
    "model_version", "feature_version", "created_at",
]

SETTLEMENT_FIELDS = [
    "issue_id", "match_id", "home_team", "away_team", "competition",
    "home_score", "away_score", "actual_result", "actual_label",
    "top1_pick", "top1_label", "second_pick", "confidence", "probability_gap",
    "base_home_win_prob", "base_draw_prob", "base_away_win_prob",
    "adjusted_home_win_prob", "adjusted_draw_prob", "adjusted_away_win_prob",
    "base_hit", "adjusted_hit", "base_actual_prob", "adjusted_actual_prob",
    "base_log_loss", "adjusted_log_loss", "base_brier", "adjusted_brier",
    "model_version", "feature_version", "settled_at",
]

BACKTEST_DETAIL_FIELDS = [
    "synthetic_backtest_id", "date", "competition", "home_team", "away_team", "neutral",
    "actual_result", "actual_label",
    "base_home_win_prob", "base_draw_prob", "base_away_win_prob",
    "top1_pick", "top1_label", "top1_prob", "second_pick", "second_prob", "probability_gap", "confidence",
    "hit", "actual_prob", "log_loss", "brier",
    "model_version", "feature_version",
]
