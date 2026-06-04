from __future__ import annotations

import unittest

from sporttery_national.mapping.team_normalizer import TeamNormalizer


class TeamNormalizerTests(unittest.TestCase):
    def test_chinese_and_english_aliases(self) -> None:
        normalizer = TeamNormalizer()
        self.assertEqual(normalizer.normalize("德国"), "Germany")
        self.assertEqual(normalizer.normalize("USA"), "United States")
        self.assertEqual(normalizer.normalize("韩国"), "Korea Republic")

    def test_unknown_team_returns_suggestions(self) -> None:
        result = TeamNormalizer().query("Geramny")
        self.assertFalse(result["known"])
        self.assertIn("Germany", result["suggestions"])


if __name__ == "__main__":
    unittest.main()
