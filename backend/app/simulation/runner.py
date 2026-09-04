"""
Simulation runner — orchestrates scenario generation → engine evaluation → metrics.

Uses the ACTUAL production evaluate_transaction() path.
"""
from __future__ import annotations
import random
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.evaluator import evaluate_transaction, EngineMode
from app.engine.types import Decision
from app.models.simulation import SimulationRun
from app.simulation.scenarios import SCENARIOS
from app.simulation.metrics import compute_metrics


async def run_simulation(
    db: AsyncSession,
    run_id: uuid.UUID,
    scenario: str,
    n_transactions: int,
    fraud_pct: float,
    seed: int,
    mode: EngineMode = "full",
) -> None:
    """Execute one simulation run.

    Fetches the SimulationRun record, generates transactions, passes each
    through the production risk engine, computes metrics, and persists results.
    """
    # Fetch the run record
    result = await db.get(SimulationRun, run_id)
    if not result:
        return

    result.status = "running"
    await db.commit()

    start_wall = time.perf_counter()

    try:
        rng = random.Random(seed)

        # 1. Generate (PaymentRequest, is_fraud) pairs
        generator = SCENARIOS[scenario]
        pairs = generator(n_transactions, fraud_pct, rng)

        # 2. For each, call the production engine
        labels: list[bool] = []
        predicted_fraud: list[bool] = []
        scores: list[int] = []
        latencies_ms: list[float] = []

        for req, is_fraud in pairs:
            t0 = time.perf_counter()
            evaluation = await evaluate_transaction(db, req, mode=mode)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # BLOCK or REVIEW = engine predicts fraud
            engine_says_fraud = evaluation.decision in (Decision.BLOCK, Decision.REVIEW)

            labels.append(is_fraud)
            predicted_fraud.append(engine_says_fraud)
            scores.append(evaluation.score)
            latencies_ms.append(elapsed_ms)

            # Do NOT commit individual transactions — simulation is ephemeral.
            # Rollback to avoid polluting the DB with synthetic data.
            await db.rollback()

        # 3. Compute metrics
        metrics = compute_metrics(labels, predicted_fraud, scores, latencies_ms)
        wall_time = time.perf_counter() - start_wall

        # 4. Persist result
        result.status = "completed"
        result.completed_at = datetime.now(timezone.utc)
        result.metrics = metrics
        result.run_duration_s = round(wall_time, 3)

    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)[:2000]
        result.completed_at = datetime.now(timezone.utc)

    await db.commit()
