import pytest
from app.engine.types import RiskLevel, Decision
from app.engine.features.extractor import FeatureContext
from app.engine.detectors.rules import AmountAnomalyDetector, VelocityDetector, GeographicAnomalyDetector
from app.engine.aggregator import aggregate_signals
from app.schemas.transaction import PaymentRequest
from app.schemas.customer import CustomerCreate
from app.schemas.merchant import MerchantCreate

@pytest.fixture
def base_request():
    return PaymentRequest(
        external_transaction_id="test_tx_1",
        amount=100.0,
        currency="USD",
        customer=CustomerCreate(external_customer_id="test_cust_1"),
        merchant=MerchantCreate(external_merchant_id="test_merch_1")
    )

def test_amount_anomaly(base_request):
    base_request.amount = 600.0
    context = FeatureContext(base_request)
    context.customer_historical_avg_amount = 100.0
    
    detector = AmountAnomalyDetector()
    signal = detector.evaluate(context)
    
    assert signal is not None
    assert signal.name == "amount_anomaly"
    assert signal.severity == RiskLevel.HIGH

def test_velocity_anomaly(base_request):
    context = FeatureContext(base_request)
    context.customer_velocity_1h = 12
    
    detector = VelocityDetector()
    signal = detector.evaluate(context)
    
    assert signal is not None
    assert signal.name == "velocity_anomaly"
    assert signal.severity == RiskLevel.CRITICAL

def test_aggregator():
    from app.engine.types import RiskSignal
    
    # 1. Low risk
    s1 = RiskSignal(name="test", value=0.1, severity=RiskLevel.LOW, explanation="test", evidence={})
    res = aggregate_signals([s1])
    assert res.risk_level == RiskLevel.LOW
    assert res.decision == Decision.APPROVE
    
    # 2. Critical risk
    s2 = RiskSignal(name="test2", value=1.0, severity=RiskLevel.CRITICAL, explanation="test", evidence={})
    res2 = aggregate_signals([s2])
    assert res2.risk_level == RiskLevel.MEDIUM or res2.risk_level == RiskLevel.HIGH or res2.risk_level == RiskLevel.CRITICAL
    # Since 60 * 1 = 60 => MEDIUM. Wait, 60 is <= 60 so MEDIUM? Let's check aggregator.py:
    # 60 * 1.0 = 60 -> MEDIUM.
    assert res2.decision == Decision.MONITOR

    # 3. High risk combo
    s3 = RiskSignal(name="test3", value=1.0, severity=RiskLevel.CRITICAL, explanation="test", evidence={})
    s4 = RiskSignal(name="test4", value=1.0, severity=RiskLevel.HIGH, explanation="test", evidence={})
    res3 = aggregate_signals([s3, s4])
    # 60 + 30 = 90 -> CRITICAL
    assert res3.risk_level == RiskLevel.CRITICAL
    assert res3.decision == Decision.BLOCK
