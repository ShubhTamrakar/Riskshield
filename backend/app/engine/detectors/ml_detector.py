from typing import Optional
from app.engine.types import RiskSignal, RiskLevel
from app.engine.features.extractor import FeatureContext
from app.engine.detectors import BaseDetector
from app.engine.ml import FraudModelLoader

class MlFraudDetector(BaseDetector):
    def __init__(self):
        self.loader = FraudModelLoader.get_instance()

    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        # If model is not loaded (e.g. not trained yet), just return None
        if self.loader._model is None:
            return None
            
        prob = self.loader.predict_proba(context)
        
        # Decide severity based on probability
        if prob > 0.8:
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.CRITICAL,
                explanation=f"Machine Learning model predicts a high probability of fraud ({prob:.1%}).",
                evidence={"fraud_probability": prob, "model_version": "v1"}
            )
        elif prob > 0.6:
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.HIGH,
                explanation=f"Machine Learning model predicts an elevated probability of fraud ({prob:.1%}).",
                evidence={"fraud_probability": prob, "model_version": "v1"}
            )
        elif prob > 0.4:
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.MEDIUM,
                explanation=f"Machine Learning model predicts a moderate probability of fraud ({prob:.1%}).",
                evidence={"fraud_probability": prob, "model_version": "v1"}
            )
            
        return None
