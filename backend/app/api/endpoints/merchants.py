from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any
import uuid

from app.api import deps
from app.models import Merchant
from app.schemas import MerchantResponse

router = APIRouter()

@router.get("/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    result = await db.execute(select(Merchant).filter(Merchant.id == merchant_id))
    merchant = result.scalars().first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant
