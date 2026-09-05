import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, delete

from synthetic.generator import SyntheticCustomer, SyntheticMerchant, TransactionState
from app.models import Customer, Merchant, Device, Transaction
from app.models.ground_truth import GroundTruth

logger = logging.getLogger(__name__)

async def bulk_write_dataset(
    session: AsyncSession, 
    customers: List[SyntheticCustomer], 
    merchants: List[SyntheticMerchant], 
    transactions: List[TransactionState],
    clear_existing: bool = True
):
    """
    Writes synthetic data to the database using bulk inserts.
    """
    if clear_existing:
        logger.info("Clearing existing data...")
        from app.models.risk import RiskEvaluation
        await session.execute(delete(RiskEvaluation))
        await session.execute(delete(GroundTruth))
        await session.execute(delete(Transaction))
        await session.execute(delete(Device))
        await session.execute(delete(Merchant))
        await session.execute(delete(Customer))
        await session.commit()
        
    logger.info("Writing merchants...")
    merchant_dicts = [
        {"id": m.id, "external_merchant_id": f"merch_{m.id.hex[:8]}", "category": m.category, "status": "active"} 
        for m in merchants
    ]
    if merchant_dicts:
        await session.execute(insert(Merchant), merchant_dicts)
        
    logger.info("Writing customers and devices...")
    customer_dicts = []
    device_dicts = []
    for c in customers:
        customer_dicts.append({
            "id": c.id, 
            "external_customer_id": f"cust_{c.id.hex[:8]}", 
            "status": "active"
        })
        for d_id in c.devices:
            device_dicts.append({
                "id": d_id,
                "device_fingerprint": f"dev_{d_id.hex}",
                "device_type": "mobile",
                "operating_system": "iOS"
            })
    
    if customer_dicts:
        await session.execute(insert(Customer), customer_dicts)
    if device_dicts:
        await session.execute(insert(Device), device_dicts)
        
    logger.info("Writing transactions...")
    batch_size = 5000
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i+batch_size]
        tx_dicts = [tx.to_dict() for tx in batch]
        
        # Insert transactions
        if tx_dicts:
            await session.execute(insert(Transaction), tx_dicts)
            
        # Insert ground truth
        gt_dicts = [
            {
                "transaction_id": tx.id,
                "label": tx.label.value,
                "fraud_scenario": tx.scenario,
                "created_at": tx.timestamp
            } for tx in batch
        ]
        if gt_dicts:
            await session.execute(insert(GroundTruth), gt_dicts)
            
        logger.info(f"Inserted {min(i+batch_size, len(transactions))} / {len(transactions)} transactions")
        
    await session.commit()
    logger.info("Dataset written successfully.")
