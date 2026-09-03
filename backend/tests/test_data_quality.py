import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import datetime

from app.models.transaction import Transaction
from app.models.ground_truth import GroundTruth
from app.models.customer import Customer
from app.models.merchant import Merchant
from app.models.device import Device

@pytest.mark.asyncio
async def test_no_missing_values(db: AsyncSession):
    # Check for null amounts or timestamps
    result = await db.execute(select(func.count(Transaction.id)).where(Transaction.amount == None))
    assert result.scalar() == 0

    result = await db.execute(select(func.count(Transaction.id)).where(Transaction.created_at == None))
    assert result.scalar() == 0

@pytest.mark.asyncio
async def test_valid_amounts(db: AsyncSession):
    # Amounts should be > 0
    result = await db.execute(select(func.count(Transaction.id)).where(Transaction.amount <= 0))
    assert result.scalar() == 0

@pytest.mark.asyncio
async def test_ground_truth_isolation(db: AsyncSession):
    # The transaction model should NOT have a label column directly
    assert not hasattr(Transaction, "label")
    assert not hasattr(Transaction, "fraud_scenario")

    # Ground truth records should equal transaction records
    tx_count = await db.execute(select(func.count(Transaction.id)))
    gt_count = await db.execute(select(func.count(GroundTruth.id)))
    
    assert tx_count.scalar() == gt_count.scalar()
    
@pytest.mark.asyncio
async def test_chronological_order(db: AsyncSession):
    # Pick a random customer and verify their transactions are chronological (or at least valid dates)
    result = await db.execute(select(Customer.id).limit(1))
    customer_id = result.scalar()
    
    if customer_id:
        txs_result = await db.execute(
            select(Transaction).where(Transaction.customer_id == customer_id).order_by(Transaction.created_at)
        )
        txs = txs_result.scalars().all()
        
        for i in range(1, len(txs)):
            assert txs[i].created_at >= txs[i-1].created_at
