import sys
import os

# Make `app` importable regardless of working directory.
# seed.py lives at backend/scripts/seed.py → backend/ is one level up.
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import asyncio
import datetime

from app.db.session import AsyncSessionLocal
from app.models import Customer, Merchant, Device
from sqlalchemy.future import select

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(Customer))
        if result.scalars().first():
            print("Database already seeded")
            return

        # Seed Customers
        c1 = Customer(external_customer_id="cust_001", status="active", account_created_at=datetime.datetime.utcnow())
        c2 = Customer(external_customer_id="cust_002", status="active")
        
        # Seed Merchants
        m1 = Merchant(external_merchant_id="merch_001", category="electronics", status="active")
        
        # Seed Devices
        d1 = Device(device_fingerprint="fp_abcd123", device_type="mobile", operating_system="ios")
        
        session.add_all([c1, c2, m1, d1])
        await session.commit()
        print("Successfully seeded data")

if __name__ == "__main__":
    asyncio.run(seed_data())
