"""
evaluate_existing.py
--------------------
Runs the risk engine against every Transaction that has no RiskEvaluation,
then persists the result.  Safe to re-run; already-evaluated rows are skipped.

Usage (from inside the container):
    python scripts/evaluate_existing.py
"""
import sys, os
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models import Transaction, Customer, Merchant, Device
from app.models.risk import RiskEvaluation
from app.schemas.transaction import PaymentRequest
from app.schemas.customer import CustomerCreate
from app.schemas.merchant import MerchantCreate
from app.schemas.device import DeviceCreate
from app.engine.evaluator import evaluate_transaction

logging.basicConfig(level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

BATCH = 100


async def main():
    async with AsyncSessionLocal() as db:
        # Fetch all transactions that have no risk evaluation
        result = await db.execute(
            select(Transaction)
            .outerjoin(RiskEvaluation, Transaction.id == RiskEvaluation.transaction_id)
            .where(RiskEvaluation.id == None)
            .options(
                selectinload(Transaction.customer),
                selectinload(Transaction.merchant),
                selectinload(Transaction.device),
            )
        )
        transactions = result.scalars().all()

    logger.info(f"Found {len(transactions)} transactions without risk evaluations.")
    if not transactions:
        logger.info("Nothing to do.")
        return

    done = 0
    async with AsyncSessionLocal() as db:
        for tx in transactions:
            # Build a PaymentRequest from stored data
            cust = tx.customer
            merch = tx.merchant
            dev = tx.device

            req = PaymentRequest(
                external_transaction_id=tx.external_transaction_id,
                amount=float(tx.amount),
                currency=tx.currency,
                payment_method=tx.payment_method,
                ip_address=tx.ip_address,
                country=tx.country,
                city=tx.city,
                latitude=float(tx.latitude) if tx.latitude is not None else None,
                longitude=float(tx.longitude) if tx.longitude is not None else None,
                customer=CustomerCreate(
                    external_customer_id=cust.external_customer_id,
                    status=cust.status,
                ),
                merchant=MerchantCreate(
                    external_merchant_id=merch.external_merchant_id,
                    category=merch.category,
                    status=merch.status,
                ),
                device=DeviceCreate(
                    device_fingerprint=dev.device_fingerprint,
                    device_type=dev.device_type,
                    operating_system=dev.operating_system,
                ) if dev else None,
            )

            try:
                eval_result = await evaluate_transaction(db, req, mode="rules_only")
            except Exception as exc:
                logger.warning(f"Skipping {tx.external_transaction_id}: {exc}")
                await db.rollback()
                continue

            risk_eval = RiskEvaluation(
                id=uuid.uuid4(),
                transaction_id=tx.id,
                score=eval_result.score,
                risk_level=eval_result.risk_level,
                decision=eval_result.decision.value if hasattr(eval_result.decision, "value") else str(eval_result.decision),
                signals=[s.__dict__ if hasattr(s, "__dict__") else str(s) for s in (eval_result.signals or [])],
            )
            db.add(risk_eval)

            done += 1
            if done % BATCH == 0:
                await db.commit()
                logger.info(f"  evaluated {done}/{len(transactions)} ...")

        await db.commit()

    logger.info(f"Done. Evaluated {done} transactions.")


if __name__ == "__main__":
    asyncio.run(main())
