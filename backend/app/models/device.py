import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, DateTime

from app.models.base import Base

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_fingerprint: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    device_type: Mapped[str] = mapped_column(String, nullable=True)
    operating_system: Mapped[str] = mapped_column(String, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    transactions = relationship("Transaction", back_populates="device")
