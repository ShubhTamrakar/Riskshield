"""
Prometheus metrics definitions.

Import and use these in endpoints / middleware to record observations.
All metrics are collected by the default prometheus_client registry.
"""
from prometheus_client import Counter, Histogram

# ── HTTP request metrics ──────────────────────────────────────────────────────

http_requests_total = Counter(
    "riskshield_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "riskshield_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Risk engine metrics ───────────────────────────────────────────────────────

risk_evaluation_duration_seconds = Histogram(
    "riskshield_risk_evaluation_duration_seconds",
    "Risk engine evaluation latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

failed_risk_evaluations_total = Counter(
    "riskshield_failed_risk_evaluations_total",
    "Number of risk evaluations that threw an exception",
)

# ── LLM metrics ───────────────────────────────────────────────────────────────

llm_request_duration_seconds = Histogram(
    "riskshield_llm_request_duration_seconds",
    "LLM investigation call latency",
    ["method", "path"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

llm_failures_total = Counter(
    "riskshield_llm_failures_total",
    "Number of LLM calls that failed",
)

# ── Simulation metrics ────────────────────────────────────────────────────────

simulation_runs_total = Counter(
    "riskshield_simulation_runs_total",
    "Simulation runs launched",
    ["status"],
)

# ── Webhook metrics ───────────────────────────────────────────────────────────

webhook_events_total = Counter(
    "riskshield_webhook_events_total",
    "Incoming webhook events",
    ["provider", "event_type"],
)

webhook_failures_total = Counter(
    "riskshield_webhook_failures_total",
    "Webhook processing failures",
    ["provider", "reason"],
)
