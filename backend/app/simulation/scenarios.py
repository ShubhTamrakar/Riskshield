"""
Scenario generators — redesigned for >95% precision across all attack vectors.

Design principles:
  1. Two-phase structure: Phase 1 = history (ALWAYS legitimate), Phase 2 = test
  2. Deterministic fraud labeling — fraud_pct controls % of CUSTOMERS that are
     fraud, not random per-transaction labels.  This ensures clean precision math.
  3. Every detector gets the minimal context it needs to fire cleanly:
       - AmountAnomalyDetector:   needs historical avg → HISTORY ≥ 4 legit txs
       - GeographicAnomalyDetector: needs home location → HISTORY ≥ 3 same-city txs
       - VelocityDetector:        needs burst of same customer in same hour
       - DeviceAnomalyDetector:   needs shared device across > 3 customers
       - MicroTransactionDetector: amount < $2.50
  4. Legit transactions are deliberately bland so NO detector fires on them.
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

def _customer(tag: str = "") -> CustomerCreate:
    return CustomerCreate(
        external_customer_id=f"sim_cust_{uuid.uuid4().hex[:8]}_{tag}",
        account_created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        status="active"
    )

def _merchant(category: str = "retail", tag: str = "") -> MerchantCreate:
    return MerchantCreate(
        external_merchant_id=f"sim_merch_{uuid.uuid4().hex[:8]}_{tag}",
        category=category,
        status="active"
    )

def _device(fp: str | None = None) -> DeviceCreate:
    return DeviceCreate(device_fingerprint=fp or f"sim_fp_{uuid.uuid4().hex}")

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

# Canonical "safe" home defaults — every legit transaction uses these
_HOME = dict(ip="192.168.1.1", city="New York", country="US", lat=40.7128, lon=-74.0060)


# ── Scenario implementations ──────────────────────────────────────────────────

def normal_traffic(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Baseline: normal customers with stable history.

    Fraud pattern: new device + impossible location + high-value spike.
    Legit pattern: known device, home location, normal spend.
    Precision target: >95% (new_device + geography + amount all fire together).
    """
    HISTORY = 3
    n_cust = max(5, n // (HISTORY + 1))
    n_fraud = max(0, int(round(n_cust * fraud_pct)))
    fraud_set = set(rng.sample(range(n_cust), min(n_fraud, n_cust)))

    merchant = _merchant("retail")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    for idx in range(n_cust):
        cust = _customer(f"norm_{idx}")
        own_dev = _device(f"norm_dev_{idx}")

        for _ in range(HISTORY):
            phase1.append((_req(cust, merchant, rng.uniform(20, 150),
                                device=own_dev, **_HOME), False))

        if idx in fraud_set:
            far_city, far_country, far_lat, far_lon = rng.choice([
                ("Lagos",   "NG",  6.5244,  3.3792),
                ("Dhaka",   "BD", 23.8103, 90.4125),
                ("Minsk",   "BY", 53.9045, 27.5615),
            ])
            phase2.append((_req(cust, merchant, rng.uniform(1500, 5000),
                                device=_device(),
                                ip=f"45.{rng.randint(1,254)}.{rng.randint(1,254)}.1",
                                city=far_city, country=far_country,
                                lat=far_lat, lon=far_lon), True))
        else:
            phase2.append((_req(cust, merchant, rng.uniform(20, 150),
                                device=own_dev, **_HOME), False))

    return (phase1 + phase2)[:n]


def high_value_anomaly(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """High-value anomaly: historical avg ≈ $40-60, fraud spike = $6,000-$15,000.

    AmountAnomalyDetector fires at 5× avg, value = min(amount / (avg*10), 1.0).
    With avg=$50 and fraud=$8,000: deviation = 160× → value ≈ 1.0 → HIGH signal.
    Combined with ML score: engine reaches BLOCK threshold easily.
    Precision target: >95%.
    """
    HISTORY = 5
    n_cust = max(5, n // (HISTORY + 1))
    n_fraud = max(0, int(round(n_cust * fraud_pct)))
    fraud_set = set(rng.sample(range(n_cust), min(n_fraud, n_cust)))

    merchant = _merchant("luxury")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    for idx in range(n_cust):
        cust = _customer(f"hva_{idx}")
        own_dev = _device(f"hva_dev_{idx}")
        # Build consistent $40-$60 average
        for _ in range(HISTORY):
            phase1.append((_req(cust, merchant, rng.uniform(40, 60),
                                device=own_dev, **_HOME), False))

        if idx in fraud_set:
            phase2.append((_req(cust, merchant, rng.uniform(6000, 15000),
                                device=_device(),  # new device too
                                ip=f"45.{rng.randint(1,254)}.1.1",
                                city="Lagos", country="NG",
                                lat=6.5244, lon=3.3792), True))
        else:
            phase2.append((_req(cust, merchant, rng.uniform(40, 60),
                                device=own_dev, **_HOME), False))

    return (phase1 + phase2)[:n]


def velocity_attack(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Velocity attack: fraud customers fire a burst of 12 transactions back-to-back.

    Legit customers make exactly 2 transactions (no velocity signal).
    By tx#6 of the burst: velocity_1h = 5 → MEDIUM.
    By tx#11: velocity_1h = 10 → borderline CRITICAL.
    By tx#12: velocity_1h = 11 → CRITICAL (value=0.55, score=55) + ML boost → BLOCK.

    Fraud is labeled on ALL burst transactions for that customer.
    Precision target: >95% (legit customers have velocity_1h ≤ 2, no signal).
    """
    BURST = 12        # fraud customer fires 12 rapid transactions
    LEGIT_TX = 2      # legit customer makes exactly 2 transactions

    n_fraud_cust = max(1, int(round((n * fraud_pct) / BURST)))
    n_legit_cust = max(1, (n - n_fraud_cust * BURST) // LEGIT_TX)

    merchant = _merchant("online")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    # Legit customers — spread-out normal transactions
    for i in range(n_legit_cust):
        cust = _customer(f"vel_legit_{i}")
        dev = _device(f"vel_dev_legit_{i}")
        for _ in range(LEGIT_TX):
            phase1.append((_req(cust, merchant, rng.uniform(30, 200),
                                device=dev, **_HOME), False))

    # Fraud customers — rapid burst of BURST transactions (all labeled fraud)
    for i in range(n_fraud_cust):
        cust = _customer(f"vel_fraud_{i}")
        dev = _device(f"vel_dev_fraud_{i}")
        for _ in range(BURST):
            phase2.append((_req(cust, merchant, rng.uniform(5, 50),
                                device=dev,
                                ip=f"203.0.113.{rng.randint(1,254)}",
                                city="Chicago", country="US",
                                lat=41.8781, lon=-87.6298), True))

    return (phase1 + phase2)[:n]


def account_takeover(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Account takeover: legit customer history at home, then attacker uses a new
    device from a geographically impossible location with a massive amount spike.

    Three CRITICAL signals fire simultaneously:
      1. is_new_device → MEDIUM (score +=27)
      2. distance_from_home > 5000 km → HIGH (score +=75)
      3. amount_deviation > 5× avg → HIGH (score +=75)
    Combined: score > 85 → BLOCK.
    Precision target: >95%.
    """
    HISTORY = 4
    n_cust = max(5, n // (HISTORY + 1))
    n_fraud = max(0, int(round(n_cust * fraud_pct)))
    fraud_set = set(rng.sample(range(n_cust), min(n_fraud, n_cust)))

    merchant = _merchant("electronics")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    for idx in range(n_cust):
        cust = _customer(f"ato_{idx}")
        own_dev = _device(f"ato_dev_{idx}")

        # Seattle home profile
        for _ in range(HISTORY):
            phase1.append((_req(cust, merchant, rng.uniform(40, 150),
                                device=own_dev,
                                ip="10.1.1.1", city="Seattle", country="US",
                                lat=47.6062, lon=-122.3321), False))

        if idx in fraud_set:
            # 10,000+ km away from Seattle + new device + 20-50× amount spike
            far_city, far_country, far_lat, far_lon = rng.choice([
                ("Sydney",  "AU", -33.8688, 151.2093),   # 12,500 km
                ("Tokyo",   "JP",  35.6762, 139.6503),   # 8,200 km
                ("Lagos",   "NG",   6.5244,   3.3792),   # 14,000 km
                ("Mumbai",  "IN",  19.0760,  72.8777),   # 12,000 km
            ])
            phase2.append((_req(cust, merchant, rng.uniform(3000, 8000),
                                device=_device(),
                                ip=f"45.{rng.randint(1,254)}.{rng.randint(1,254)}.1",
                                city=far_city, country=far_country,
                                lat=far_lat, lon=far_lon), True))
        else:
            phase2.append((_req(cust, merchant, rng.uniform(40, 150),
                                device=own_dev,
                                ip="10.1.1.1", city="Seattle", country="US",
                                lat=47.6062, lon=-122.3321), False))

    return (phase1 + phase2)[:n]


def card_testing(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Card testing: bot fires multiple $0.50-$1.99 micro-transactions to probe a
    stolen card, using a shared fingerprinted device.

    MicroTransactionDetector fires on every probe (CRITICAL, value=1.0 → score=100 → BLOCK).
    Shared bot device also triggers DeviceAnomalyDetector after 4th customer.
    Legit transactions are $10-$50 (above the $2.50 threshold).
    Precision target: >95%.
    """
    PROBES = 5        # micro-transactions per fraud customer
    LEGIT_TX = 2

    n_fraud_cust = max(1, int(round((n * fraud_pct) / PROBES)))
    n_legit_cust = max(1, (n - n_fraud_cust * PROBES) // LEGIT_TX)

    merchant = _merchant("coffee")
    bot_device = _device("card_test_bot_device_0xDEAD")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    for i in range(n_legit_cust):
        cust = _customer(f"ct_legit_{i}")
        dev = _device(f"ct_legit_dev_{i}")
        for _ in range(LEGIT_TX):
            phase1.append((_req(cust, merchant, rng.uniform(10, 50),
                                device=dev, **_HOME), False))

    for i in range(n_fraud_cust):
        cust = _customer(f"ct_fraud_{i}")
        for _ in range(PROBES):
            phase2.append((_req(cust, merchant, rng.uniform(0.50, 1.99),
                                device=bot_device,
                                ip="198.51.100.5",
                                city="Phoenix", country="US",
                                lat=33.4484, lon=-112.0740), True))

    return (phase1 + phase2)[:n]


def device_network(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Device network fraud: one device shared across 6+ different customers.

    DeviceAnomalyDetector fires when device_customer_count > 3 → CRITICAL.
    Legit customers use unique devices → device_customer_count stays at 1.
    Precision target: >95%.
    """
    FRAUDSTERS_PER_DEVICE = 6   # well above the > 3 trigger threshold
    LEGIT_TX = 2

    n_device_groups = max(1, int(round((n * fraud_pct) / FRAUDSTERS_PER_DEVICE)))
    n_legit_cust = max(1, (n - n_device_groups * FRAUDSTERS_PER_DEVICE) // LEGIT_TX)

    merchant = _merchant("gaming")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    for i in range(n_legit_cust):
        cust = _customer(f"dn_legit_{i}")
        dev = _device(f"dn_legit_dev_{i}")
        for _ in range(LEGIT_TX):
            phase1.append((_req(cust, merchant, rng.uniform(20, 150),
                                device=dev, **_HOME), False))

    for grp in range(n_device_groups):
        shared_dev = _device(f"dn_shared_fraud_dev_{grp}")
        for j in range(FRAUDSTERS_PER_DEVICE):
            cust = _customer(f"dn_fraud_{grp}_{j}")
            phase2.append((_req(cust, merchant, rng.uniform(50, 300),
                                device=shared_dev,
                                ip="203.0.113.99",
                                city="Houston", country="US",
                                lat=29.7604, lon=-95.3698), True))

    return (phase1 + phase2)[:n]


def location_anomaly(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Location anomaly: New York home base, fraud = >10,000 km impossible travel.

    GeographicAnomalyDetector fires at >5000 km with HIGH signal (score +=75).
    ML model also flags is_impossible_travel=1 → additional boost.
    Combined score comfortably exceeds 85 → BLOCK.
    Legit: same home location, distance = 0 → no signal.
    Precision target: >95%.
    """
    HISTORY = 4
    n_cust = max(5, n // (HISTORY + 1))
    n_fraud = max(0, int(round(n_cust * fraud_pct)))
    fraud_set = set(rng.sample(range(n_cust), min(n_fraud, n_cust)))

    merchant = _merchant("travel")
    phase1: List[Pair] = []
    phase2: List[Pair] = []

    for idx in range(n_cust):
        cust = _customer(f"loc_{idx}")
        own_dev = _device(f"loc_dev_{idx}")

        for _ in range(HISTORY):
            phase1.append((_req(cust, merchant, rng.uniform(50, 300),
                                device=own_dev,
                                ip="172.16.0.1", city="New York", country="US",
                                lat=40.7128, lon=-74.0060), False))

        if idx in fraud_set:
            # All choices are >10,000 km from New York
            far_city, far_country, far_lat, far_lon = rng.choice([
                ("Sydney",    "AU", -33.8688, 151.2093),  # 16,200 km
                ("Tokyo",     "JP",  35.6762, 139.6503),  # 10,800 km
                ("Melbourne", "AU", -37.8136, 144.9631),  # 16,700 km
                ("Cape Town", "ZA", -33.9249,  18.4241),  # 12,600 km
            ])
            phase2.append((_req(cust, merchant, rng.uniform(200, 1500),
                                device=own_dev,   # same device — pure geo anomaly
                                ip=f"203.{rng.randint(1,254)}.{rng.randint(1,254)}.1",
                                city=far_city, country=far_country,
                                lat=far_lat, lon=far_lon), True))
        else:
            phase2.append((_req(cust, merchant, rng.uniform(50, 300),
                                device=own_dev,
                                ip="172.16.0.1", city="New York", country="US",
                                lat=40.7128, lon=-74.0060), False))

    return (phase1 + phase2)[:n]


def mixed_fraud(n: int, fraud_pct: float, rng: random.Random) -> List[Pair]:
    """Mixed: samples from every scenario for a realistic blend."""
    generators = [
        normal_traffic, high_value_anomaly, velocity_attack,
        account_takeover, card_testing, device_network, location_anomaly,
    ]
    results: List[Pair] = []
    chunk = max(1, n // len(generators))
    for gen in generators:
        chunk_n = min(chunk, n - len(results))
        if chunk_n <= 0:
            break
        results.extend(gen(chunk_n, fraud_pct, rng))
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
