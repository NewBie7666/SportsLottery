from __future__ import annotations

from datetime import date

from sporttery_national.features.elo import EloRatings
from sporttery_national.features.form_features import FormTracker
from sporttery_national.features.h2h_features import H2HTracker
from sporttery_national.utils.dates import parse_date


def competition_weight(competition: str) -> float:
    text = (competition or "").lower()
    if any(key in text for key in ["world cup", "euro", "asian cup", "copa", "africa cup", "continental"]):
        return 1.3
    if "qualif" in text or "预选" in text:
        return 1.15
    if "friendly" in text or "友谊" in text:
        return 0.75
    return 1.0


class FeatureBuilder:
    def __init__(self, elo: EloRatings | None = None) -> None:
        self.elo = elo or EloRatings()
        self.form = FormTracker()
        self.h2h = H2HTracker()
        self.last_played: dict[str, date] = {}

    def build_before_match(self, match: dict) -> dict:
        home = match["home_team"]
        away = match["away_team"]
        match_date = parse_date(match["date"])
        elo_home = self.elo.get(home)
        elo_away = self.elo.get(away)
        features = {
            "elo_home": elo_home,
            "elo_away": elo_away,
            "elo_diff": elo_home - elo_away,
            "home_advantage": 0 if match.get("neutral") else 1,
            "neutral": bool(match.get("neutral")),
            "competition_weight": competition_weight(match.get("competition", "")),
            "days_rest_home": self._days_rest(home, match_date),
            "days_rest_away": self._days_rest(away, match_date),
        }
        features.update(self.form.features(home, "home"))
        features.update(self.form.features(away, "away"))
        features.update(self.h2h.features(home, away))
        return features

    def update_after_match(self, match: dict) -> None:
        home = match["home_team"]
        away = match["away_team"]
        self.elo.update(home, away, int(match["result"]), bool(match.get("neutral")))
        self.form.update(home, away, int(match["home_score"]), int(match["away_score"]))
        self.h2h.update(home, away, int(match["result"]))
        match_date = parse_date(match["date"])
        self.last_played[home] = match_date
        self.last_played[away] = match_date

    def warmup(self, matches: list[dict]) -> None:
        for match in sorted(matches, key=lambda row: row["date"]):
            self.update_after_match(match)

    def _days_rest(self, team: str, match_date: date) -> int:
        previous = self.last_played.get(team)
        if previous is None:
            return 999
        return max((match_date - previous).days, 0)
