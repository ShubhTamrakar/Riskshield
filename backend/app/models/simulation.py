import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import String, Float, DateTime

from app.models.base import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)

    # Configuration snapshot
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Results
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Metadata
    model_version: Mapped[str] = mapped_column(String, nullable=True)
    dataset_version: Mapped[str] = mapped_column(String, nullable=True)
    run_duration_s: Mapped[float] = mapped_column(Float, nullable=True)
    error: Mapped[str] = mapped_column(String, nullable=True)
