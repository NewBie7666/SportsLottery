from __future__ import annotations

import csv
import difflib
from pathlib import Path

from .aliases import DEFAULT_ALIASES


class TeamNormalizer:
    def __init__(self, alias_path: str | Path | None = None) -> None:
        self.aliases = dict(DEFAULT_ALIASES)
        if alias_path and Path(alias_path).exists():
            self._load_csv(Path(alias_path))

    def _load_csv(self, path: Path) -> None:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                alias = (row.get("alias") or row.get("name") or "").strip()
                canonical = (row.get("canonical") or row.get("standard") or "").strip()
                if alias and canonical:
                    self.aliases[self._key(alias)] = canonical
                    self.aliases[self._key(canonical)] = canonical

    def normalize(self, name: str) -> str:
        key = self._key(name)
        if key in self.aliases:
            return self.aliases[key]
        stripped = name.strip()
        if not stripped:
            raise ValueError("Team name is empty")
        return stripped

    def suggestions(self, name: str, limit: int = 5) -> list[str]:
        key = self._key(name)
        candidates = sorted(set(self.aliases.keys()) | set(self.aliases.values()))
        matches = difflib.get_close_matches(key, candidates, n=limit, cutoff=0.45)
        return [self.aliases.get(match, match) for match in matches]

    def query(self, name: str) -> dict:
        normalized = self.normalize(name)
        known = self._key(name) in self.aliases
        return {"query": name, "team": normalized, "known": known, "suggestions": self.suggestions(name)}

    def is_unknown(self, name: str) -> bool:
        return self._key(name) not in self.aliases

    @staticmethod
    def _key(value: str) -> str:
        return " ".join(value.strip().lower().replace("　", " ").split())
