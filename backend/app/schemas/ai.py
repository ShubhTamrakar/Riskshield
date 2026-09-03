from pydantic import BaseModel, Field
from typing import List, Optional

class StructuredInvestigationReport(BaseModel):
    executive_summary: str = Field(description="A brief 1-2 sentence summary of the transaction's overall risk.")
    primary_risk_factors: List[str] = Field(description="The primary reasons this transaction was flagged (e.g. 'amount_anomaly', 'new_device').")
    supporting_evidence: List[str] = Field(description="Specific data points supporting the risk factors (e.g. 'Amount is 18x higher than average').")
    behavioral_comparison: str = Field(description="Comparison of this transaction to the customer's historical baseline.")
    recommended_investigation_action: str = Field(description="Action recommendation for an analyst (e.g. 'Call customer to verify device').")
    confidence_statement: str = Field(description="Statement of confidence in this explanation or explicitly stating if evidence is unavailable.")
