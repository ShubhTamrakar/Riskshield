import math
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.device import Device
from app.schemas.transaction import PaymentRequest

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in kilometers between two points on the earth."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class FeatureContext:
    def __init__(self, request: PaymentRequest):
        self.request = request
        self.customer_historical_tx_count: int = 0
        self.customer_historical_avg_amount: float = 0.0
        self.customer_velocity_1h: int = 0
        self.customer_velocity_24h: int = 0
        self.is_new_device: bool = True
        self.device_customer_count: int = 1
        self.ip_customer_count: int = 1
        self.distance_from_home_km: float = 0.0
        self.failed_payment_sequence: int = 0

async def extract_features(db: AsyncSession, request: PaymentRequest) -> FeatureContext:
    context = FeatureContext(request)
    
    # Needs a real customer ID if they exist. We need to look them up by external_id
    res = await db.execute(select(Customer.id).filter(Customer.external_customer_id == request.customer.external_customer_id))
    customer_id = res.scalar()
    
    if not customer_id:
        # Brand new customer, defaults are fine
        return context
        
    now = datetime.utcnow()
    
    # 1. Historical Tx Stats
    res = await db.execute(
        select(
            func.count(Transaction.id),
            func.avg(Transaction.amount)
        ).where(Transaction.customer_id == customer_id)
    )
    count, avg_amount = res.first()
    context.customer_historical_tx_count = count or 0
    context.customer_historical_avg_amount = float(avg_amount) if avg_amount else 0.0
    
    # 2. Velocity
    res = await db.execute(
        select(func.count(Transaction.id))
        .where(Transaction.customer_id == customer_id)
        .where(Transaction.created_at >= now - timedelta(hours=1))
    )
    context.customer_velocity_1h = res.scalar() or 0
    
    res = await db.execute(
        select(func.count(Transaction.id))
        .where(Transaction.customer_id == customer_id)
        .where(Transaction.created_at >= now - timedelta(hours=24))
    )
    context.customer_velocity_24h = res.scalar() or 0
    
    # 3. Failed payment sequence
    # Look at recent transactions to see if they failed
    res = await db.execute(
        select(Transaction.status)
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.created_at.desc())
        .limit(10)
    )
    statuses = res.scalars().all()
    fails = 0
    for s in statuses:
        if s == "failed":
            fails += 1
        else:
            break
    context.failed_payment_sequence = fails

    # 4. Device Stats
    # Note: payment_service creates the Device row BEFORE calling evaluate_transaction,
    # so checking Device existence would always return True for this request's device.
    # Instead we check whether this device has a prior *completed* transaction for this customer.
    if request.device and request.device.device_fingerprint:
        res = await db.execute(select(Device.id).filter(Device.device_fingerprint == request.device.device_fingerprint))
        device_id = res.scalar()
        if device_id:
            # is_new_device = True if this customer has NEVER completed a tx with this device before
            res = await db.execute(
                select(func.count(Transaction.id))
                .where(Transaction.device_id == device_id)
                .where(Transaction.customer_id == customer_id)
                .where(Transaction.status == "completed")
            )
            prior_txns = res.scalar() or 0
            context.is_new_device = prior_txns == 0

            # Check how many distinct customers used this device (for shared_device signal)
            res = await db.execute(
                select(func.count(func.distinct(Transaction.customer_id)))
                .where(Transaction.device_id == device_id)
            )
            context.device_customer_count = res.scalar() or 1

    # 5. IP Stats
    if request.ip_address:
        res = await db.execute(
            select(func.count(func.distinct(Transaction.customer_id)))
            .where(Transaction.ip_address == request.ip_address)
        )
        context.ip_customer_count = res.scalar() or 1
        
    # 6. Geolocation
    subq = (
        select(Transaction.latitude, Transaction.longitude)
        .where(Transaction.customer_id == customer_id)
        .where(Transaction.latitude != None)
        .where(Transaction.longitude != None)
        .where(Transaction.status == 'completed')
        .order_by(Transaction.created_at.desc())
        .limit(10)
        .subquery()
    )
    res = await db.execute(
        select(func.avg(subq.c.latitude), func.avg(subq.c.longitude))
    )
    home_lat, home_lon = res.first()
    
    if home_lat is not None and home_lon is not None and request.latitude is not None and request.longitude is not None:
        context.distance_from_home_km = haversine(float(home_lat), float(home_lon), request.latitude, request.longitude)
        
    return context
