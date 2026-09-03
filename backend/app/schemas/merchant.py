from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class MerchantBase(BaseModel):
    external_merchant_id: str
    category: Optional[str] = None
    status: str = "active"

class MerchantCreate(MerchantBase):
    pass

class MerchantResponse(MerchantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
