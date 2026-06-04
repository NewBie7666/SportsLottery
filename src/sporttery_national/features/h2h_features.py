from __future__ import annotations

from collections import defaultdict

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME


class H2HTracker:
    def __init__(self) -> None:
        self.results: dict[tuple[str, str], list[int]] = defaultdict(list)

    def features(self, home_team: str, away_team: str) -> dict:
        rows = self.results[(home_team, away_team)]
        if not rows:
            return {"h2h_home_win_rate": 0.0, "h2h_draw_rate": 0.0, "h2h_away_win_rate": 0.0}
        return {
            "h2h_home_win_rate": rows.count(LABEL_HOME) / len(rows),
            "h2h_draw_rate": rows.count(LABEL_DRAW) / len(rows),
            "h2h_away_win_rate": rows.count(LABEL_AWAY) / len(rows),
        }

    def update(self, home_team: str, away_team: str, result: int) -> None:
        self.results[(home_team, away_team)].append(result)
        reverse = LABEL_AWAY if result == LABEL_HOME else LABEL_HOME if result == LABEL_AWAY else LABEL_DRAW
        self.results[(away_team, home_team)].append(reverse)
