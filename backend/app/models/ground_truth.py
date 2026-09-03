import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, ForeignKey, DateTime

from app.models.base import Base


class GroundTruth(Base):
    """
    Stores the true fraud label for each transaction.

    This table is NEVER joined to the transaction table during model inference.
    It exists solely for training, evaluation, and auditing purposes.
    """
    __tablename__ = "ground_truth"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id"), unique=True, nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String, nullable=False, index=True)
    fraud_scenario: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    transaction = relationship("Transaction", back_populates="ground_truth")
