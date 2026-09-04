import pytest
import hmac
import hashlib
import json
from app.adapters.razorpay import RazorpayAdapter

def test_razorpay_verify_signature():
    adapter = RazorpayAdapter()
    secret = "test_secret"
    payload = {"test": "data"}
    body = json.dumps(payload).encode()
    
    # Valid signature
    valid_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    headers = {"x-razorpay-signature": valid_sig}
    
    assert adapter.verify_signature(body, headers, secret) is True
    
    # Invalid signature
    headers = {"x-razorpay-signature": "invalid_sig"}
    assert adapter.verify_signature(body, headers, secret) is False
    
    # Missing signature
    assert adapter.verify_signature(body, {}, secret) is False

def test_razorpay_get_event_id():
    adapter = RazorpayAdapter()
    payload = {
        "event": "payment.authorized",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_12345"
                }
            }
        }
    }
    assert adapter.get_event_id(payload) == "payment.authorized_pay_12345"

def test_razorpay_normalize_payload_valid():
    adapter = RazorpayAdapter()
    payload = {
        "event": "payment.authorized",
        "account_id": "acc_123",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_12345",
                    "amount": 50000, # 500.00 INR
                    "currency": "INR",
                    "method": "card",
                    "email": "test@example.com",
                    "card": {
                        "network": "Visa"
                    }
                }
            }
        }
    }
    
    req = adapter.normalize_payload(payload)
    assert req is not None
    assert req.external_transaction_id == "pay_12345"
    assert req.amount == 500.00
    assert req.currency == "INR"
    assert req.payment_method == "card_visa"
    assert req.customer.external_customer_id == "test@example.com"
    assert req.merchant.external_merchant_id == "acc_123"

def test_razorpay_normalize_payload_ignored_event():
    adapter = RazorpayAdapter()
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_12345"
                }
            }
        }
    }
    req = adapter.normalize_payload(payload)
    assert req is None
