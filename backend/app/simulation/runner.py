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
from sqlalchemy import select

from app.engine.evaluator import evaluate_transaction, EngineMode
from app.engine.types import Decision
from app.models.simulation import SimulationRun
from app.models import Transaction, Customer, Merchant, Device
from app.security.sanitizer import sanitize_string
from app.simulation.scenarios import SCENARIOS
from app.simulation.metrics import compute_metrics
from app.db.session import AsyncSessionLocal


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

            # 1. Upsert entities to DB (with flush, not commit) so the engine can query history
            res = await db.execute(select(Customer).filter(Customer.external_customer_id == req.customer.external_customer_id))
            customer = res.scalars().first()
            if not customer:
                customer = Customer(
                    external_customer_id=sanitize_string(req.customer.external_customer_id),
                    account_created_at=req.customer.account_created_at,
                    status=sanitize_string(req.customer.status)
                )
                db.add(customer)

            res = await db.execute(select(Merchant).filter(Merchant.external_merchant_id == req.merchant.external_merchant_id))
            merchant = res.scalars().first()
            if not merchant:
                merchant = Merchant(
                    external_merchant_id=sanitize_string(req.merchant.external_merchant_id),
                    category=sanitize_string(req.merchant.category),
                    status=sanitize_string(req.merchant.status)
                )
                db.add(merchant)

            device = None
            if req.device:
                res = await db.execute(select(Device).filter(Device.device_fingerprint == req.device.device_fingerprint))
                device = res.scalars().first()
                if not device:
                    device = Device(
                        device_fingerprint=sanitize_string(req.device.device_fingerprint),
                        device_type=sanitize_string(req.device.device_type) if req.device.device_type else "unknown",
                        operating_system=sanitize_string(req.device.operating_system) if req.device.operating_system else "unknown"
                    )
                    db.add(device)

            await db.flush()

            # 2. Evaluate with the context now visible in the current transaction
            evaluation = await evaluate_transaction(db, req, mode=mode)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # 3. Create the transaction so subsequent loops can query it (velocity, avg amount, etc)
            transaction = Transaction(
                external_transaction_id=sanitize_string(req.external_transaction_id),
                customer_id=customer.id,
                merchant_id=merchant.id,
                device_id=device.id if device else None,
                amount=req.amount,
                currency=sanitize_string(req.currency),
                payment_method=sanitize_string(req.payment_method) if req.payment_method else None,
                ip_address=sanitize_string(req.ip_address) if req.ip_address else None,
                country=sanitize_string(req.country) if req.country else None,
                city=sanitize_string(req.city) if req.city else None,
                latitude=req.latitude,
                longitude=req.longitude,
                status="completed" if evaluation.decision != Decision.BLOCK else "blocked",
                created_at=datetime.utcnow() # Ensure timestamp is current for velocity checks
            )
            db.add(transaction)
            await db.flush()

            # BLOCK or REVIEW = engine predicts fraud
            engine_says_fraud = evaluation.decision in (Decision.BLOCK, Decision.REVIEW)

            labels.append(is_fraud)
            predicted_fraud.append(engine_says_fraud)
            scores.append(evaluation.score)
            latencies_ms.append(elapsed_ms)
            
            # Periodically write progress out of band so we don't commit synthetic txns
            i = len(labels)
            if i % 10 == 0 or i == len(pairs):
                elapsed = time.perf_counter() - start_wall
                eta_s = (elapsed / i) * (len(pairs) - i)
                async with AsyncSessionLocal() as prog_db:
                    prog_run = await prog_db.get(SimulationRun, run_id)
                    if prog_run:
                        prog_run.metrics = {
                            "progress": {
                                "completed": i,
                                "total": len(pairs),
                                "estimated_time_remaining_s": eta_s
                            }
                        }
                        await prog_db.commit()

        # 4. Rollback ALL synthetic data created during the loop
        await db.rollback()

        # Re-fetch the result because the session was rolled back
        result = await db.get(SimulationRun, run_id)

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
