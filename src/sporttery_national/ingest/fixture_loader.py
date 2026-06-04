from __future__ import annotations

import csv
from pathlib import Path

from sporttery_national.mapping.team_normalizer import TeamNormalizer
from sporttery_national.utils.validation import parse_bool, parse_float, require_columns

REQUIRED_FIXTURE_COLUMNS = {"match_id", "date", "kickoff", "home_team", "away_team", "odds_home", "odds_draw", "odds_away"}


def load_fixtures(path: str | Path, alias_path: str | Path | None = None) -> list[dict]:
    normalizer = TeamNormalizer(alias_path)
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        require_columns(set(reader.fieldnames or []), REQUIRED_FIXTURE_COLUMNS, str(path))
        rows = []
        for row in reader:
            home_raw = row["home_team"]
            away_raw = row["away_team"]
            odds_home = parse_float(row.get("odds_home"))
            odds_draw = parse_float(row.get("odds_draw"))
            odds_away = parse_float(row.get("odds_away"))
            implied = implied_probabilities(odds_home, odds_draw, odds_away)
            rows.append({
                "issue_id": row.get("issue_id", ""),
                "match_id": row["match_id"],
                "date": row["date"],
                "kickoff": row["kickoff"],
                "competition": row.get("competition", ""),
                "venue": row.get("venue", ""),
                "neutral": parse_bool(row.get("neutral")),
                "home_team_raw": home_raw,
                "away_team_raw": away_raw,
                "home_team": normalizer.normalize(home_raw),
                "away_team": normalizer.normalize(away_raw),
                "odds_home": odds_home,
                "odds_draw": odds_draw,
                "odds_away": odds_away,
                **implied,
            })
    return rows


def implied_probabilities(odds_home: float | None, odds_draw: float | None, odds_away: float | None) -> dict:
    if not odds_home or not odds_draw or not odds_away:
        return {"implied_home_win_prob": None, "implied_draw_prob": None, "implied_away_win_prob": None}
    raw_home = 1 / odds_home
    raw_draw = 1 / odds_draw
    raw_away = 1 / odds_away
    total = raw_home + raw_draw + raw_away
    return {
        "implied_home_win_prob": raw_home / total,
        "implied_draw_prob": raw_draw / total,
        "implied_away_win_prob": raw_away / total,
    }
