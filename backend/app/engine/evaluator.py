from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.transaction import PaymentRequest
from app.engine.types import RiskEvaluationResult
from app.engine.features.extractor import extract_features
from app.engine.detectors.rules import ALL_DETECTORS
from app.engine.aggregator import aggregate_signals

async def evaluate_transaction(db: AsyncSession, request: PaymentRequest) -> RiskEvaluationResult:
    # 1. Extract context (historical data, DB lookups, velocity, etc.)
    context = await extract_features(db, request)
    
    # 2. Run detectors
    signals = []
    for detector in ALL_DETECTORS:
        signal = detector.evaluate(context)
        if signal:
            signals.append(signal)
            
    # 3. Aggregate
    result = aggregate_signals(signals)
    
    return result
