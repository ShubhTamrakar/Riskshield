from typing import Optional
from app.adapters.base import PaymentProviderAdapter
from app.adapters.synthetic import SyntheticPaymentProviderAdapter
from app.adapters.razorpay import RazorpayAdapter

_registry: dict[str, PaymentProviderAdapter] = {
    "synthetic": SyntheticPaymentProviderAdapter(),
    "razorpay": RazorpayAdapter(),
}

def get_adapter(provider: str) -> Optional[PaymentProviderAdapter]:
    """
    Retrieve the appropriate adapter for the given provider name.
    """
    return _registry.get(provider.lower())
