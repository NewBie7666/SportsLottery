from __future__ import annotations


class IdentityCalibrator:
    def transform(self, probabilities: dict[str, float]) -> dict[str, float]:
        total = sum(probabilities.values())
        if total <= 0:
            return probabilities
        return {key: value / total for key, value in probabilities.items()}
