import uuid
from typing import Optional
from app.schemas.transaction import PaymentRequest

class SyntheticPaymentProviderAdapter:
    """
    Adapter for the internal Synthetic simulator.
    Since the simulator already generates payloads in the exact
    PaymentRequest format, this adapter just validates and passes it through.
    """
    
    def verify_signature(self, body: bytes, headers: dict, secret: str) -> bool:
        # Synthetic provider has no external signature since it is internal/simulated.
        # It relies on the generic API Key authentication.
        return True
        
    def get_event_id(self, payload: dict) -> str:
        # The synthetic provider usually provides an external_transaction_id.
        return payload.get("external_transaction_id") or str(uuid.uuid4())
        
    def normalize_payload(self, payload: dict) -> Optional[PaymentRequest]:
        try:
            return PaymentRequest(**payload)
        except Exception:
            return None
