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

        # CRITICAL: above the precision-optimised threshold — very high confidence
        if prob >= threshold:
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.CRITICAL,
                explanation=f"ML model predicts fraud with {prob:.1%} probability (threshold: {threshold:.1%}).",
                evidence={"fraud_probability": prob, "threshold": threshold, "model_version": "v2"}
            )

        # HIGH: within 10 pp of the threshold — elevated suspicion
        if prob >= max(threshold - 0.10, 0.60):
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.HIGH,
                explanation=f"ML model flags elevated fraud probability ({prob:.1%}).",
                evidence={"fraud_probability": prob, "threshold": threshold, "model_version": "v2"}
            )

        # MEDIUM: above 0.40 — worth noting
        if prob >= 0.40:
            return RiskSignal(
                name="ml_fraud_model",
                value=prob,
                severity=RiskLevel.MEDIUM,
                explanation=f"ML model reports a moderate fraud probability ({prob:.1%}).",
                evidence={"fraud_probability": prob, "threshold": threshold, "model_version": "v2"}
            )

        return None
