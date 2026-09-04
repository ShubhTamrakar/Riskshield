"""
Scenario generators.

Each function returns a list of (PaymentRequest, is_fraud: bool) tuples.
is_fraud is the ground-truth label — the engine never sees this.
"""
from __future__ import annotations
import random
import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from app.schemas.transaction import PaymentRequest
from app.schemas.customer import CustomerCreate
from app.schemas.merchant import MerchantCreate
from app.schemas.device import DeviceCreate

# ── Helpers ───────────────────────────────────────────────────────────────────

def _customer(seed_suffix: str = "") -> CustomerCreate:
    return CustomerCreate(
        external_customer_id=f"sim_cust_{uuid.uuid4().hex[:8]}_{seed_suffix}",
        account_created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        status="active"
    )

def _merchant(category: str = "retail", seed_suffix: str = "") -> MerchantCreate:
    return MerchantCreate(
        external_merchant_id=f"sim_merch_{uuid.uuid4().hex[:8]}_{seed_suffix}",
        category=category,
        status="active"
    )

def _device(fingerprint: str | None = None) -> DeviceCreate:
    return DeviceCreate(
        device_fingerprint=fingerprint or f"sim_fp_{uuid.uuid4().hex}"
    )

def _req(
    customer: CustomerCreate,
    merchant: MerchantCreate,
    amount: float,
    device: DeviceCreate | None = None,
    ip: str | None = None,
    city: str | None = None,
    country: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> PaymentRequest:
    return PaymentRequest(
        external_transaction_id=f"sim_{uuid.uuid4().hex}",
        amount=amount,
        currency="USD",
        payment_method="credit_card",
        customer=customer,
        merchant=merchant,
        device=device,
        ip_address=ip,
        city=city,
        country=country,
        latitude=lat,
        longitude=lon,
    )

Pair = Tuple[PaymentRequest, bool]

# ── Scenario implementations ──────────────────────────────────────────────────

def normal_traffic(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Baseline: typical customer behaviour with low fraud rate."""
    results = []
    merchant = _merchant("retail")
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = _customer(str(i))
        amount = rng.uniform(10, 200) if not is_fraud else rng.uniform(500, 2000)
        results.append((_req(customer, merchant, amount,
                             ip="192.168.1.1", city="New York", country="US",
                             lat=40.7128, lon=-74.0060), is_fraud))
    return results


def high_value_anomaly(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """High-value anomaly: fraudulent transactions are 10–25x the customer baseline."""
    results = []
    merchant = _merchant("luxury")
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = _customer(str(i))
        amount = rng.uniform(20, 80) if not is_fraud else rng.uniform(3000, 15000)
        results.append((_req(customer, merchant, amount,
                             ip="10.0.0.1", city="Los Angeles", country="US",
                             lat=34.0522, lon=-118.2437), is_fraud))
    return results


def velocity_attack(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Velocity attack: a small set of customers make many rapid transactions."""
    results = []
    # Use a small pool of 5 customers to produce velocity signals
    pool_size = max(3, n // 20)
    customers = [_customer(f"velocity_{i}") for i in range(pool_size)]
    merchants = [_merchant("online", f"v_{i}") for i in range(3)]
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = rng.choice(customers)
        merchant = rng.choice(merchants)
        amount = rng.uniform(5, 50)  # card-testing style amounts
        results.append((_req(customer, merchant, amount,
                             ip="203.0.113.5", city="Chicago", country="US",
                             lat=41.8781, lon=-87.6298), is_fraud))
    return results


def account_takeover(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Account takeover: new device + location change + elevated amounts."""
    results = []
    merchant = _merchant("electronics")
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = _customer(str(i))
        # Fraudulent ATO uses a fresh device fingerprint each time
        device = _device() if is_fraud else _device(f"known_{i}")
        amount = rng.uniform(800, 3000) if is_fraud else rng.uniform(30, 120)
        city = rng.choice(["Lagos", "Kiev", "Dhaka"]) if is_fraud else "Seattle"
        country = "NG" if is_fraud else "US"
        lat = rng.uniform(-90, 90) if is_fraud else 47.6062
        lon = rng.uniform(-180, 180) if is_fraud else -122.3321
        results.append((_req(customer, merchant, amount, device=device,
                             ip=f"45.{rng.randint(1,254)}.{rng.randint(1,254)}.1" if is_fraud else "10.1.1.1",
                             city=city, country=country, lat=lat, lon=lon), is_fraud))
    return results


def card_testing(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Card testing: many small transactions from same customer to verify a stolen card."""
    results = []
    pool = [_customer(f"ct_{i}") for i in range(max(2, n // 15))]
    merchant = _merchant("coffee")
    device = _device("card_test_device")
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = rng.choice(pool)
        amount = rng.uniform(0.50, 5.00) if is_fraud else rng.uniform(3, 25)
        results.append((_req(customer, merchant, amount, device=device,
                             ip="198.51.100.5", city="Phoenix", country="US",
                             lat=33.4484, lon=-112.0740), is_fraud))
    return results


def device_network(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Device network fraud: one device shared across many different customers."""
    results = []
    # Single shared device for fraudulent transactions
    shared_device = _device("shared_device_fingerprint_0xDEAD")
    merchant = _merchant("gaming")
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = _customer(str(i))  # many different customers
        device = shared_device if is_fraud else _device(f"legit_{i}")
        amount = rng.uniform(20, 150)
        results.append((_req(customer, merchant, amount, device=device,
                             ip="203.0.113.99", city="Houston", country="US",
                             lat=29.7604, lon=-95.3698), is_fraud))
    return results


def location_anomaly(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Location anomaly: transactions originating from unusual geographies."""
    results = []
    merchant = _merchant("travel")
    for i in range(n):
        is_fraud = rng.random() < fraud_pct
        customer = _customer(str(i))
        # Fraudulent = high-risk geography
        if is_fraud:
            city = rng.choice(["Accra", "Caracas", "Minsk"])
            country = rng.choice(["GH", "VE", "BY"])
            lat = rng.uniform(-20, 60)
            lon = rng.uniform(-80, 60)
        else:
            city, country, lat, lon = "Boston", "US", 42.3601, -71.0589
        amount = rng.uniform(50, 500)
        results.append((_req(customer, merchant, amount,
                             city=city, country=country, lat=lat, lon=lon,
                             ip=f"41.{rng.randint(1,254)}.1.1" if is_fraud else "172.16.0.1"), is_fraud))
    return results


def mixed_fraud(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Mixed: randomly samples from all scenarios for a realistic blend."""
    generators = [
        normal_traffic, high_value_anomaly, velocity_attack,
        account_takeover, card_testing, device_network, location_anomaly,
    ]
    results = []
    chunk = max(1, n // len(generators))
    for gen in generators:
        chunk_n = min(chunk, n - len(results))
        if chunk_n <= 0:
            break
        results.extend(gen(chunk_n, fraud_pct, rng))
    # Top up if rounding left us short
    while len(results) < n:
        results.extend(rng.choice(generators)(1, fraud_pct, rng))
    return results[:n]


# ── Registry ──────────────────────────────────────────────────────────────────

SCENARIOS = {
    "normal_traffic":     normal_traffic,
    "high_value_anomaly": high_value_anomaly,
    "velocity_attack":    velocity_attack,
    "account_takeover":   account_takeover,
    "card_testing":       card_testing,
    "device_network":     device_network,
    "location_anomaly":   location_anomaly,
    "mixed_fraud":        mixed_fraud,
}

SCENARIO_LABELS = {
    "normal_traffic":     "Normal Traffic",
    "high_value_anomaly": "High-Value Anomaly",
    "velocity_attack":    "Velocity Attack",
    "account_takeover":   "Account Takeover",
    "card_testing":       "Card Testing",
    "device_network":     "Device Network",
    "location_anomaly":   "Location Anomaly",
    "mixed_fraud":        "Mixed Fraud",
}
