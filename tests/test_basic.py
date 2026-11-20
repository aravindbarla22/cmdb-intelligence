import unittest

from core.drift import detect_drift_exact, detect_drift_policy
from core.match import find_duplicate_pairs, select_master
from core.normalize import normalize_name
from data.synth import generate
from eval.metrics import drift_metrics, duplicate_metrics


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

    def test_drift_exact_diff_is_correct_when_no_changes_are_approved(self):
        e = generate(seed=42)
        found = detect_drift_exact(e["cis"], e["baseline"])
        m = drift_metrics(found, e["ground_truth"]["drift"])
        self.assertEqual((m["precision"], m["recall"]), (1.0, 1.0))

    def test_exact_diff_flags_approved_changes_in_hard_mode(self):
        for seed in (1, 7, 42, 99):
            e = generate(seed=seed, difficulty="hard")
            self.assertTrue(e["ground_truth"]["benign_changes"])
            found = detect_drift_exact(e["cis"], e["baseline"])
            m = drift_metrics(found, e["ground_truth"]["drift"])
            self.assertEqual(m["recall"], 1.0)
            self.assertLess(m["precision"], 1.0)

    def test_policy_detector_matches_policy_defined_truth(self):
        # Truth is defined by the same policy, so this is a reference ceiling,
        # not evidence of performance on real data.
        for seed in (1, 7, 42, 99):
            e = generate(seed=seed, difficulty="hard")
            found = detect_drift_policy(e["cis"], e["baseline"], e["policy"])
            m = drift_metrics(found, e["ground_truth"]["drift"])
            self.assertEqual((m["precision"], m["recall"]), (1.0, 1.0))

    def test_root_login_drift_is_critical(self):
        cis = [{"id": "s", "class": "server", "attrs": {"ssh_root_login": True}}]
        found = detect_drift_policy(cis, {"s": {"ssh_root_login": False}}, {})
        self.assertEqual(found[0]["severity"], "critical")


if __name__ == "__main__":
    unittest.main()
