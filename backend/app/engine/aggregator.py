from typing import List
from app.engine.types import RiskSignal, RiskLevel, Decision, RiskEvaluationResult

def aggregate_signals(signals: List[RiskSignal]) -> RiskEvaluationResult:
    if not signals:
        return RiskEvaluationResult(
            score=0,
            risk_level=RiskLevel.LOW,
            decision=Decision.APPROVE,
            signals=[]
        )
        
    score = 0
    
    # Simple weighted aggregation based on severity
    for signal in signals:
        if signal.severity == RiskLevel.CRITICAL:
            score += 100 * signal.value
        elif signal.severity == RiskLevel.HIGH:
            score += 75 * signal.value
        elif signal.severity == RiskLevel.MEDIUM:
            score += 45 * signal.value
        elif signal.severity == RiskLevel.LOW:
            score += 15 * signal.value
            
    # Cap score at 100
    final_score = min(int(round(score)), 100)
    
    # Determine Risk Level and Decision
    if final_score <= 30:
        level = RiskLevel.LOW
        decision = Decision.APPROVE
    elif final_score <= 60:
        level = RiskLevel.MEDIUM
        decision = Decision.MONITOR  # or APPROVE
    elif final_score <= 85:
        level = RiskLevel.HIGH
        decision = Decision.REVIEW
    else:
        level = RiskLevel.CRITICAL
        decision = Decision.BLOCK
        
    return RiskEvaluationResult(
        score=final_score,
        risk_level=level,
        decision=decision,
        signals=signals
    )
