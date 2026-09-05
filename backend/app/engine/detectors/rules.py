from typing import Optional
from app.engine.types import RiskSignal, RiskLevel
from app.engine.features.extractor import FeatureContext
from app.engine.detectors import BaseDetector

class AmountAnomalyDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        amount = context.request.amount
        avg_amount = context.customer_historical_avg_amount
        
        if avg_amount > 0 and amount > avg_amount * 5:
            return RiskSignal(
                name="amount_anomaly",
                value=min(amount / (avg_amount * 10), 1.0),
                severity=RiskLevel.HIGH,
                explanation=f"Transaction amount (${amount:.2f}) is significantly higher than historical average (${avg_amount:.2f}).",
                evidence={"amount": amount, "historical_avg": avg_amount, "multiplier": amount / avg_amount}
            )
        return None

class VelocityDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        vel_1h = context.customer_velocity_1h
        
        if vel_1h > 10:
            return RiskSignal(
                name="velocity_anomaly",
                value=min(vel_1h / 20.0, 1.0),
                severity=RiskLevel.CRITICAL,
                explanation=f"High transaction velocity detected: {vel_1h} transactions in the last hour.",
                evidence={"velocity_1h": vel_1h}
            )
        elif vel_1h > 5:
            return RiskSignal(
                name="velocity_anomaly",
                value=0.5,
                severity=RiskLevel.MEDIUM,
                explanation=f"Elevated transaction velocity detected: {vel_1h} transactions in the last hour.",
                evidence={"velocity_1h": vel_1h}
            )
        return None

class DeviceAnomalyDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        if context.is_new_device:
            return RiskSignal(
                name="new_device",
                value=0.6,
                severity=RiskLevel.MEDIUM,
                explanation="Transaction originated from a previously unseen device for this customer.",
                evidence={"is_new_device": True}
            )
        
        if context.device_customer_count > 3:
            return RiskSignal(
                name="shared_device",
                value=0.9,
                severity=RiskLevel.CRITICAL,
                explanation=f"Device has been used by {context.device_customer_count} distinct customers.",
                evidence={"device_customer_count": context.device_customer_count}
            )
            
        return None

class GeographicAnomalyDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        dist = context.distance_from_home_km
        
        if dist > 5000:
            return RiskSignal(
                name="geographic_anomaly",
                value=1.0,
                severity=RiskLevel.HIGH,
                explanation=f"Transaction location is {dist:.0f} km away from usual activity.",
                evidence={"distance_km": dist}
            )
        elif dist > 1000:
            return RiskSignal(
                name="geographic_anomaly",
                value=0.5,
                severity=RiskLevel.MEDIUM,
                explanation=f"Transaction location is {dist:.0f} km away from usual activity.",
                evidence={"distance_km": dist}
            )
        return None

class FailedPaymentSequenceDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        fails = context.failed_payment_sequence
        if fails >= 3:
            return RiskSignal(
                name="failed_payment_sequence",
                value=min(fails / 6.0, 1.0),
                severity=RiskLevel.HIGH,
                explanation=f"Customer had {fails} consecutive failed payments prior to this transaction.",
                evidence={"failed_sequence_count": fails}
            )
        return None

class SharedIpDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        if context.ip_customer_count > 5:
            return RiskSignal(
                name="shared_ip",
                value=0.8,
                severity=RiskLevel.HIGH,
                explanation=f"IP address has been used by {context.ip_customer_count} distinct customers.",
                evidence={"ip_customer_count": context.ip_customer_count}
            )
        return None

class MicroTransactionDetector(BaseDetector):
    def evaluate(self, context: FeatureContext) -> Optional[RiskSignal]:
        amount = context.request.amount
        
        # Extremely small transactions (e.g. $1 or $2) are classic card testing probes
        if amount < 2.50:
            return RiskSignal(
                name="micro_transaction",
                value=1.0,
                severity=RiskLevel.CRITICAL,
                explanation=f"Transaction amount (${amount:.2f}) is extremely small, indicative of card testing.",
                evidence={"amount": amount}
            )
        return None

from app.engine.detectors.ml_detector import MlFraudDetector

ALL_DETECTORS = [
    AmountAnomalyDetector(),
    VelocityDetector(),
    DeviceAnomalyDetector(),
    GeographicAnomalyDetector(),
    FailedPaymentSequenceDetector(),
    SharedIpDetector(),
    MicroTransactionDetector(),
    MlFraudDetector()
]
