import unittest

from core.match import find_duplicate_pairs, select_master
from core.normalize import normalize_name
from data.synth import generate
from eval.metrics import duplicate_metrics


class BasicTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_name("The Apex-Billing App"), "apex billing")
        self.assertEqual(normalize_name("APEX  BILLING Prod"), "apex billing")

    def test_generator_is_deterministic(self):
        self.assertEqual(generate(seed=1), generate(seed=1))
        self.assertNotEqual(generate(seed=1), generate(seed=2))

    def test_master_is_older_record(self):
        a = {"id": "a", "created": "2024-01-01"}
        b = {"id": "b", "created": "2025-01-01"}
        self.assertEqual(select_master(b, a)[0]["id"], "a")

    def test_metrics_perfect_and_empty(self):
        truth = [{"master": "a", "duplicate": "b"}]
        self.assertEqual(duplicate_metrics(truth, truth)["f1"], 1.0)
        self.assertEqual(duplicate_metrics([], truth)["recall"], 0.0)

    def test_baseline_finds_most_injected_duplicates(self):
        estate = generate(seed=42)
        pred = find_duplicate_pairs(estate["cis"])
        m = duplicate_metrics(pred, estate["ground_truth"]["duplicate_pairs"])
        self.assertGreaterEqual(m["recall"], 0.8)
        self.assertGreaterEqual(m["precision"], 0.8)


    def test_hard_benchmark_is_not_saturated(self):
        # A benchmark the baseline solves perfectly cannot show improvement.
        for seed in (1, 7, 42, 99):
            estate = generate(seed=seed, difficulty="hard")
            pred = find_duplicate_pairs(estate["cis"])
            m = duplicate_metrics(pred, estate["ground_truth"]["duplicate_pairs"])
            self.assertLess(m["f1"], 0.95)


if __name__ == "__main__":
    unittest.main()
