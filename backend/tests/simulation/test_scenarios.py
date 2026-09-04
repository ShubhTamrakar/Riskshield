"""
Tests for scenario generators — verify label distributions and output structure.
No DB required; generators return plain (PaymentRequest, bool) pairs.
"""
import random
import pytest
from app.simulation.scenarios import (
    SCENARIOS, normal_traffic, velocity_attack, card_testing,
    high_value_anomaly, account_takeover, device_network,
    location_anomaly, mixed_fraud,
)
from app.schemas.transaction import PaymentRequest


RNG = random.Random(99)


def _run(gen, n=50, fraud_pct=0.3):
    return gen(n, fraud_pct, random.Random(42))


class TestScenarioStructure:
    @pytest.mark.parametrize("key,gen", SCENARIOS.items())
    def test_returns_correct_count(self, key, gen):
        pairs = _run(gen, n=20)
        assert len(pairs) == 20, f"{key} returned {len(pairs)} pairs, expected 20"

    @pytest.mark.parametrize("key,gen", SCENARIOS.items())
    def test_all_pairs_are_tuples(self, key, gen):
        pairs = _run(gen, n=10)
        for req, label in pairs:
            assert isinstance(req, PaymentRequest)
            assert isinstance(label, bool)

    @pytest.mark.parametrize("key,gen", SCENARIOS.items())
    def test_all_amounts_positive(self, key, gen):
        pairs = _run(gen, n=20)
        for req, _ in pairs:
            assert req.amount > 0, f"{key}: amount {req.amount} is not positive"

    @pytest.mark.parametrize("key,gen", SCENARIOS.items())
    def test_external_transaction_id_unique(self, key, gen):
        pairs = _run(gen, n=30)
        ids = [req.external_transaction_id for req, _ in pairs]
        assert len(set(ids)) == 30, f"{key}: duplicate transaction IDs found"


class TestFraudRates:
    def test_fraud_rate_approx_matches_target(self):
        """With 200 transactions, actual fraud rate should be within 15pp of target."""
        for pct in (0.1, 0.25, 0.5):
            pairs = normal_traffic(200, pct, random.Random(7))
            actual = sum(1 for _, f in pairs if f) / len(pairs)
            assert abs(actual - pct) < 0.15, f"Expected ~{pct}, got {actual}"

    def test_zero_fraud_produces_no_fraud_labels(self):
        pairs = normal_traffic(50, 0.0, random.Random(1))
        assert all(not f for _, f in pairs)

    def test_full_fraud_produces_all_fraud_labels(self):
        pairs = normal_traffic(50, 1.0, random.Random(1))
        assert all(f for _, f in pairs)


class TestVelocityAttack:
    def test_reuses_customer_pool(self):
        """Velocity scenario should reuse a small pool of customers."""
        pairs = velocity_attack(60, 0.5, random.Random(5))
        customer_ids = {req.customer.external_customer_id for req, _ in pairs}
        # Pool should be << total transactions
        assert len(customer_ids) < 60

    def test_amounts_are_small_for_fraud(self):
        """Card-testing-style: fraudulent amounts should be small."""
        pairs = card_testing(50, 1.0, random.Random(3))
        for req, is_fraud in pairs:
            if is_fraud:
                assert req.amount < 10.0


class TestAccountTakeover:
    def test_fraud_uses_different_location(self):
        """ATO fraud transactions should not all be from US/Seattle."""
        pairs = account_takeover(50, 1.0, random.Random(2))
        countries = {req.country for req, _ in pairs}
        assert "US" not in countries or len(countries) > 1


class TestDeviceNetwork:
    def test_fraud_shares_device(self):
        """Device-network fraud should use a single shared fingerprint."""
        pairs = device_network(40, 1.0, random.Random(8))
        fingerprints = {req.device.device_fingerprint for req, _ in pairs if req.device}
        assert len(fingerprints) == 1  # all share one device


class TestMixedFraud:
    def test_mixed_returns_exact_n(self):
        for n in (7, 14, 50, 100):
            pairs = mixed_fraud(n, 0.3, random.Random(n))
            assert len(pairs) == n

    def test_mixed_has_both_labels(self):
        pairs = mixed_fraud(100, 0.4, random.Random(42))
        labels = [f for _, f in pairs]
        assert any(labels)
        assert not all(labels)
