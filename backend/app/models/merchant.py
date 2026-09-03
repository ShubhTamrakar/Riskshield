import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String

from app.models.base import Base, TimestampMixin

class Merchant(Base, TimestampMixin):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_merchant_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

    transactions = relationship("Transaction", back_populates="merchant")
