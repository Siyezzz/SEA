import sqlite3
import tempfile
import unittest
from pathlib import Path
from kernel import Kernel


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.k = Kernel()
        self.mid = self.k.add("alpha", "CSV encoding", "Check encoding before reading CSV", "fixture:encoding", "discovery")

    def tearDown(self):
        self.k.close()

    def activate(self):
        for i in range(3):
            self.k.feedback(self.mid, f"heldout-{i}", 1, f"test:{i}:pass")

    def test_promotion_and_regression(self):
        self.assertEqual(self.k.recall("CSV", "alpha"), "")
        self.activate()
        self.assertIn(self.mid, self.k.recall("CSV", "alpha"))
        self.k.feedback(self.mid, "counterexample", 0, "test:failed")
        self.assertEqual(self.k.recall("CSV", "alpha"), "")

    def test_no_self_confirmation_or_duplicate_rewards(self):
        with self.assertRaises(ValueError):
            self.k.feedback(self.mid, "discovery", 1, "self")
        self.k.feedback(self.mid, "holdout", 1, "test:pass")
        with self.assertRaises(sqlite3.IntegrityError):
            self.k.feedback(self.mid, "holdout", 1, "test:pass")

    def test_scope_archive_and_recovery(self):
        self.activate()
        self.assertEqual(self.k.recall("CSV", "beta"), "")
        self.k.archive("alpha")
        self.assertEqual(self.k.recall("CSV", "alpha"), "")
        self.assertIn(self.mid, self.k.recall("CSV", "alpha", include_archived=True))
        self.assertEqual(self.k.get(self.mid)["evidence"], "fixture:encoding")

    def test_exact_multilingual_budget_and_no_irrelevant_injection(self):
        self.activate()
        multilingual = self.k.add("alpha", "CSV unicode", "Check \u7f16\u7801 and encoding", "fixture:unicode", "unicode-discovery")
        for i in range(3):
            self.k.feedback(multilingual, f"unicode-{i}", 1, "test:unicode:pass")
        self.assertIn(multilingual, self.k.recall("\u7f16\u7801", "alpha"))
        for budget in (0, 10, 128, 512, 2048):
            text = self.k.recall("CSV encoding", "alpha", budget)
            self.assertLessEqual(len(text.encode("utf-8")), budget)
        self.assertEqual(self.k.recall("astronomy", "alpha"), "")

    def test_invalid_reward(self):
        for reward in (-1, 2, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.k.feedback(self.mid, "bad", reward, "test")

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "memory.db")
            k = Kernel(path)
            mid = k.add("p", "trigger", "lesson", "evidence", "origin")
            k.close()
            k = Kernel(path)
            self.assertEqual(k.get(mid)["lesson"], "lesson")
            k.close()


if __name__ == "__main__":
    unittest.main()
