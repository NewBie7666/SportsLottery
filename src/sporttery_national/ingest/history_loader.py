from __future__ import annotations

import csv
import re
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME
from sporttery_national.mapping.team_normalizer import TeamNormalizer
from sporttery_national.utils.dates import parse_date
from sporttery_national.utils.storage import write_records
from sporttery_national.utils.validation import parse_bool

EXCLUDE_PATTERN = re.compile(r"\b(u-?2[013]|u-?19|olympic|b team| xi|select|all stars)\b", re.I)
SCORE_LINE = re.compile(r"^(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(?P<home>.+?)\s+(?P<hs>\d+)\s*[-:]\s*(?P<as>\d+)\s+(?P<away>.+)$")


def load_history(input_path: str | Path, alias_path: str | Path | None = None) -> list[dict]:
    root = Path(input_path)
    normalizer = TeamNormalizer(alias_path)
    records: list[dict] = []
    for path in sorted(root.rglob("*")) if root.is_dir() else [root]:
        if path.suffix.lower() == ".csv":
            records.extend(_load_csv(path, normalizer))
        elif path.suffix.lower() == ".txt":
            records.extend(_load_txt(path, normalizer))
    records.sort(key=lambda row: (row["date"], row["home_team"], row["away_team"]))
    return records


def import_history(input_path: str | Path, output_path: str | Path, alias_path: str | Path | None = None) -> int:
    records = load_history(input_path, alias_path)
    write_records(output_path, records)
    return len(records)


def _load_csv(path: Path, normalizer: TeamNormalizer) -> list[dict]:
    output: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if _excluded(row.get("home_team", ""), row.get("away_team", "")):
                continue
            home_score = int(row["home_score"])
            away_score = int(row["away_score"])
            if home_score < 0 or away_score < 0:
                raise ValueError(f"Negative score in {path}")
            output.append({
                "date": parse_date(row["date"]).isoformat(),
                "home_team": normalizer.normalize(row["home_team"]),
                "away_team": normalizer.normalize(row["away_team"]),
                "home_score": home_score,
                "away_score": away_score,
                "competition": row.get("competition", ""),
                "neutral": parse_bool(row.get("neutral")),
                "venue": row.get("venue", ""),
                "result": _result(home_score, away_score),
            })
    return output


def _load_txt(path: Path, normalizer: TeamNormalizer) -> list[dict]:
    output: list[dict] = []
    competition = path.stem
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            match = SCORE_LINE.match(line.strip())
            if not match or _excluded(match["home"], match["away"]):
                continue
            home_score = int(match["hs"])
            away_score = int(match["as"])
            output.append({
                "date": parse_date(match["date"]).isoformat(),
                "home_team": normalizer.normalize(match["home"]),
                "away_team": normalizer.normalize(match["away"]),
                "home_score": home_score,
                "away_score": away_score,
                "competition": competition,
                "neutral": False,
                "venue": "",
                "result": _result(home_score, away_score),
            })
    return output


def _excluded(home: str, away: str) -> bool:
    return bool(EXCLUDE_PATTERN.search(f"{home} {away}"))


def _result(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return LABEL_HOME
    if home_score == away_score:
        return LABEL_DRAW
    return LABEL_AWAY
