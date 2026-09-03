from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class CustomerBase(BaseModel):
    external_customer_id: str
    account_created_at: Optional[datetime] = None
    status: str = "active"

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
