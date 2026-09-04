import hashlib
import hmac
import logging
import uuid
from typing import Optional
from datetime import datetime
from app.schemas.transaction import PaymentRequest
from app.schemas.customer import CustomerCreate
from app.schemas.merchant import MerchantCreate
from app.schemas.device import DeviceCreate

logger = logging.getLogger(__name__)

class RazorpayAdapter:
    """
    Adapter for Razorpay Webhooks.
    Designed around Razorpay's Test Mode APIs.
    """
    
    def verify_signature(self, body: bytes, headers: dict, secret: str) -> bool:
        """
        Razorpay sends the signature in the `x-razorpay-signature` header.
        """
        signature = headers.get("x-razorpay-signature")
        if not signature:
            return False
            
        expected_sig = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)
        
    def get_event_id(self, payload: dict) -> str:
        # Razorpay sends a top level event ID, typically not explicit in all docs but usually there's an 'id' or we can hash the created_at/account_id, or razorpay sends 'event_id'
        # Let's extract the payment ID as the unique event identifier for payment.authorized, combined with the event type
        event_type = payload.get("event", "unknown")
        payment_data = payload.get("payload", {}).get("payment", {}).get("entity", {})
        payment_id = payment_data.get("id", str(uuid.uuid4()))
        return f"{event_type}_{payment_id}"
        
    def normalize_payload(self, payload: dict) -> Optional[PaymentRequest]:
        """
        Only process 'payment.authorized' events.
        """
        event = payload.get("event")
        if event != "payment.authorized":
            logger.info("RazorpayAdapter ignoring event type: %s", event)
            return None
            
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        if not payment:
            return None
            
        # Amount in Razorpay is typically in smallest units (e.g., paise). Divide by 100.
        amount = payment.get("amount", 0) / 100.0
        currency = payment.get("currency", "INR")
        
        email = payment.get("email") or "unknown@razorpay.com"
        
        customer = CustomerCreate(
            external_customer_id=email, # Often email or contact is the best unique identifier if no customer_id
            account_created_at=datetime.now(), # Approximation since not provided
            status="active"
        )
        
        merchant = MerchantCreate(
            external_merchant_id=payload.get("account_id", "razorpay_merchant"),
            category="razorpay_default",
            status="active"
        )
        
        card_data = payment.get("card", {})
        payment_method = payment.get("method") or "card"
        if card_data:
            payment_method = f"card_{card_data.get('network', 'unknown')}".lower()
            
        return PaymentRequest(
            external_transaction_id=payment.get("id", str(uuid.uuid4())),
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            ip_address=None,
            country=None,
            city=None,
            latitude=None,
            longitude=None,
            customer=customer,
            merchant=merchant,
            device=None # Not natively present in standard Razorpay webhook
        )
