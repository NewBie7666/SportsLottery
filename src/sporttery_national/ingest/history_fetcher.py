from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

OPENFOOTBALL_URL = "https://github.com/openfootball/internationals.git"


def fetch_history(source: str, output: str | Path) -> str:
    if source != "openfootball":
        raise ValueError(f"Unsupported history source: {source}")
    if shutil.which("git") is None:
        raise RuntimeError("git is required to fetch openfootball history data, but it was not found on PATH")

    target = Path(output)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", OPENFOOTBALL_URL, str(target)])
        return f"Cloned {OPENFOOTBALL_URL} to {target}"

    if not (target / ".git").exists():
        raise RuntimeError(f"Output path exists but is not a git repository: {target}")

    _run(["git", "-C", str(target), "pull", "--ff-only"])
    return f"Updated {target}"


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed: {' '.join(command)}") from exc
