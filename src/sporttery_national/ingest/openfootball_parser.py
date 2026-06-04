from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME
from sporttery_national.utils.dates import parse_date

COMMENT_PREFIXES = ("#", "//", ";")
MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
DATE_LINE = re.compile(r"^\[(?P<text>[^\]]+)\]\s*(?P<rest>.*)$")
ISO_DATE_PREFIX = re.compile(r"^(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(?P<rest>.+)$")
SCORE_FIRST = re.compile(r"^(?P<home>.+?)\s+(?P<hs>\d+)\s*[-:]\s*(?P<as>\d+)\s+(?P<away>.+)$")
VERSUS_SCORE_LAST = re.compile(r"^(?P<home>.+?)\s+v(?:s\.?)?\s+(?P<away>.+?)\s+(?P<hs>\d+)\s*[-:]\s*(?P<as>\d+)(?:\s+.*)?$", re.I)
DASH_SCORE_LAST = re.compile(r"^(?P<home>.+?)\s+-\s+(?P<away>.+?)\s+(?P<hs>\d+)\s*[-:]\s*(?P<as>\d+)(?:\s+.*)?$")


@dataclass
class ParseOutput:
    records: list[dict]
    errors: list[dict]
    files: int


def parse_openfootball(root: str | Path) -> ParseOutput:
    source = Path(root)
    records: list[dict] = []
    errors: list[dict] = []
    files = sorted(source.rglob("*.txt")) if source.is_dir() else [source]
    for path in files:
        parsed, failed = parse_file(path, source)
        records.extend(parsed)
        errors.extend(failed)
    records.sort(key=lambda row: (row["date"], row["home_team"], row["away_team"]))
    return ParseOutput(records=records, errors=errors, files=len(files))


def parse_file(path: Path, root: Path | None = None) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    errors: list[dict] = []
    competition = _competition(path, root)
    inferred_year = _infer_year(path)
    current_date: date | None = None
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, start=1):
            text = raw.strip().lstrip("\ufeff")
            if _skip_line(text):
                continue
            text, current_date = _extract_date(text, current_date, inferred_year)
            if not text:
                continue
            match = _parse_match(text)
            if not match:
                if _looks_like_match(text):
                    errors.append(_error(path, line_no, raw, "unrecognized match format"))
                continue
            if current_date is None:
                errors.append(_error(path, line_no, raw, "missing date context"))
                continue
            home_score = int(match["hs"])
            away_score = int(match["as"])
            if home_score < 0 or away_score < 0:
                errors.append(_error(path, line_no, raw, "negative score"))
                continue
            home_team = _clean_team(match["home"])
            away_team = _clean_team(match["away"])
            if not home_team or not away_team:
                errors.append(_error(path, line_no, raw, "empty team name"))
                continue
            records.append({
                "date": current_date.isoformat(),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "competition": competition,
                "neutral": False,
                "venue": "",
                "source_file": str(path),
                "source_line": line_no,
                "result": _result(home_score, away_score),
            })
    return records, errors


def _parse_match(text: str) -> re.Match[str] | None:
    for pattern in (VERSUS_SCORE_LAST, DASH_SCORE_LAST, SCORE_FIRST):
        match = pattern.match(text)
        if match:
            return match
    return None


def _extract_date(text: str, current: date | None, inferred_year: int | None) -> tuple[str, date | None]:
    match = ISO_DATE_PREFIX.match(text)
    if match:
        return match["rest"].strip(), parse_date(match["date"])
    date_line = DATE_LINE.match(text)
    if not date_line:
        parsed = _parse_openfootball_date(text, inferred_year)
        if parsed and not _looks_like_match(text):
            return "", parsed
        return text, current
    parsed = _parse_openfootball_date(date_line["text"], inferred_year)
    return date_line["rest"].strip(), parsed or current


def _parse_openfootball_date(text: str, inferred_year: int | None) -> date | None:
    stripped = text.strip()
    try:
        return parse_date(stripped)
    except ValueError:
        pass
    cleaned = text.replace("/", " ").replace(".", " ").replace(",", " ")
    parts = [p for p in cleaned.split() if p]
    parts = [p for p in parts if p[:3].lower() not in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}]
    year = next((int(p) for p in parts if p.isdigit() and len(p) == 4), inferred_year)
    if year is None:
        return None
    month = None
    day = None
    for part in parts:
        low = part.lower()
        if low in MONTHS:
            month = MONTHS[low]
        elif part.isdigit() and len(part) != 4:
            day = int(part)
    if month and day:
        return date(year, month, day)
    return None


def _competition(path: Path, root: Path | None) -> str:
    if root is None:
        return path.stem.replace("-", " ").title()
    rel = path.relative_to(root) if root and path.is_relative_to(root) else path
    parts = list(rel.parts)
    if len(parts) > 1:
        return " / ".join(Path(part).stem.replace("-", " ").title() for part in parts[:-1])
    return path.stem.replace("-", " ").title()


def _infer_year(path: Path) -> int | None:
    for part in reversed(path.parts):
        match = re.search(r"(18|19|20)\d{2}", part)
        if match:
            return int(match.group(0))
    return None


def _skip_line(text: str) -> bool:
    return not text or text.startswith(COMMENT_PREFIXES) or text.startswith("=") or text.lower().startswith(("group ", "round ", "matchday "))


def _looks_like_match(text: str) -> bool:
    return bool(re.search(r"\d+\s*[-:]\s*\d+", text) or re.search(r"\bv(?:s\.?)?\b", text, re.I))


def _clean_team(text: str) -> str:
    text = text.split("@", 1)[0]
    text = re.sub(r"\s+\[[^\]]+\]$", "", text)
    text = re.sub(r"\s+\([^)]+\)$", "", text)
    return " ".join(text.strip(" -*").split())


def _result(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return LABEL_HOME
    if home_score == away_score:
        return LABEL_DRAW
    return LABEL_AWAY


def _error(path: Path, line_no: int, raw: str, reason: str) -> dict:
    return {"source_file": str(path), "source_line": line_no, "raw_text": raw.strip(), "reason": reason}
