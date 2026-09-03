import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Numeric, ForeignKey, DateTime

from app.models.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_transaction_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    payment_method: Mapped[str] = mapped_column(String, nullable=True)
    
    ip_address: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    device = relationship("Device", back_populates="transactions")
    risk_evaluation = relationship("RiskEvaluation", back_populates="transaction", uselist=False)
    ground_truth = relationship("GroundTruth", back_populates="transaction", uselist=False)
