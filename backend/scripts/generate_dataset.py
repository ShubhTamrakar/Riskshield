import sys
import os

# Make `app` importable regardless of working directory.
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import asyncio
import argparse
import logging

from app.db.session import AsyncSessionLocal
from synthetic.config import DATASET_PRESETS, DatasetConfig
from synthetic.pipeline import build_dataset
from synthetic.writer import bulk_write_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

async def generate(size: str, seed: int):
    if size not in DATASET_PRESETS:
        logger.error(f"Invalid size '{size}'. Available: {list(DATASET_PRESETS.keys())}")
        return
        
    config = DATASET_PRESETS[size]
    # Override seed if provided via CLI
    if seed is not None:
        config.seed = seed
        
    logger.info(f"Generating dataset '{config.name}' (seed={config.seed})")
    logger.info(f"Target: {config.num_customers} customers, {config.num_merchants} merchants, {config.target_transactions} transactions")
    
    customers, merchants, transactions = build_dataset(config)
    
    logger.info(f"Generated {len(customers)} customers, {len(merchants)} merchants, {len(transactions)} transactions.")
    
    async with AsyncSessionLocal() as session:
        await bulk_write_dataset(session, customers, merchants, transactions)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic RiskShield dataset.")
    parser.add_argument("--size", type=str, default="dev", choices=list(DATASET_PRESETS.keys()), help="Dataset size preset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    
    args = parser.parse_args()
    
    asyncio.run(generate(args.size, args.seed))
