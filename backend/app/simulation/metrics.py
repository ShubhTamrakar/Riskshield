"""
Pure-function metrics calculator.
Isolated from DB and engine — can be unit-tested independently.
"""
from __future__ import annotations
import math
from typing import List, Tuple


def compute_metrics(
    labels: List[bool],
    predicted_fraud: List[bool],
    scores: List[int],
    latencies_ms: List[float],
) -> dict:
    """Compute all simulation metrics.

    Args:
        labels:          Ground-truth — True = fraud.
        predicted_fraud: Engine decision — True = BLOCK (or REVIEW).
        scores:          Continuous risk score 0–100 for AUC computation.
        latencies_ms:    Per-transaction evaluation latency in milliseconds.

    Returns:
        Dict with all metrics.
    """
    n = len(labels)
    if n == 0:
        return _empty()

    # Confusion matrix
    tp = sum(1 for l, p in zip(labels, predicted_fraud) if l and p)
    fp = sum(1 for l, p in zip(labels, predicted_fraud) if not l and p)
    tn = sum(1 for l, p in zip(labels, predicted_fraud) if not l and not p)
    fn = sum(1 for l, p in zip(labels, predicted_fraud) if l and not p)

    precision  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall     = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1         = (2 * precision * recall / (precision + recall)
                  if (precision + recall) > 0 else 0.0)
    fpr        = fp / (fp + tn) if (fp + tn) > 0 else 0.0  # False Positive Rate
    fnr        = fn / (fn + tp) if (fn + tp) > 0 else 0.0  # False Negative Rate

    roc_auc = _roc_auc(labels, scores)
    pr_auc  = _pr_auc(labels, scores)

    # Latency percentiles
    sorted_lat = sorted(latencies_ms)
    p50 = _percentile(sorted_lat, 50)
    p95 = _percentile(sorted_lat, 95)
    p99 = _percentile(sorted_lat, 99)
    avg = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    fraud_count = sum(labels)
    legit_count = n - fraud_count

    return {
        "n_transactions": n,
        "n_fraud": fraud_count,
        "n_legitimate": legit_count,
        "fraud_rate": round(fraud_count / n, 4) if n > 0 else 0.0,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision":  round(precision, 4),
        "recall":     round(recall, 4),
        "f1":         round(f1, 4),
        "fpr":        round(fpr, 4),
        "fnr":        round(fnr, 4),
        "roc_auc":    round(roc_auc, 4),
        "pr_auc":     round(pr_auc, 4),
        "latency_ms": {
            "avg": round(avg, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        },
    }


def _empty() -> dict:
    return {
        "n_transactions": 0, "n_fraud": 0, "n_legitimate": 0, "fraud_rate": 0.0,
        "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
        "precision": 0.0, "recall": 0.0, "f1": 0.0, "fpr": 0.0, "fnr": 0.0,
        "roc_auc": 0.0, "pr_auc": 0.0,
        "latency_ms": {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0},
    }


def _percentile(sorted_vals: List[float], pct: int) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _roc_auc(labels: List[bool], scores: List[int]) -> float:
    """Trapezoidal AUC via manual sort."""
    paired = sorted(zip(scores, labels), key=lambda x: -x[0])
    tp = fp = 0
    tp_total = sum(labels)
    fp_total = len(labels) - tp_total
    if tp_total == 0 or fp_total == 0:
        return 0.0

    prev_tp, prev_fp = 0, 0
    auc = 0.0
    for _, label in paired:
        if label:
            tp += 1
        else:
            fp += 1
        auc += (fp - prev_fp) * (tp + prev_tp) / 2.0
        prev_tp, prev_fp = tp, fp

    return auc / (tp_total * fp_total)


def _pr_auc(labels: List[bool], scores: List[int]) -> float:
    """PR-AUC via trapezoidal rule."""
    paired = sorted(zip(scores, labels), key=lambda x: -x[0])
    tp = fp = 0
    tp_total = sum(labels)
    if tp_total == 0:
        return 0.0

    prev_rec = 0.0
    prev_prec = 1.0
    auc = 0.0
    for _, label in paired:
        if label:
            tp += 1
        else:
            fp += 1
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec  = tp / tp_total
        auc += (rec - prev_rec) * (prec + prev_prec) / 2.0
        prev_rec, prev_prec = rec, prec

    return auc
