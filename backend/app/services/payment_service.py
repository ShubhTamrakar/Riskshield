from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Transaction, Customer, Merchant, Device
from app.models.risk import RiskEvaluation
from app.schemas.transaction import PaymentRequest
from app.engine.evaluator import evaluate_transaction
from app.security.sanitizer import sanitize_string

async def process_payment(db: AsyncSession, payload: PaymentRequest) -> Transaction:
    """
    Core business logic to process a payment request.
    1. Upserts Customer, Merchant, Device.
    2. Runs the Risk Engine.
    3. Persists the Transaction and RiskEvaluation.
    Returns the persisted Transaction model.
    """
    
    # 1. Get or create Customer
    customer = None
    if payload.customer:
        res = await db.execute(select(Customer).filter(Customer.external_customer_id == payload.customer.external_customer_id))
        customer = res.scalars().first()
        if not customer:
            customer = Customer(
                external_customer_id=sanitize_string(payload.customer.external_customer_id),
                account_created_at=payload.customer.account_created_at,
                status=sanitize_string(payload.customer.status)
            )
            db.add(customer)
            await db.flush()
            
    # 2. Get or create Merchant
    merchant = None
    if payload.merchant:
        res = await db.execute(select(Merchant).filter(Merchant.external_merchant_id == payload.merchant.external_merchant_id))
        merchant = res.scalars().first()
        if not merchant:
            merchant = Merchant(
                external_merchant_id=sanitize_string(payload.merchant.external_merchant_id),
                category=sanitize_string(payload.merchant.category),
                status=sanitize_string(payload.merchant.status)
            )
            db.add(merchant)
            await db.flush()
            
    # 3. Get or create Device
    device = None
    if payload.device:
        res = await db.execute(select(Device).filter(Device.device_fingerprint == payload.device.device_fingerprint))
        device = res.scalars().first()
        if not device:
            device = Device(
                device_fingerprint=sanitize_string(payload.device.device_fingerprint),
                device_type=sanitize_string(payload.device.device_type),
                operating_system=sanitize_string(payload.device.operating_system)
            )
            db.add(device)
            await db.flush()
            
    # 4. Evaluate Risk synchronously
    risk_result = await evaluate_transaction(db, payload)
    
    final_status = "blocked" if risk_result.decision == "BLOCK" else "completed"
    
    transaction = Transaction(
        external_transaction_id=sanitize_string(payload.external_transaction_id),
        customer_id=customer.id if customer else None,
        merchant_id=merchant.id if merchant else None,
        device_id=device.id if device else None,
        amount=payload.amount,
        currency=sanitize_string(payload.currency),
        payment_method=sanitize_string(payload.payment_method) if payload.payment_method else None,
        ip_address=sanitize_string(payload.ip_address) if payload.ip_address else None,
        country=sanitize_string(payload.country) if payload.country else None,
        city=sanitize_string(payload.city) if payload.city else None,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status=final_status
    )
    db.add(transaction)
    await db.flush()
    
    risk_eval = RiskEvaluation(
        transaction_id=transaction.id,
        score=risk_result.score,
        risk_level=risk_result.risk_level.value,
        decision=risk_result.decision.value,
        signals=[s.model_dump() for s in risk_result.signals]
    )
    db.add(risk_eval)
    
    await db.commit()
    await db.refresh(transaction)
    await db.refresh(risk_eval)
    transaction.risk_evaluation = risk_eval
    
    return transaction
