from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc, or_
from sqlalchemy.orm import selectinload
from typing import Any, List, Optional
import uuid

from app.api import deps
from app.models import Transaction, Customer, Merchant, Device
from app.models.risk import RiskEvaluation
from app.schemas import PaymentRequest, TransactionResponse
from pydantic import BaseModel
from app.security.auth import get_current_user, require_analyst, CurrentUser
from app.security.rate_limit import limiter
from app.security.sanitizer import guard_prompt_injection, sanitize_string
from app.security.idempotency import check_idempotency, cache_idempotency_response
from app.observability.metrics import llm_request_duration_seconds, llm_failures_total
import time

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
@limiter.limit("120/minute")
async def list_payments(
    request: Request,
    page: int  = Query(1, ge=1),
    size: int  = Query(20, ge=1, le=200),
    search: Optional[str]  = Query(None),
    risk_level: Optional[str]  = Query(None),
    decision: Optional[str]   = Query(None),
    sort: Optional[str]   = Query("created_at"),
    order: Optional[str]  = Query("desc"),
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(get_current_user)
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
        search_safe = sanitize_string(search, max_length=100)
        q = q.filter(Transaction.external_transaction_id.ilike(f"%{search_safe}%"))

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    sort_col = getattr(Transaction, sort, Transaction.created_at)
    q = q.order_by(desc(sort_col) if order == "desc" else asc(sort_col))

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
@limiter.limit("300/minute")
async def get_summary(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(get_current_user)
) -> Any:
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
@limiter.limit("30/minute")
async def create_payment(
    request: Request,
    payload: PaymentRequest,
    db: AsyncSession = Depends(deps.get_db),
    cached_response: Optional[dict] = Depends(check_idempotency),
    user: CurrentUser = Depends(get_current_user)
) -> Any:
    if cached_response:
        return cached_response

    from app.services.payment_service import process_payment
    transaction = await process_payment(db, payload)
    
    response_model = TransactionResponse.model_validate(transaction)
    
    idempotency_key = getattr(request.state, "idempotency_key", None)
    if idempotency_key:
        await cache_idempotency_response(idempotency_key, response_model.model_dump(mode='json'))
    
    return transaction

@router.get("/{transaction_id}", response_model=TransactionResponse)
@limiter.limit("120/minute")
async def get_payment(
    request: Request,
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(get_current_user)
) -> Any:
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.risk_evaluation))
        .filter(Transaction.id == transaction_id)
    )
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Transaction not found"})
    return transaction

@router.get("/{transaction_id}/investigate")
@limiter.limit("10/minute")
async def investigate_payment(
    request: Request,
    transaction_id: str,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(require_analyst)
) -> Any:
    from app.ai.investigator import investigate_transaction
    
    try:
        uuid_obj = uuid.UUID(transaction_id)
        filter_expr = or_(Transaction.id == uuid_obj, Transaction.external_transaction_id == transaction_id)
    except ValueError:
        filter_expr = Transaction.external_transaction_id == transaction_id
        
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.risk_evaluation))
        .filter(filter_expr)
    )
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Transaction not found"})
        
    # Guard against prompt injection in free text fields (e.g. city) before feeding to LLM
    if transaction.city:
        transaction.city = guard_prompt_injection(transaction.city)
    
    start = time.perf_counter()
    try:
        report = await investigate_transaction(transaction, transaction.risk_evaluation)
        llm_request_duration_seconds.labels(method="GET", path="/investigate").observe(time.perf_counter() - start)
        return report
    except Exception as e:
        llm_failures_total.inc()
        raise e


# ── Admin: Clear database ─────────────────────────────────────────────────────

@router.delete("/admin/reset-data")
@limiter.limit("5/minute")
async def reset_data(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    user: CurrentUser = Depends(require_analyst)
) -> Any:
    """Clear live transactional data while preserving the ML training dataset."""
    from sqlalchemy import text as sql_text
    
    # Delete risk evaluations and webhooks for non-training transactions
    await db.execute(sql_text("""
        DELETE FROM risk_evaluations 
        WHERE transaction_id IN (
            SELECT id FROM transactions 
            WHERE id NOT IN (SELECT transaction_id FROM ground_truth)
        )
    """))
    
    await db.execute(sql_text("""
        DELETE FROM webhook_events 
        WHERE transaction_id IN (
            SELECT id FROM transactions 
            WHERE id NOT IN (SELECT transaction_id FROM ground_truth)
        )
    """))
    
    # Delete the non-training transactions themselves
    await db.execute(sql_text("""
        DELETE FROM transactions 
        WHERE id NOT IN (SELECT transaction_id FROM ground_truth)
    """))
    
    # Clear simulation history (these are safe to drop entirely)
    await db.execute(sql_text('TRUNCATE TABLE simulation_runs RESTART IDENTITY CASCADE'))
    
    await db.commit()
    return {"status": "ok", "message": "Live transactions cleared. ML training dataset preserved."}

