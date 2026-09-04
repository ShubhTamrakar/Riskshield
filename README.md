# RiskShield

**A production-grade, AI-powered fraud detection and risk management platform for fintech applications.**

RiskShield intercepts every payment, evaluates it against a multi-layer risk engine (rule-based detectors + ML model), and returns a real-time decision (`APPROVE`, `MONITOR`, `REVIEW`, or `BLOCK`) in under 200 ms.

---

## Table of Contents

1. [Problem](#problem)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Risk Detection Methodology](#risk-detection-methodology)
5. [AI/ML Architecture](#aiml-architecture)
6. [API Documentation](#api-documentation)
7. [Testing Methodology](#testing-methodology)
8. [Evaluation Results](#evaluation-results)
9. [Deployment Instructions](#deployment-instructions)
10. [Limitations](#limitations)
11. [Future Razorpay Integration](#future-razorpay-integration)

---

## Problem

Payment fraud costs the global economy hundreds of billions of dollars annually. Traditional rule-only systems suffer from high false-positive rates and cannot adapt to novel fraud patterns. Meanwhile, purely ML-based systems lack explainability and require prohibitively large training sets.

RiskShield solves this by:

- **Combining deterministic rules with ML** so each approach compensates for the other's weaknesses.
- **Providing structured, auditable signals** so analysts can understand every decision.
- **Using LLM-powered investigation** to produce human-readable fraud narratives for analysts.
- **Supporting multiple payment providers** via a pluggable adapter architecture (Phase 9).

---

## Architecture

```
Payment Provider (Razorpay / Synthetic)
          │
          ▼
 Provider Adapter Layer        ← normalizes provider-specific events
          │
          ▼
 PaymentRequest (unified schema)
          │
          ▼
┌─────────────────────────────────────────┐
│             Risk Engine                 │
│                                         │
│  ┌──────────────┐  ┌──────────────┐    │
│  │  Rule-Based  │  │  ML Detector │    │
│  │  Detectors   │  │  (XGBoost)   │    │
│  └──────┬───────┘  └──────┬───────┘    │
│         └────────┬─────────┘           │
│                  ▼                     │
│           Signal Aggregator            │
│                  │                     │
│                  ▼                     │
│      Decision + Score + Signals        │
└─────────────────────────────────────────┘
          │
          ▼
 Transaction persisted to PostgreSQL
          │
          ├──► Analyst requests AI Investigation
          │           │
          │           ▼
          │    LLM (Gemini) generates fraud narrative
          │
          └──► Dashboard (Next.js frontend)
```

**Stack:**

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12) |
| Database | PostgreSQL 15 via SQLAlchemy async |
| Cache / Rate State | Redis 7 |
| ML | XGBoost + scikit-learn |
| LLM Investigation | Google Gemini |
| Frontend | Next.js 14 (TypeScript) |
| Deployment | Docker Compose |

---

## Features

### Risk Operations Dashboard
- Real-time transaction feed with risk badges (LOW / MEDIUM / HIGH / CRITICAL)
- Risk Alert queue with live updates
- Customer risk profiles aggregated from transaction history
- AI-powered investigation reports for individual transactions

### Risk Simulation Lab
- Run controlled synthetic fraud scenarios against the **production** risk pipeline
- Scenarios: Normal, High-Value, Velocity Attack, Account Takeover, Card Testing, Device Network, Location Anomaly, Mixed Fraud
- Real-time metrics: Precision, Recall, F1, Confusion Matrix, P50/P95/P99 latency

### Model Performance Monitoring
- Live accuracy statistics computed from real transactions
- Decision distribution pie chart
- Latency tracking

### Payment Provider Adapters (Phase 9)
- `SyntheticPaymentProviderAdapter` — wraps the simulation pipeline
- `RazorpayAdapter` — normalises Razorpay Test Mode webhook events, verifies HMAC-SHA256 signatures

### Security & Reliability (Phase 8)
- API Key authentication + role-based access (viewer / analyst)
- SlowAPI rate limiting (30/min for payment creation)
- Idempotency keys backed by Redis
- Request ID propagation and structured JSON logging
- CORS, Security headers (X-Content-Type-Options, etc.)
- Input sanitisation and prompt-injection guards for LLM workflows

---

## Risk Detection Methodology

### Rule-Based Detectors

Each detector produces a `RiskSignal` with a `severity` (LOW / MEDIUM / HIGH / CRITICAL) and a continuous `value` (0–1).

| Detector | Trigger | Max Severity |
|---|---|---|
| `AmountAnomalyDetector` | Amount > 5× historical average | HIGH |
| `VelocityDetector` | > 5 tx/hr (MEDIUM) or > 10 tx/hr (CRITICAL) | CRITICAL |
| `DeviceAnomalyDetector` | New device for known customer; device used by > 3 customers | CRITICAL |
| `GeographicAnomalyDetector` | Distance from home centroid > 1 000 km (MEDIUM) or > 5 000 km (HIGH) | HIGH |
| `FailedPaymentSequenceDetector` | ≥ 3 consecutive failed payments | HIGH |
| `SharedIpDetector` | IP shared by > 5 distinct customers | HIGH |

### Signal Aggregation

Signals are combined via weighted summation:

| Severity | Weight per signal-value unit |
|---|---|
| CRITICAL | 60 |
| HIGH | 30 |
| MEDIUM | 15 |
| LOW | 5 |

Final score capped at 100:

| Score | Risk Level | Decision |
|---|---|---|
| 0 – 30 | LOW | APPROVE |
| 31 – 60 | MEDIUM | MONITOR |
| 61 – 85 | HIGH | REVIEW |
| 86 – 100 | CRITICAL | BLOCK |

### ML Detector

An XGBoost gradient-boosted classifier is trained offline on synthetic labelled data (see `backend/scripts/train_model.py`). Features fed to the model:

- `amount`, `log_amount`
- `customer_historical_tx_count`, `customer_historical_avg_amount`
- `velocity_1h`, `velocity_24h`
- `is_new_device`, `device_customer_count`
- `ip_customer_count`
- `distance_from_home_km`
- `failed_payment_sequence`

The model outputs a fraud probability; signals are generated at thresholds > 0.4 (MEDIUM), > 0.6 (HIGH), > 0.8 (CRITICAL).

**Graceful degradation:** if the ML detector raises any exception (service unavailable, model not loaded), the evaluator logs a warning and continues — the rule engine always produces a result.

---

## AI/ML Architecture

### Investigation Workflow

```
Analyst clicks "Investigate" on a flagged transaction
                    │
                    ▼
 LLM receives sanitised transaction context
 (amount, merchant, customer age, signals, decision)
                    │
                    ▼
 Prompt-injection guards run on all free-text fields
                    │
                    ▼
 Gemini produces structured fraud narrative:
   - Summary
   - Risk factors
   - Recommended action
   - Confidence note
```

**Safety constraints:**
- The LLM is **never** asked to make or change the fraud decision — that is handled deterministically by the engine.
- All customer PII is minimised before being sent to the LLM.
- Prompt-injection patterns are stripped from user-supplied text fields before LLM submission.

---

## API Documentation

Base URL: `http://localhost:8000`

Authentication: `X-API-Key: <your_key>` header on all requests.

### Payments

| Method | Path | Description |
|---|---|---|
| `POST` | `/payments` | Submit a new payment for risk evaluation |
| `GET` | `/payments` | List payments (paginated, filterable) |
| `GET` | `/payments/{id}` | Get a single transaction |
| `GET` | `/payments/{id}/investigate` | LLM fraud investigation (analyst role) |
| `GET` | `/payments/summary` | Aggregate risk statistics |

**POST `/payments` — example request:**
```json
{
  "external_transaction_id": "txn_abc123",
  "amount": 250.00,
  "currency": "USD",
  "payment_method": "card",
  "ip_address": "203.0.113.5",
  "country": "US",
  "city": "New York",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "customer": {
    "external_customer_id": "cust_xyz",
    "account_created_at": "2023-06-01T00:00:00Z",
    "status": "active"
  },
  "merchant": {
    "external_merchant_id": "merch_001",
    "category": "electronics",
    "status": "active"
  },
  "device": {
    "device_fingerprint": "fp_abc",
    "device_type": "mobile",
    "operating_system": "iOS"
  }
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "external_transaction_id": "txn_abc123",
  "amount": 250.00,
  "status": "completed",
  "risk_evaluation": {
    "score": 9,
    "risk_level": "LOW",
    "decision": "APPROVE",
    "signals": []
  }
}
```

### Webhooks

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhooks/{provider}` | Receive payment provider webhook events |

Supported providers: `razorpay`, `synthetic`

Signature verification is done by the provider-specific adapter. Set `WEBHOOK_SECRET_{PROVIDER}` to enable.

### Simulation

| Method | Path | Description |
|---|---|---|
| `POST` | `/simulation/runs` | Start a simulation run |
| `GET` | `/simulation/runs` | List all simulation runs |
| `GET` | `/simulation/runs/{id}` | Get results for a run |

### Observability

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (checks DB + Redis) |
| `GET` | `/metrics` | Prometheus metrics |

---

## Testing Methodology

### Test Suites

| Suite | Path | Coverage |
|---|---|---|
| Engine unit tests | `tests/engine/test_detectors.py` | Individual detector logic |
| API integration | `tests/api/test_payments.py` | CRUD + validation |
| Adapter unit tests | `tests/adapters/test_razorpay.py` | Signature + normalisation |
| Simulation validation | `tests/simulation/` | Metrics computation |
| Security | `tests/security/test_sanitizer.py` | Prompt injection guards |
| E2E scenarios | `tests/e2e/test_scenarios.py` | 14 real-world fraud patterns |

### Running Tests

```bash
# Inside Docker
docker exec riskshield-backend-1 pytest tests/ -v

# By suite
docker exec riskshield-backend-1 pytest tests/e2e/ -v
docker exec riskshield-backend-1 pytest tests/engine/ -v
```

### E2E Scenario Coverage

| # | Scenario | Expected |
|---|---|---|
| 1 | Normal payment | APPROVE / LOW |
| 2 | High-value anomaly (>5× avg) | `amount_anomaly` signal |
| 3 | Velocity attack (>10/hr) | MEDIUM–CRITICAL |
| 4 | Account takeover (geo jump) | `geographic_anomaly` signal |
| 5 | New device for known customer | `new_device` signal |
| 6 | Location anomaly (>1000 km) | `geographic_anomaly` signal |
| 7 | Shared device/IP (>6 customers) | `shared_device` / `shared_ip` |
| 8 | Duplicate event (idempotency key) | Same response, no new TX |
| 9 | Invalid request (amount < 0) | 422 Unprocessable Entity |
| 10 | Invalid webhook signature | 401 Unauthorized |
| 11 | ML service unavailable | Rules still produce a decision |
| 12 | LLM unavailable | Payments unaffected |
| 13 | DB failure | Graceful error (mocked) |
| 14 | Repeated identical request | Consistent result via idempotency |

---

## Evaluation Results

> Results are produced by running the **Simulation Lab** against the production risk engine. No values are invented.

### Demo Simulation — Velocity Attack Scenario

Run from the frontend Simulation Lab (`http://localhost:3000/simulation`):

- **Scenario:** Velocity Attack
- **Transactions:** 200
- **Fraud percentage:** 30%

Typical results observed during development:

| Metric | Value |
|---|---|
| Precision | ~0.85–0.95 |
| Recall | ~0.60–0.80 |
| F1 Score | ~0.70–0.85 |
| P50 Latency | ~80–120 ms |
| P95 Latency | ~150–250 ms |
| P99 Latency | ~200–350 ms |

> **Note:** Metrics vary by scenario, seed, and whether the ML model is trained. Run the Simulation Lab yourself to produce your own evaluation results. Do not treat the ranges above as authoritative benchmarks.

---

## Deployment Instructions

### Prerequisites

- Docker Desktop ≥ 24
- Docker Compose ≥ 2.20

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```dotenv
# --- Database ---
POSTGRES_USER=riskshield
POSTGRES_PASSWORD=<your_password>
POSTGRES_DB=riskshield

# --- Application ---
API_KEY=<your_api_key>                  # Used by the frontend and tests
SECRET_KEY=<random_32_char_string>      # JWT / session signing

# --- Redis ---
REDIS_URL=redis://redis:6379/0

# --- AI (optional) ---
GEMINI_API_KEY=<your_gemini_api_key>    # Only needed for LLM investigation

# --- Webhook secrets (optional) ---
WEBHOOK_SECRET_RAZORPAY=<razorpay_webhook_secret>
```

### Start the System

```bash
# Clone and enter the project
git clone <repo>
cd RiskShield

# Copy environment file
cp .env.example .env
# Edit .env with your secrets

# Start all services (DB, Redis, backend, frontend)
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Prometheus Metrics: http://localhost:8000/metrics

### Database Migrations

Migrations run automatically on backend startup via Alembic. To run manually:

```bash
docker exec riskshield-backend-1 alembic upgrade head
```

### Train the ML Model

```bash
docker exec riskshield-backend-1 python scripts/train_model.py
```

The model is saved to `backend/app/engine/model/fraud_model.pkl`. The risk engine loads it automatically on next evaluation.

### Execute Tests

```bash
# All tests
docker exec riskshield-backend-1 pytest tests/ -v

# E2E scenarios only
docker exec riskshield-backend-1 pytest tests/e2e/ -v

# Adapters
docker exec riskshield-backend-1 pytest tests/adapters/ -v
```

### Run a Simulation

**Via frontend:** Navigate to `http://localhost:3000/simulation`, configure scenario parameters, and click Run.

**Via API:**
```bash
curl -X POST http://localhost:8000/simulation/runs \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "velocity_attack",
    "n_transactions": 200,
    "fraud_pct": 0.3,
    "seed": 42,
    "mode": "full"
  }'
```

### Demo Walkthrough

Run the interactive demonstration script (requires `jq` and `bash` on Linux/macOS, or WSL on Windows):

```bash
bash scripts/demo.sh
```

This walks through:
1. A legitimate payment → `APPROVE / LOW`
2. A geographic anomaly → `REVIEW`
3. A velocity attack sequence → `BLOCK / CRITICAL`

---

## Limitations

1. **ML Model requires training data.** The XGBoost model must be trained before it contributes signals. Until `train_model.py` is run, the engine falls back gracefully to rule-only mode.

2. **LLM investigation requires a Gemini API key.** If `GEMINI_API_KEY` is not set, the `/investigate` endpoint will return an error. All payment processing is unaffected.

3. **Idempotency requires Redis.** If Redis is unavailable, idempotency checking is silently bypassed (logged as a warning). Payments still process correctly.

4. **Rate limiting is per-process.** SlowAPI uses an in-memory store by default. In multi-worker deployments, use a Redis-backed limiter for cross-process rate limiting.

5. **Synthetic fraud data.** The simulation generates synthetic transactions from statistical models. Real fraud patterns will differ in distribution and subtlety.

6. **No live payment blocking.** The current Razorpay integration only processes inbound webhook events. It does not programmatically block or refund Razorpay payments — that requires the Razorpay server-to-server API and is out of scope.

7. **Single-region deployment.** The Docker Compose configuration is suitable for local development and small-scale demos. A production deployment would require Kubernetes, regional DB replicas, and a distributed cache.

---

## Future Razorpay Integration

RiskShield is architecturally ready for a live Razorpay Test Mode integration. The work remaining:

### What exists today

- `RazorpayAdapter` — verifies HMAC-SHA256 signatures, normalises `payment.authorized` events into a `PaymentRequest`.
- Generic webhook router at `POST /webhooks/razorpay`.
- `WEBHOOK_SECRET_RAZORPAY` environment variable support.

### What is needed to go live

1. **Register the webhook in Razorpay Dashboard** (Test Mode → Webhooks → `https://your-domain.com/webhooks/razorpay`).
2. **Set `WEBHOOK_SECRET_RAZORPAY`** to the secret from the Razorpay Dashboard.
3. **Map Razorpay customer IDs** — extend `RazorpayAdapter.normalize_payload()` to extract `customer_id` from the payment entity if available.
4. **Expose the backend publicly** (e.g., via ngrok for local testing, or a real domain for staging).
5. **Programmatic response** — if the risk engine returns `BLOCK`, call the Razorpay API to capture/refund the payment (requires `razorpay` Python SDK and production credentials).

> **Important:** Do not use production credentials during testing. Razorpay Test Mode keys are prefixed with `rzp_test_`.
