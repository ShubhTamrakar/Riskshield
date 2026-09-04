import logging
from typing import Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.transaction import PaymentRequest
from app.engine.types import RiskEvaluationResult
from app.engine.features.extractor import extract_features
from app.engine.detectors.rules import ALL_DETECTORS
from app.engine.aggregator import aggregate_signals

logger = logging.getLogger(__name__)

EngineMode = Literal["rules_only", "ml_only", "rules_ml", "full"]

async def evaluate_transaction(
    db: AsyncSession,
    request: PaymentRequest,
    mode: EngineMode = "full"
) -> RiskEvaluationResult:
    """Evaluate a transaction through the risk engine.

    Args:
        db: Database session.
        request: Payment request.
        mode: Which detectors to run.
            - "rules_only": only rule-based detectors (no ML)
            - "ml_only": only ML detector
            - "rules_ml": rules + ML (no extra behavioral signals if separate)
            - "full" (default): all detectors — production behaviour
    """
    # 1. Extract context (historical data, DB lookups, velocity, etc.)
    context = await extract_features(db, request)

    # 2. Filter detectors based on mode
    if mode == "full":
        detectors = ALL_DETECTORS
    elif mode == "rules_only":
        detectors = [d for d in ALL_DETECTORS if type(d).__name__ != "MlFraudDetector"]
    elif mode == "ml_only":
        detectors = [d for d in ALL_DETECTORS if type(d).__name__ == "MlFraudDetector"]
    else:  # rules_ml — all currently means same as full (ML is already one of the detectors)
        detectors = ALL_DETECTORS

    # 3. Run detectors — each isolated so one failure does not abort the pipeline
    signals = []
    for detector in detectors:
        try:
            signal = detector.evaluate(context)
            if signal:
                signals.append(signal)
        except Exception as exc:
            logger.warning(
                "Detector %s raised an exception and was skipped: %s",
                type(detector).__name__, exc,
            )

    # 4. Aggregate
    result = aggregate_signals(signals)

    return result
