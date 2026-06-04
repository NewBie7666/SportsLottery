from __future__ import annotations

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME


class EloRatings:
    def __init__(self, default: float = 1500.0, k: float = 24.0) -> None:
        self.default = default
        self.k = k
        self.ratings: dict[str, float] = {}

    def get(self, team: str) -> float:
        return self.ratings.get(team, self.default)

    def update(self, home_team: str, away_team: str, result: int, neutral: bool = False) -> None:
        home = self.get(home_team)
        away = self.get(away_team)
        home_boost = 0 if neutral else 55
        expected_home = 1 / (1 + 10 ** (((away - (home + home_boost)) / 400)))
        actual_home = 1.0 if result == LABEL_HOME else 0.5 if result == LABEL_DRAW else 0.0
        delta = self.k * (actual_home - expected_home)
        self.ratings[home_team] = home + delta
        self.ratings[away_team] = away - delta

    def to_json(self) -> dict:
        return {"default": self.default, "k": self.k, "ratings": self.ratings}

    @classmethod
    def from_json(cls, payload: dict) -> "EloRatings":
        obj = cls(default=payload.get("default", 1500.0), k=payload.get("k", 24.0))
        obj.ratings = {team: float(rating) for team, rating in payload.get("ratings", {}).items()}
        return obj
