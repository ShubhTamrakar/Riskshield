from typing import Optional
from app.engine.types import RiskSignal, RiskLevel
from app.engine.features.extractor import FeatureContext
from app.engine.detectors import BaseDetector
from app.engine.ml import FraudModelLoader


class MlFraudDetector(BaseDetector):
    def __init__(self):
        self.loader = FraudModelLoader.get_instance()

    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        if self.loader._model is None:
            return None

        prob = self.loader.predict_proba(context)
        threshold = self.loader.threshold
        
        reasons = self.loader.explain_prediction(context)
        reasons_str = ", ".join(reasons)

        # CRITICAL: extremely high confidence
        if prob >= max(threshold, 0.95):
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.CRITICAL,
                explanation=f"ML predicts fraud with {prob:.1%} probability. Key factors: {reasons_str}.",
                evidence={"fraud_probability": prob, "threshold": threshold, "model_version": "v2"}
            )

        # HIGH: elevated suspicion
        if prob >= max(threshold - 0.10, 0.85):
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.HIGH,
                explanation=f"ML flags elevated fraud probability ({prob:.1%}). Key factors: {reasons_str}.",
                evidence={"fraud_probability": prob, "threshold": threshold, "model_version": "v2"}
            )

        # MEDIUM: worth noting
        if prob >= 0.70:
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.MEDIUM,
                explanation=f"ML reports a moderate fraud probability ({prob:.1%}). Key factors: {reasons_str}.",
                evidence={"fraud_probability": prob, "threshold": threshold, "model_version": "v2"}
            )

        return None
