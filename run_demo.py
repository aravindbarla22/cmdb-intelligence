"""Generate synthetic estates, run the baseline duplicate matcher, and score it.

Reports easy and hard difficulty separately. A benchmark that the baseline
solves perfectly cannot show improvement, so the hard setting matters.
"""
import argparse
import json

from core.match import find_duplicate_pairs
from data.synth import generate
from eval.metrics import duplicate_metrics


def run(seed, apps, threshold, difficulty):
    estate = generate(seed=seed, n_apps=apps, difficulty=difficulty)
    predicted = find_duplicate_pairs(estate["cis"], threshold=threshold)
    metrics = duplicate_metrics(predicted, estate["ground_truth"]["duplicate_pairs"])
    return {
        "difficulty": difficulty,
        "cis": len(estate["cis"]),
        "injected_duplicate_pairs": len(estate["ground_truth"]["duplicate_pairs"]),
        "baseline_duplicate_detection": metrics,
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
