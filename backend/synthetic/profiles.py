import random
from enum import Enum
from pydantic import BaseModel

class ProfileType(str, Enum):
    LOW_FREQUENCY = "LOW_FREQUENCY"
    HIGH_FREQUENCY = "HIGH_FREQUENCY"
    HIGH_VALUE = "HIGH_VALUE"
    REGULAR = "REGULAR"
    NEW_CUSTOMER = "NEW_CUSTOMER"

class ProfileConfig(BaseModel):
    tx_per_month_mean: float
    tx_per_month_std: float
    avg_tx_value: float
    tx_value_std: float
    prob_new_device: float
    prob_travel: float
    favorite_merchant_categories: list[str]

PROFILES = {
    ProfileType.LOW_FREQUENCY: ProfileConfig(
        tx_per_month_mean=2.0,
        tx_per_month_std=1.0,
        avg_tx_value=50.0,
        tx_value_std=20.0,
        prob_new_device=0.01,
        prob_travel=0.05,
        favorite_merchant_categories=["retail", "groceries"],
    ),
    ProfileType.HIGH_FREQUENCY: ProfileConfig(
        tx_per_month_mean=30.0,
        tx_per_month_std=10.0,
        avg_tx_value=25.0,
        tx_value_std=15.0,
        prob_new_device=0.05,
        prob_travel=0.2,
        favorite_merchant_categories=["food", "transportation", "entertainment"],
    ),
    ProfileType.HIGH_VALUE: ProfileConfig(
        tx_per_month_mean=5.0,
        tx_per_month_std=3.0,
        avg_tx_value=800.0,
        tx_value_std=400.0,
        prob_new_device=0.02,
        prob_travel=0.3,
        favorite_merchant_categories=["electronics", "travel", "luxury"],
    ),
    ProfileType.REGULAR: ProfileConfig(
        tx_per_month_mean=10.0,
        tx_per_month_std=4.0,
        avg_tx_value=100.0,
        tx_value_std=50.0,
        prob_new_device=0.03,
        prob_travel=0.1,
        favorite_merchant_categories=["retail", "groceries", "food", "services"],
    ),
    ProfileType.NEW_CUSTOMER: ProfileConfig(
        tx_per_month_mean=3.0,
        tx_per_month_std=2.0,
        avg_tx_value=60.0,
        tx_value_std=30.0,
        prob_new_device=1.0,  # Always new device initially
        prob_travel=0.0,
        favorite_merchant_categories=["retail"],
    ),
}

def get_random_profile(random_state: random.Random) -> ProfileType:
    choices = [
        (ProfileType.REGULAR, 0.5),
        (ProfileType.LOW_FREQUENCY, 0.2),
        (ProfileType.HIGH_FREQUENCY, 0.15),
        (ProfileType.HIGH_VALUE, 0.05),
        (ProfileType.NEW_CUSTOMER, 0.1),
    ]
    types, weights = zip(*choices)
    return random_state.choices(types, weights=weights, k=1)[0]
