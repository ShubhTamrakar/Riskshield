from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Decision(str, Enum):
    APPROVE = "APPROVE"
    MONITOR = "MONITOR"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"

class RiskSignal(BaseModel):
    name: str
    value: float  # typically 0 to 1
    severity: RiskLevel
    explanation: str
    evidence: dict[str, Any]

class RiskEvaluationResult(BaseModel):
    score: int  # 0 to 100
    risk_level: RiskLevel
    decision: Decision
    signals: list[RiskSignal]
