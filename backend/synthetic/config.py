from enum import Enum
from pydantic import BaseModel

class FraudLabel(str, Enum):
    LEGITIMATE = "LEGITIMATE"
    FRAUD = "FRAUD"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    CARD_TESTING = "CARD_TESTING"
    VELOCITY_ATTACK = "VELOCITY_ATTACK"
    HIGH_VALUE_ANOMALY = "HIGH_VALUE_ANOMALY"
    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"
    LOCATION_ANOMALY = "LOCATION_ANOMALY"
    NEW_DEVICE_ATTACK = "NEW_DEVICE_ATTACK"
    REFUND_ANOMALY = "REFUND_ANOMALY"
    COORDINATED_FRAUD = "COORDINATED_FRAUD"
    SHARED_DEVICE = "SHARED_DEVICE"
    SHARED_IP = "SHARED_IP"
    MULTIPLE_FAILED = "MULTIPLE_FAILED"
    SUSPICIOUS_MERCHANT = "SUSPICIOUS_MERCHANT"
    OTHER = "OTHER"

class DatasetConfig(BaseModel):
    name: str
    num_customers: int
    num_merchants: int
    target_transactions: int
    fraud_rate: float
    seed: int = 42

DATASET_PRESETS = {
    "dev": DatasetConfig(
        name="dev",
        num_customers=100,
        num_merchants=20,
        target_transactions=1000,
        fraud_rate=0.20,
    ),
    "medium": DatasetConfig(
        name="medium",
        num_customers=1000,
        num_merchants=50,
        target_transactions=10000,
        fraud_rate=0.08,
    ),
    "large": DatasetConfig(
        name="large",
        num_customers=10000,
        num_merchants=100,
        target_transactions=50000,
        fraud_rate=0.05,
    ),
}
