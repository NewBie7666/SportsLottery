from __future__ import annotations

import unittest

from sporttery_national.cli import main


class CliTests(unittest.TestCase):
    def test_help_includes_new_commands(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_import_history_accepts_source(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            main(["import-history", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_fetch_history_accepts_source(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            main(["fetch-history", "--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
