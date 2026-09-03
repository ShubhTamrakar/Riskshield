from fastapi import APIRouter

from app.api.endpoints import payments, customers, merchants, risk

api_router = APIRouter()
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(merchants.router, prefix="/merchants", tags=["merchants"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
