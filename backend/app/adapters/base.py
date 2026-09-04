from typing import Protocol, Optional
from app.schemas.transaction import PaymentRequest

class PaymentProviderAdapter(Protocol):
    """
    Protocol defining the interface for payment provider adapters.
    Adapters are responsible for taking provider-specific webhook events
    and converting them into our unified PaymentRequest structure.
    """
    
    def verify_signature(self, body: bytes, headers: dict, secret: str) -> bool:
        """
        Verify the webhook signature for the provider.
        """
        ...
        
    def get_event_id(self, payload: dict) -> str:
        """
        Extract a unique event ID from the payload for idempotency checks.
        """
        ...
        
    def normalize_payload(self, payload: dict) -> Optional[PaymentRequest]:
        """
        Normalize the provider-specific payload into a PaymentRequest.
        Returns None if the event is not a payment authorization or should be ignored.
        """
        ...
