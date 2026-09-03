import pytest
import json
import uuid
from app.ai.investigator import build_sanitized_payload, investigate_transaction
from app.ai.guardrails import generate_fallback_report
from app.models.transaction import Transaction
from app.models.risk import RiskEvaluation

def test_payload_sanitization():
    tx_id = uuid.uuid4()
    transaction = Transaction(
        id=tx_id,
        amount=500.0,
        status="pending",
        # Simulate PII or other data
        customer_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        ip_address="192.168.1.1"
    )
    
    risk_eval = RiskEvaluation(
        transaction_id=tx_id,
        score=94,
        risk_level="CRITICAL",
        decision="BLOCK",
        signals=[
            {"name": "velocity", "value": 12, "explanation": "12 transactions in 5 minutes"}
        ]
    )
    
    payload_str = build_sanitized_payload(transaction, risk_eval)
    payload = json.loads(payload_str)
    
    # Check that it includes necessary data
    assert payload["transaction"]["amount"] == 500.0
    assert payload["risk_evaluation"]["score"] == 94
    assert len(payload["risk_evaluation"]["signals"]) == 1
    
    # Check that it explicitly omits PII
    assert "ip_address" not in payload["transaction"]
    assert "customer_id" not in payload["transaction"]

@pytest.mark.asyncio
async def test_fallback_generation():
    risk_eval = RiskEvaluation(
        transaction_id=uuid.uuid4(),
        score=94,
        risk_level="CRITICAL",
        decision="BLOCK",
        signals=[
            {"name": "velocity", "value": 12, "explanation": "12 transactions in 5 minutes"}
        ]
    )
    
    report = generate_fallback_report(risk_eval)
    
    assert report.executive_summary == "AI Investigation Service is currently unavailable. Displaying deterministic fallback."
    assert report.confidence_statement == "LOW - Fallback generated."
    assert report.primary_risk_factors == ["velocity"]

@pytest.mark.asyncio
async def test_investigator_fallback_when_no_api_key():
    # Because GEMINI_API_KEY is not set in test env, this should fallback
    transaction = Transaction(id=uuid.uuid4(), amount=100.0, status="pending")
    risk_eval = RiskEvaluation(
        transaction_id=transaction.id,
        score=90,
        risk_level="HIGH",
        decision="BLOCK",
        signals=[{"name": "amount_anomaly", "explanation": "High amount"}]
    )
    
    report = await investigate_transaction(transaction, risk_eval)
    assert report.primary_risk_factors == ["amount_anomaly"]
    assert report.confidence_statement == "LOW - Fallback generated."
