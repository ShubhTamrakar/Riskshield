from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any
import uuid

from app.api import deps
from app.models import Customer
from app.schemas import CustomerResponse, PaginatedResponse

router = APIRouter()

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    result = await db.execute(select(Customer).filter(Customer.id == customer_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
