from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class DeviceBase(BaseModel):
    device_fingerprint: str
    device_type: Optional[str] = None
    operating_system: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: uuid.UUID
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
