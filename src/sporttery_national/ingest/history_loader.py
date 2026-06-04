from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from sporttery_national.constants import LABEL_AWAY, LABEL_DRAW, LABEL_HOME
from sporttery_national.ingest.openfootball_parser import ParseOutput, parse_openfootball
from sporttery_national.mapping.team_normalizer import TeamNormalizer
from sporttery_national.utils.dates import parse_date
from sporttery_national.utils.storage import write_records
from sporttery_national.utils.validation import parse_bool

EXCLUDE_PATTERN = re.compile(
    r"\b(u-?2[013]|u-?19|olympics?|b[ -]?team|\bxi\b|select|all stars|women'?s?|ladies|club)\b",
    re.I,
)
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


def import_history(
    input_path: str | Path,
    output_path: str | Path,
    alias_path: str | Path | None = None,
    source: str = "csv",
    report_dir: str | Path = "reports",
) -> dict:
    normalizer = TeamNormalizer(alias_path)
    if source == "csv":
        parsed = ParseOutput(records=load_history(input_path, alias_path), errors=[], files=_file_count(input_path, {".csv", ".txt"}))
    elif source == "openfootball":
        parsed = parse_openfootball(input_path)
    else:
        raise ValueError(f"Unsupported history source: {source}")

    records, filtered_count, unknown_teams = _clean_records(parsed.records, normalizer)
    write_records(output_path, records)
    summary = _summary(source, parsed.files, parsed.records, records, filtered_count, parsed.errors, unknown_teams)
    _write_reports(Path(report_dir), summary, parsed.errors, unknown_teams)
    return summary


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
    return _excluded_text(f"{home} {away}")


def _result(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return LABEL_HOME
    if home_score == away_score:
        return LABEL_DRAW
    return LABEL_AWAY


def _clean_records(records: list[dict], normalizer: TeamNormalizer) -> tuple[list[dict], int, Counter[str]]:
    output: list[dict] = []
    filtered = 0
    unknown: Counter[str] = Counter()
    for record in records:
        if _excluded(record.get("home_team", ""), record.get("away_team", "")) or _excluded_text(record.get("competition", "")):
            filtered += 1
            continue
        try:
            match_date = parse_date(record["date"]).isoformat()
            home_score = int(record["home_score"])
            away_score = int(record["away_score"])
        except (KeyError, TypeError, ValueError):
            filtered += 1
            continue
        if home_score < 0 or away_score < 0 or not str(record.get("home_team", "")).strip() or not str(record.get("away_team", "")).strip():
            filtered += 1
            continue
        for side in ("home_team", "away_team"):
            if normalizer.is_unknown(record[side]):
                unknown[record[side]] += 1
        cleaned = dict(record)
        cleaned.update({
            "date": match_date,
            "home_team": normalizer.normalize(record["home_team"]),
            "away_team": normalizer.normalize(record["away_team"]),
            "home_score": home_score,
            "away_score": away_score,
            "neutral": parse_bool(record.get("neutral")),
            "venue": record.get("venue", ""),
            "competition": record.get("competition", ""),
            "result": _result(home_score, away_score),
        })
        output.append(cleaned)
    output.sort(key=lambda row: (row["date"], row["home_team"], row["away_team"]))
    return output, filtered, unknown


def _summary(
    source: str,
    file_count: int,
    parsed_records: list[dict],
    final_records: list[dict],
    filtered_count: int,
    errors: list[dict],
    unknown_teams: Counter[str],
) -> dict:
    team_counts: Counter[str] = Counter()
    competition_counts: Counter[str] = Counter()
    for record in final_records:
        team_counts[record["home_team"]] += 1
        team_counts[record["away_team"]] += 1
        competition_counts[record.get("competition", "") or "Unknown"] += 1
    dates = [record["date"] for record in final_records]
    return {
        "source": source,
        "raw_file_count": file_count,
        "successful_parsed_matches": len(parsed_records),
        "filtered_matches": filtered_count,
        "final_matches": len(final_records),
        "parse_error_rows": len(errors),
        "unknown_team_count": len(unknown_teams),
        "date_start": min(dates) if dates else None,
        "date_end": max(dates) if dates else None,
        "top_teams": team_counts.most_common(20),
        "competition_distribution": competition_counts.most_common(),
    }


def _write_reports(report_dir: Path, summary: dict, errors: list[dict], unknown_teams: Counter[str]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    error_dir = report_dir / "import_errors"
    error_dir.mkdir(parents=True, exist_ok=True)
    _write_summary(report_dir / "import_history_summary.md", summary)
    _write_error_csv(error_dir / "openfootball_parse_errors.csv", errors)
    _write_unknown_csv(error_dir / "unknown_teams.csv", unknown_teams)


def _write_summary(path: Path, summary: dict) -> None:
    lines = [
        "# Import History Summary",
        "",
        f"- Data source: {summary['source']}",
        f"- Raw file count: {summary['raw_file_count']}",
        f"- Successful parsed matches: {summary['successful_parsed_matches']}",
        f"- Filtered matches: {summary['filtered_matches']}",
        f"- Final retained matches: {summary['final_matches']}",
        f"- Parse failed rows: {summary['parse_error_rows']}",
        f"- Unknown team count: {summary['unknown_team_count']}",
        f"- Date range: {summary['date_start']} to {summary['date_end']}",
        "",
        "## Top 20 Teams",
        "",
    ]
    lines.extend(f"- {team}: {count}" for team, count in summary["top_teams"])
    lines.extend(["", "## Competition Distribution", ""])
    lines.extend(f"- {competition}: {count}" for competition, count in summary["competition_distribution"][:50])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_error_csv(path: Path, errors: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["source_file", "source_line", "raw_text", "reason"])
        writer.writeheader()
        writer.writerows(errors)


def _write_unknown_csv(path: Path, unknown_teams: Counter[str]) -> None:
    normalizer = TeamNormalizer()
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["raw_team", "count", "suggestions"])
        writer.writeheader()
        for team, count in unknown_teams.most_common():
            writer.writerow({"raw_team": team, "count": count, "suggestions": "|".join(normalizer.suggestions(team))})


def _file_count(input_path: str | Path, suffixes: set[str]) -> int:
    root = Path(input_path)
    if root.is_file():
        return 1
    return sum(1 for path in root.rglob("*") if path.suffix.lower() in suffixes)


def _excluded_text(text: str) -> bool:
    normalized = re.sub(r"[_-]+", " ", text)
    return bool(EXCLUDE_PATTERN.search(normalized))
