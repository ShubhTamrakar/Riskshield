import json
import os
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from google import genai
from pydantic import ValidationError

from app.schemas.ai import StructuredInvestigationReport
from app.models.transaction import Transaction
from app.models.risk import RiskEvaluation
from app.ai.guardrails import generate_fallback_report

SYSTEM_PROMPT = """You are an expert fraud analyst system for RiskShield.
Your job is to analyze the provided deterministic risk signals and output a structured JSON report.
DO NOT invent, hallucinate, or assume any facts that are not explicitly provided in the input payload.
You DO NOT make the final decision. You only explain the evidence provided.
If evidence for a specific section is unavailable, explicitly state "Unavailable based on provided evidence."
Return ONLY a valid JSON object matching the requested schema.
"""

def build_sanitized_payload(transaction: Transaction, risk_eval: RiskEvaluation) -> str:
    """Strips PII and builds a structured payload for the LLM."""
    # We omit customer names, specific raw IP addresses, raw exact location coordinates, etc.
    # We only include the signals and high level metadata.
    payload = {
        "transaction": {
            "amount": transaction.amount,
            "status": transaction.status
        },
        "risk_evaluation": {
            "score": risk_eval.score if risk_eval else None,
            "risk_level": risk_eval.risk_level if risk_eval else None,
            "decision": risk_eval.decision if risk_eval else None,
            "signals": risk_eval.signals if risk_eval else []
        }
    }
    return json.dumps(payload, indent=2)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def _call_llm_with_retry(payload_str: str) -> str:
    """Calls the LLM provider with retries."""
    # Try to load API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # For this test environment, if no API key is set, we simulate an error 
        # to trigger the fallback, or we could return a mock JSON.
        raise ValueError("GEMINI_API_KEY not set. Triggering fallback.")
        
    client = genai.Client(api_key=api_key)
    
    # We use asyncio.to_thread because the SDK might be synchronous, 
    # or use the async client if available. We will just use to_thread to prevent blocking.
    def do_call():
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=payload_str,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=StructuredInvestigationReport,
                temperature=0.1
            ),
        )
        return response.text

    return await asyncio.to_thread(do_call)

async def investigate_transaction(transaction: Transaction, risk_eval: RiskEvaluation) -> StructuredInvestigationReport:
    """Main entry point to investigate a transaction."""
    if not risk_eval:
        return generate_fallback_report(risk_eval)
        
    payload_str = build_sanitized_payload(transaction, risk_eval)
    
    try:
        # Enforce a 5-second timeout on the LLM call
        raw_response = await asyncio.wait_for(_call_llm_with_retry(payload_str), timeout=10.0)
        
        # Parse and validate the structured output
        report = StructuredInvestigationReport.model_validate_json(raw_response)
        return report
        
    except (asyncio.TimeoutError, ValueError, ValidationError, Exception) as e:
        print(f"AI Investigator failed or timed out: {e}")
        return generate_fallback_report(risk_eval)
