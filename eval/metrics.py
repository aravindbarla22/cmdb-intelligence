"""Scoring against injected ground truth."""


def _prf(pred, true):
    tp, fp, fn = len(pred & true), len(pred - true), len(true - pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return tp, fp, fn, precision, recall, f1


def _key(pair):
    return frozenset((pair["master"], pair["duplicate"]))


def duplicate_metrics(predicted, truth):
    """Precision, recall and F1 over duplicate pairs, plus master-selection accuracy."""
    tp, fp, fn, precision, recall, f1 = _prf({_key(p) for p in predicted},
                                             {_key(t) for t in truth})
    true_master = {_key(t): t["master"] for t in truth}
    correct = sum(1 for p in predicted if _key(p) in true_master
                  and true_master[_key(p)] == p["master"])
    master_accuracy = correct / tp if tp else 0.0
    return {
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": round(precision, 3), "recall": round(recall, 3),
        "f1": round(f1, 3), "master_selection_accuracy": round(master_accuracy, 3),
    }


def drift_metrics(predicted, truth):
    """Precision, recall and F1 over (CI, field) drift findings."""
    tp, fp, fn, precision, recall, f1 = _prf({(p["ci_id"], p["field"]) for p in predicted},
                                             {(t["ci_id"], t["field"]) for t in truth})
    return {
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
    }
