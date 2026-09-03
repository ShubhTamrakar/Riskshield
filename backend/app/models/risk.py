import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import String, Integer, ForeignKey, DateTime

from app.models.base import Base

class RiskEvaluation(Base):
    __tablename__ = "risk_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transactions.id"), unique=True, nullable=False)
    
    score: Mapped[int] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String, nullable=True)
    signals: Mapped[list] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="risk_evaluation")
