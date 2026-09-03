import pytest
from app.engine.types import RiskLevel
from app.engine.features.extractor import FeatureContext
from app.engine.detectors.ml_detector import MlFraudDetector
from app.schemas.transaction import PaymentRequest
from app.schemas.customer import CustomerCreate
from app.schemas.merchant import MerchantCreate

@pytest.fixture
def base_request():
    return PaymentRequest(
        external_transaction_id="test_ml_tx_1",
        amount=500.0,
        currency="USD",
        customer=CustomerCreate(external_customer_id="test_cust_ml"),
        merchant=MerchantCreate(external_merchant_id="test_merch_ml")
    )

def test_ml_detector_no_model(base_request):
    detector = MlFraudDetector()
    # Force model to be None to simulate missing model
    detector.loader._model = None
    
    context = FeatureContext(base_request)
    signal = detector.evaluate(context)
    
    # Should safely return None
    assert signal is None

def test_ml_detector_mocked_prediction(base_request, monkeypatch):
    detector = MlFraudDetector()
    
    # Mock the predict_proba method
    def mock_predict_proba(context):
        return 0.85 # High probability of fraud
        
    monkeypatch.setattr(detector.loader, "predict_proba", mock_predict_proba)
    # Mock the model property so it doesn't return early
    detector.loader._model = True 
    
    context = FeatureContext(base_request)
    signal = detector.evaluate(context)
    
    assert signal is not None
    assert signal.name == "ml_fraud_model"
    assert signal.value == 0.85
    assert signal.severity == RiskLevel.CRITICAL
    assert signal.evidence["fraud_probability"] == 0.85
