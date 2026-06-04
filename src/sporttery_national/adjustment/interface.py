from __future__ import annotations


def apply_adjustment(base_probs: dict, params: dict | None = None) -> dict:
    """
    Placeholder for future user adjustment.

    V1 returns base probabilities unchanged. Future adjustment must be a
    prediction post-processing layer only; it must not modify training data or
    model weights.
    """
    return dict(base_probs)
