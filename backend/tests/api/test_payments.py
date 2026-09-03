import pytest
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_create_payment_success(client: AsyncClient):
    payload = {
        "external_transaction_id": f"txn_{uuid.uuid4()}",
        "amount": 150.50,
        "currency": "USD",
        "payment_method": "credit_card",
        "customer": {
            "external_customer_id": f"cust_{uuid.uuid4()}",
            "status": "active"
        },
        "merchant": {
            "external_merchant_id": f"merch_{uuid.uuid4()}",
            "category": "retail"
        },
        "device": {
            "device_fingerprint": f"fp_{uuid.uuid4()}",
            "device_type": "desktop"
        }
    }
    
    response = await client.post("/api/v1/payments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 150.50
    assert "id" in data
    
    # Verify GET payment
    txn_id = data["id"]
    response = await client.get(f"/api/v1/payments/{txn_id}")
    assert response.status_code == 200
    assert response.json()["id"] == txn_id

@pytest.mark.asyncio
async def test_get_payment_not_found(client: AsyncClient):
    response = await client.get(f"/api/v1/payments/{uuid.uuid4()}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_payment_validation_error(client: AsyncClient):
    payload = {
        # Missing required fields
        "amount": -10, # Invalid amount
    }
    
    response = await client.post("/api/v1/payments", json=payload)
    assert response.status_code == 422
