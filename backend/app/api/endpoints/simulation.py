import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.api import deps
from app.models.simulation import SimulationRun
from app.simulation.scenarios import SCENARIOS
from app.simulation.runner import run_simulation
from fastapi import Request
from app.security.auth import get_current_user, CurrentUser, require_analyst
from app.security.rate_limit import limiter

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class SimulationConfig(BaseModel):
    scenario:       str   = Field(..., description="One of the scenario keys")
    n_transactions: int   = Field(50, ge=5, le=1000)
    fraud_pct:      float = Field(0.20, ge=0.01, le=0.99)
    seed:           int   = Field(42)
    mode:           str   = Field("full", description="rules_only | ml_only | rules_ml | full")


class SimulationRunResponse(BaseModel):
    id:              uuid.UUID
    created_at:      datetime
    completed_at:    Optional[datetime]
    status:          str
    config:          dict
    metrics:         Optional[dict]
    model_version:   Optional[str]
    dataset_version: Optional[str]
    run_duration_s:  Optional[float]
    error:           Optional[str]

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/scenarios")
@limiter.limit("60/minute")
async def list_scenarios(
    request: Request,
    user: CurrentUser = Depends(get_current_user)
) -> Any:
    """Return all available scenario keys and human labels."""
    from app.simulation.scenarios import SCENARIO_LABELS
    return [{"key": k, "label": SCENARIO_LABELS[k]} for k in SCENARIOS]


@router.post("/runs", status_code=202)
@limiter.limit("20/minute")
async def create_run(
    request: Request,
    config: SimulationConfig,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(require_analyst)
) -> Any:
    """Trigger a new simulation run (async background task).

    Returns immediately with a run ID. Poll GET /simulation/runs/{id} for results.
    """
    if config.scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{config.scenario}'. Valid: {list(SCENARIOS.keys())}"
        )

    valid_modes = ("rules_only", "ml_only", "rules_ml", "full")
    if config.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"mode must be one of {valid_modes}")

    run_id = uuid.uuid4()
    run = SimulationRun(
        id=run_id,
        status="pending",
        config={
            "scenario":       config.scenario,
            "n_transactions": config.n_transactions,
            "fraud_pct":      config.fraud_pct,
            "seed":           config.seed,
            "mode":           config.mode,
        },
        model_version="v1",
        dataset_version=f"synthetic-seed{config.seed}",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Background task — receives a fresh DB session inside the runner
    from app.db.session import AsyncSessionLocal

    async def _bg_run():
        async with AsyncSessionLocal() as bg_db:
            await run_simulation(
                bg_db,
                run_id=run_id,
                scenario=config.scenario,
                n_transactions=config.n_transactions,
                fraud_pct=config.fraud_pct,
                seed=config.seed,
                mode=config.mode,
            )

    background_tasks.add_task(_bg_run)

    return {"run_id": str(run_id), "status": "pending"}


@router.get("/runs", response_model=List[SimulationRunResponse])
@limiter.limit("60/minute")
async def list_runs(
    request: Request,
    limit: int = 20,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(get_current_user)
) -> Any:
    result = await db.execute(
        select(SimulationRun).order_by(desc(SimulationRun.created_at)).limit(limit)
    )
    return result.scalars().all()


@router.get("/runs/{run_id}", response_model=SimulationRunResponse)
@limiter.limit("60/minute")
async def get_run(
    request: Request,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(get_current_user)
) -> Any:
    run = await db.get(SimulationRun, run_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Simulation run not found"}
        )
    return run
