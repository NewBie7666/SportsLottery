export type PredictionRow = {
  issue_id?: string;
  match_id?: string;
  home_team?: string;
  away_team?: string;
  base_home_win_prob?: number | null;
  base_draw_prob?: number | null;
  base_away_win_prob?: number | null;
  adjusted_home_win_prob?: number | null;
  adjusted_draw_prob?: number | null;
  adjusted_away_win_prob?: number | null;
  top1_label?: string;
  second_pick?: number | null;
  probability_gap?: number | null;
  confidence?: string;
  risk_note?: string;
  adjusted_top1_label?: string;
  adjusted_probability_gap?: number | null;
};

export type MetricBlock = {
  matches?: number;
  accuracy?: number | null;
  avg_log_loss?: number | null;
  avg_brier?: number | null;
  draw_recall?: number | null;
};

export type BacktestSummary = {
  total_matches?: number;
  top1_accuracy?: number | null;
  avg_log_loss?: number | null;
  avg_brier?: number | null;
  draw_recall?: number | null;
  home_win_recall?: number | null;
  away_win_recall?: number | null;
  draw_bias_diagnostics?: Record<string, number | null>;
  prediction_bias?: {
    actual_distribution?: Record<string, number>;
    top1_distribution?: Record<string, number>;
    distribution_gap?: Record<string, number>;
  };
  calibration_bins?: Array<{
    bin: string;
    matches?: number;
    avg_top1_prob?: number | null;
    accuracy?: number | null;
    avg_log_loss?: number | null;
  }>;
  by_confidence?: Record<string, MetricBlock>;
  recent_windows?: Record<string, MetricBlock>;
};

export type BacktestDetail = {
  synthetic_backtest_id?: string;
};

export type SettlementSummary = {
  total_matches?: number;
  base_top1_accuracy?: number | null;
  adjusted_top1_accuracy?: number | null;
  base_avg_log_loss?: number | null;
  adjusted_avg_log_loss?: number | null;
  base_avg_brier?: number | null;
  adjusted_avg_brier?: number | null;
  error_count?: number;
  by_confidence?: Record<string, MetricBlock>;
  by_competition?: Record<string, MetricBlock>;
};

export type SettlementRow = {
  issue_id?: string;
  match_id?: string;
};

export type AdjustmentSummary = {
  experiment_name?: string;
  adjustment_params?: Record<string, unknown>;
  total_matches?: number;
  changed_pick_count?: number;
  changed_top1_count?: number;
  market_skipped_count?: number;
  market_weight_skipped_count?: number;
  avg_abs_prob_shift?: number | null;
  avg_abs_home_shift?: number | null;
  avg_abs_draw_shift?: number | null;
  avg_abs_away_shift?: number | null;
  base_top1_distribution?: Record<string, number>;
  adjusted_top1_distribution?: Record<string, number>;
  changed_picks?: Array<{
    issue_id?: string;
    match_id?: string;
    home_team?: string;
    away_team?: string;
    top1_label?: string;
    adjusted_top1_label?: string;
    base_home_win_prob?: number | null;
    base_draw_prob?: number | null;
    base_away_win_prob?: number | null;
    adjusted_home_win_prob?: number | null;
    adjusted_draw_prob?: number | null;
    adjusted_away_win_prob?: number | null;
  }>;
};
