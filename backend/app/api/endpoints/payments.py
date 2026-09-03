from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import selectinload
from typing import Any, List, Optional
import uuid

from app.api import deps
from app.models import Transaction, Customer, Merchant, Device
from app.models.risk import RiskEvaluation
from app.schemas import PaymentRequest, TransactionResponse
from pydantic import BaseModel

router = APIRouter()

# ── List / paginated endpoint ─────────────────────────────────────────────────

class PagedTransactions(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = {"from_attributes": True}


@router.get("", response_model=PagedTransactions)
async def list_payments(
    page: int  = Query(1, ge=1),
    size: int  = Query(20, ge=1, le=200),
    search: Optional[str]  = Query(None),
    risk_level: Optional[str]  = Query(None),
    decision: Optional[str]   = Query(None),
    sort: Optional[str]   = Query("created_at"),
    order: Optional[str]  = Query("desc"),
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    q = (
        select(Transaction)
        .options(selectinload(Transaction.risk_evaluation))
    )

    if risk_level:
        q = q.join(RiskEvaluation, Transaction.id == RiskEvaluation.transaction_id)\
             .filter(RiskEvaluation.risk_level == risk_level)
    if decision:
        if risk_level:
            q = q.filter(RiskEvaluation.decision == decision)
        else:
            q = q.join(RiskEvaluation, Transaction.id == RiskEvaluation.transaction_id)\
                 .filter(RiskEvaluation.decision == decision)
    if search:
        q = q.filter(Transaction.external_transaction_id.ilike(f"%{search}%"))

    # Count total
    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Sort
    sort_col = getattr(Transaction, sort, Transaction.created_at)
    q = q.order_by(desc(sort_col) if order == "desc" else asc(sort_col))

    # Paginate
    q = q.offset((page - 1) * size).limit(size)
    result = await db.execute(q)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, (total + size - 1) // size)
    }


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(deps.get_db)) -> Any:
    result = await db.execute(
        select(Transaction).options(selectinload(Transaction.risk_evaluation))
    )
    txs = result.scalars().all()
    dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    high_risk = blocked = review = 0
    for tx in txs:
        re = tx.risk_evaluation
        if re:
            lvl = re.risk_level
            if lvl in dist: dist[lvl] += 1
            if lvl in ("HIGH", "CRITICAL"): high_risk += 1
            if re.decision == "BLOCK":  blocked += 1
            if re.decision == "REVIEW": review  += 1
    return {
        "total_transactions": len(txs),
        "high_risk":  high_risk,
        "blocked":    blocked,
        "review":     review,
        "risk_distribution": dist
    }

@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    request: PaymentRequest,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    # 1. Get or create Customer
    customer = None
    if request.customer:
        res = await db.execute(select(Customer).filter(Customer.external_customer_id == request.customer.external_customer_id))
        customer = res.scalars().first()
        if not customer:
            customer = Customer(
                external_customer_id=request.customer.external_customer_id,
                account_created_at=request.customer.account_created_at,
                status=request.customer.status
            )
            db.add(customer)
            await db.flush()
            
    # 2. Get or create Merchant
    merchant = None
    if request.merchant:
        res = await db.execute(select(Merchant).filter(Merchant.external_merchant_id == request.merchant.external_merchant_id))
        merchant = res.scalars().first()
        if not merchant:
            merchant = Merchant(
                external_merchant_id=request.merchant.external_merchant_id,
                category=request.merchant.category,
                status=request.merchant.status
            )
            db.add(merchant)
            await db.flush()
            
    # 3. Get or create Device
    device = None
    if request.device:
        res = await db.execute(select(Device).filter(Device.device_fingerprint == request.device.device_fingerprint))
        device = res.scalars().first()
        if not device:
            device = Device(
                device_fingerprint=request.device.device_fingerprint,
                device_type=request.device.device_type,
                operating_system=request.device.operating_system
            )
            db.add(device)
            await db.flush()
            
    # 4. Evaluate Risk synchronously
    from app.engine.evaluator import evaluate_transaction
    from app.models.risk import RiskEvaluation
    
    risk_result = await evaluate_transaction(db, request)
    
    # 5. Create Transaction
    # If decision is BLOCK, we might mark status as failed/blocked
    final_status = "blocked" if risk_result.decision == "BLOCK" else "completed"
    
    transaction = Transaction(
        external_transaction_id=request.external_transaction_id,
        customer_id=customer.id if customer else None,
        merchant_id=merchant.id if merchant else None,
        device_id=device.id if device else None,
        amount=request.amount,
        currency=request.currency,
        payment_method=request.payment_method,
        ip_address=request.ip_address,
        country=request.country,
        city=request.city,
        latitude=request.latitude,
        longitude=request.longitude,
        status=final_status
    )
    db.add(transaction)
    await db.flush()  # To get transaction.id
    
    # 6. Save Risk Evaluation
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
    
    # Need to load the relationship so it appears in the response
    # We can just assign it to the Pydantic schema manually or let ORM handle it if we used joinedload
    # Given we just created it, it's safer to attach it for the response model
    await db.refresh(risk_eval)
    transaction.risk_evaluation = risk_eval
    
    return transaction

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_payment(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.risk_evaluation))
        .filter(Transaction.id == transaction_id)
    )
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.get("/{transaction_id}/investigate")
async def investigate_payment(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    from sqlalchemy.orm import selectinload
    from app.ai.investigator import investigate_transaction
    
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.risk_evaluation))
        .filter(Transaction.id == transaction_id)
    )
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    report = await investigate_transaction(transaction, transaction.risk_evaluation)
    return report
