from pydantic import BaseModel, Field, ConfigDict
import uuid
from datetime import datetime
from typing import Optional
from .customer import CustomerCreate
from .merchant import MerchantCreate
from .device import DeviceCreate
from .risk import RiskEvaluationResponse

class PaymentRequest(BaseModel):
    external_transaction_id: str
    amount: float = Field(..., gt=0)
    currency: str
    payment_method: Optional[str] = None
    
    ip_address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Required relations data for the synthetic provider
    customer: CustomerCreate
    merchant: MerchantCreate
    device: Optional[DeviceCreate] = None
    
    is_background_seed: bool = False

class TransactionResponse(BaseModel):
    id: uuid.UUID
    external_transaction_id: str
    customer_id: uuid.UUID
    merchant_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None
    
    amount: float
    currency: str
    payment_method: Optional[str]
    status: str
    created_at: datetime
    
    ip_address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    risk_evaluation: Optional['RiskEvaluationResponse'] = None
    
    model_config = ConfigDict(from_attributes=True)
