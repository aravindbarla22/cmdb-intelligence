"""Generate synthetic estates, run the baseline detectors, and score them.

Reports easy and hard difficulty separately. A benchmark that a baseline
solves perfectly cannot show improvement, so the hard setting matters.
"""
import argparse
import json

from core.drift import detect_drift_exact, detect_drift_policy
from core.match import find_duplicate_pairs
from data.synth import generate
from eval.metrics import drift_metrics, duplicate_metrics


def run(seed, apps, threshold, difficulty):
    estate = generate(seed=seed, n_apps=apps, difficulty=difficulty)
    truth = estate["ground_truth"]
    pairs = find_duplicate_pairs(estate["cis"], threshold=threshold)
    exact = detect_drift_exact(estate["cis"], estate["baseline"])
    policy = detect_drift_policy(estate["cis"], estate["baseline"], estate["policy"])
    return {
        "difficulty": difficulty,
        "cis": len(estate["cis"]),
        "injected_duplicate_pairs": len(truth["duplicate_pairs"]),
        "injected_drift_findings": len(truth["drift"]),
        "approved_benign_changes": len(truth["benign_changes"]),
        "baseline_duplicate_detection": duplicate_metrics(pairs, truth["duplicate_pairs"]),
        "drift_detection_exact_diff": drift_metrics(exact, truth["drift"]),
        "drift_detection_policy_aware": drift_metrics(policy, truth["drift"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--apps", type=int, default=100)
    ap.add_argument("--threshold", type=float, default=0.92)
    args = ap.parse_args()
    results = [run(args.seed, args.apps, args.threshold, d) for d in ("easy", "hard")]
    print(json.dumps({"seed": args.seed, "results": results}, indent=2))


if __name__ == "__main__":
    main()
