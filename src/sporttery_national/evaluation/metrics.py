from __future__ import annotations

import math

from sporttery_national.constants import LABELS


def log_loss(rows: list[dict]) -> float:
    total = 0.0
    for row in rows:
        total += -math.log(max(row["probs"][row["actual"]], 1e-15))
    return total / len(rows) if rows else 0.0


def brier_score(rows: list[dict]) -> float:
    total = 0.0
    for row in rows:
        for label in LABELS:
            expected = 1.0 if label == row["actual"] else 0.0
            total += (row["probs"][label] - expected) ** 2
    return total / len(rows) if rows else 0.0


def top1_accuracy(rows: list[dict]) -> float:
    return sum(row["predicted"] == row["actual"] for row in rows) / len(rows) if rows else 0.0
