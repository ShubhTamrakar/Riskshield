import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.models.ground_truth import GroundTruth
from synthetic.config import FraudLabel
from synthetic.profiles import ProfileType, PROFILES, get_random_profile

class SyntheticCustomer:
    def __init__(self, random_state: random.Random):
        self.id = uuid.uuid4()
        self.profile = get_random_profile(random_state)
        self.config = PROFILES[self.profile]
        self.devices = [uuid.uuid4()]
        self.home_location = {
            "country": "US",
            "city": random_state.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
            "latitude": random_state.uniform(25.0, 48.0),
            "longitude": random_state.uniform(-125.0, -70.0)
        }
        self.ip_address = f"{random_state.randint(1,255)}.{random_state.randint(1,255)}.{random_state.randint(1,255)}.{random_state.randint(1,255)}"

class SyntheticMerchant:
    def __init__(self, random_state: random.Random, category: str):
        self.id = uuid.uuid4()
        self.category = category

class TransactionState:
    def __init__(self, customer: SyntheticCustomer, merchant: SyntheticMerchant, 
                 amount: float, timestamp: datetime, label: FraudLabel, scenario: str = None):
        self.id = uuid.uuid4()
        self.customer = customer
        self.customer_id = customer.id
        self.merchant_id = merchant.id
        self.device_id = customer.devices[0]  # simplified
        self.amount = amount
        self.currency = "USD"
        self.payment_method = "credit_card"
        self.ip_address = customer.ip_address
        self.country = customer.home_location["country"]
        self.city = customer.home_location["city"]
        self.latitude = customer.home_location["latitude"]
        self.longitude = customer.home_location["longitude"]
        self.status = "completed"
        self.timestamp = timestamp
        self.label = label
        self.scenario = scenario

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "external_transaction_id": f"txn_{self.id.hex[:8]}",
            "customer_id": self.customer_id,
            "merchant_id": self.merchant_id,
            "device_id": self.device_id,
            "amount": self.amount,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "ip_address": self.ip_address,
            "country": self.country,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "status": self.status,
            "created_at": self.timestamp
        }
