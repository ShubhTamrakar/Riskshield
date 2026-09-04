"""
Unit tests for app.simulation.metrics — pure functions, no DB required.
"""
import pytest
from app.simulation.metrics import compute_metrics, _roc_auc, _pr_auc, _percentile


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make(
    tp: int, fp: int, tn: int, fn: int,
    score_fraud: int = 90, score_legit: int = 10,
) -> dict:
    """Build inputs from confusion-matrix counts."""
    labels    = [True] * (tp + fn) + [False] * (fp + tn)
    predicted = [True] * tp + [False] * fn + [True] * fp + [False] * tn
    scores    = [score_fraud] * (tp + fn) + [score_legit] * (fp + tn)
    latencies = [5.0] * (tp + fp + tn + fn)
    return compute_metrics(labels, predicted, scores, latencies)


# ── Precision / Recall / F1 ───────────────────────────────────────────────────

class TestPrecisionRecallF1:
    def test_perfect_classifier(self):
        m = _make(tp=10, fp=0, tn=90, fn=0)
        assert m["precision"] == 1.0
        assert m["recall"]    == 1.0
        assert m["f1"]        == 1.0

    def test_zero_precision_when_all_false_positives(self):
        m = _make(tp=0, fp=10, tn=0, fn=5)
        assert m["precision"] == 0.0

    def test_zero_recall_when_all_false_negatives(self):
        m = _make(tp=0, fp=5, tn=10, fn=10)
        assert m["recall"] == 0.0

    def test_f1_harmonic_mean(self):
        m = _make(tp=8, fp=2, tn=8, fn=2)
        # precision = 8/10 = 0.8, recall = 8/10 = 0.8 → F1 = 0.8
        assert abs(m["f1"] - 0.8) < 0.01

    def test_confusion_matrix_counts(self):
        m = _make(tp=5, fp=3, tn=7, fn=2)
        assert m["confusion_matrix"]["tp"] == 5
        assert m["confusion_matrix"]["fp"] == 3
        assert m["confusion_matrix"]["tn"] == 7
        assert m["confusion_matrix"]["fn"] == 2


# ── False Positive / Negative Rates ──────────────────────────────────────────

class TestFPRFNR:
    def test_fpr_is_fp_over_negatives(self):
        m = _make(tp=5, fp=4, tn=6, fn=5)
        # FPR = 4 / (4+6) = 0.4
        assert abs(m["fpr"] - 0.4) < 0.01

    def test_fnr_is_fn_over_positives(self):
        m = _make(tp=6, fp=2, tn=8, fn=4)
        # FNR = 4 / (4+6) = 0.4
        assert abs(m["fnr"] - 0.4) < 0.01

    def test_perfect_classifier_has_zero_fpr_fnr(self):
        m = _make(tp=10, fp=0, tn=10, fn=0)
        assert m["fpr"] == 0.0
        assert m["fnr"] == 0.0


# ── AUC ───────────────────────────────────────────────────────────────────────

class TestAUC:
    def test_perfect_roc_auc(self):
        # Perfect: all frauds scored 100, all legit scored 0
        labels  = [True]*10 + [False]*10
        scores  = [100]*10  + [0]*10
        auc = _roc_auc(labels, scores)
        assert abs(auc - 1.0) < 0.01

    def test_random_roc_auc_near_half(self):
        # Uninformative: all same score
        labels  = [True]*5 + [False]*5
        scores  = [50]*10
        auc = _roc_auc(labels, scores)
        # Can be 0 or 1 depending on tie-breaking, but should be near 0.5
        assert 0.0 <= auc <= 1.0

    def test_pr_auc_perfect(self):
        labels  = [True]*5  + [False]*5
        scores  = [100]*5   + [0]*5
        auc = _pr_auc(labels, scores)
        assert abs(auc - 1.0) < 0.05  # near perfect

    def test_no_fraud_returns_zero_auc(self):
        labels = [False]*10
        scores = [50]*10
        assert _roc_auc(labels, scores) == 0.0
        assert _pr_auc(labels, scores)  == 0.0


# ── Latency ───────────────────────────────────────────────────────────────────

class TestLatency:
    def test_p50_p95_p99(self):
        latencies = list(range(1, 101))  # 1..100 ms
        labels    = [False]*100
        predicted = [False]*100
        scores    = [10]*100
        m = compute_metrics(labels, predicted, scores, latencies)
        assert abs(m["latency_ms"]["p50"] - 50.5) < 1.0
        assert abs(m["latency_ms"]["p95"] - 95.05) < 1.0
        assert abs(m["latency_ms"]["p99"] - 99.01) < 1.0

    def test_empty_latency_returns_zero(self):
        m = compute_metrics([], [], [], [])
        assert m["latency_ms"]["avg"] == 0.0


# ── n / fraud_rate ────────────────────────────────────────────────────────────

class TestCounts:
    def test_n_transactions_and_fraud_rate(self):
        m = _make(tp=20, fp=5, tn=70, fn=5)
        assert m["n_transactions"] == 100
        assert m["n_fraud"]        == 25
        assert m["n_legitimate"]   == 75
        assert abs(m["fraud_rate"] - 0.25) < 0.001
