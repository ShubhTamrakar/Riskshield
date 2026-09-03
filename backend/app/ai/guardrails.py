import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from app.schemas.ai import StructuredInvestigationReport
from app.models.risk import RiskEvaluation

def generate_fallback_report(risk_eval: RiskEvaluation) -> StructuredInvestigationReport:
    """Generates a deterministic fallback report if the LLM fails."""
    primary_factors = []
    evidence = []
    
    if risk_eval and risk_eval.signals:
        for signal in risk_eval.signals:
            if isinstance(signal, dict):
                name = signal.get("name", "unknown")
                explanation = signal.get("explanation", "")
                primary_factors.append(name)
                evidence.append(explanation)
                
    if not primary_factors:
        primary_factors = ["no_signals"]
        evidence = ["No specific risk signals triggered."]
        
    return StructuredInvestigationReport(
        executive_summary="AI Investigation Service is currently unavailable. Displaying deterministic fallback.",
        primary_risk_factors=primary_factors,
        supporting_evidence=evidence,
        behavioral_comparison="Unavailable due to service disruption.",
        recommended_investigation_action="Review transaction manually based on triggered heuristics.",
        confidence_statement="LOW - Fallback generated."
    )
