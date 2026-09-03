from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class RiskEvaluationRequest(BaseModel):
    transaction_id: uuid.UUID

class RiskEvaluationResponse(BaseModel):
    transaction_id: uuid.UUID
    score: Optional[int] = None
    risk_level: Optional[str] = None
    decision: Optional[str] = None
    signals: Optional[list] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
