from __future__ import annotations

import unittest

from sporttery_national.features.feature_builder import FeatureBuilder


class FeatureBuilderTests(unittest.TestCase):
    def test_features_use_only_prior_matches(self) -> None:
        builder = FeatureBuilder()
        first = {
            "date": "2024-01-01",
            "home_team": "Germany",
            "away_team": "France",
            "home_score": 2,
            "away_score": 1,
            "competition": "Friendly",
            "neutral": False,
            "result": 3,
        }
        before = builder.build_before_match(first)
        self.assertEqual(before["home_recent_win_rate"], 0.0)
        builder.update_after_match(first)
        second = dict(first, date="2024-01-10", home_score=0, away_score=0, result=1)
        after = builder.build_before_match(second)
        self.assertGreater(after["home_recent_win_rate"], 0.0)
        self.assertEqual(after["days_rest_home"], 9)


if __name__ == "__main__":
    unittest.main()
