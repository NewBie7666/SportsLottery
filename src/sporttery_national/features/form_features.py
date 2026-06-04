from __future__ import annotations

from collections import defaultdict, deque


class FormTracker:
    def __init__(self, window: int = 10) -> None:
        self.window = window
        self.matches: dict[str, deque[dict]] = defaultdict(lambda: deque(maxlen=window))

    def features(self, team: str, prefix: str) -> dict:
        rows = list(self.matches[team])
        if not rows:
            return {
                f"{prefix}_recent_win_rate": 0.0,
                f"{prefix}_recent_draw_rate": 0.0,
                f"{prefix}_recent_goals_for": 0.0,
                f"{prefix}_recent_goals_against": 0.0,
            }
        return {
            f"{prefix}_recent_win_rate": sum(r["win"] for r in rows) / len(rows),
            f"{prefix}_recent_draw_rate": sum(r["draw"] for r in rows) / len(rows),
            f"{prefix}_recent_goals_for": sum(r["gf"] for r in rows) / len(rows),
            f"{prefix}_recent_goals_against": sum(r["ga"] for r in rows) / len(rows),
        }

    def update(self, home_team: str, away_team: str, home_score: int, away_score: int) -> None:
        self.matches[home_team].append({"win": home_score > away_score, "draw": home_score == away_score, "gf": home_score, "ga": away_score})
        self.matches[away_team].append({"win": away_score > home_score, "draw": home_score == away_score, "gf": away_score, "ga": home_score})
