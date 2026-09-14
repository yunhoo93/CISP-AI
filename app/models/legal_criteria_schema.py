# app/models/legal_criteria_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional


class CaseSummary(BaseModel):
    action: str
    object: str
    interaction: str
    place: str
    time: str
    result: str


class LegalCriteriaRequest(BaseModel):
    description: str
    summary: CaseSummary
    type: str = Field(..., description="ASSAULT|THEFT|FRAUD|TRAFFIC|OTHER")
    occurred_at: str
    location: str


class CriteriaEvaluation(BaseModel):
    status: str = Field(..., description="INSUFFICIENT, MET, NOT_MET")
    reason: str
    evidence_gap: str


class LegalCriterion(BaseModel):
    criterion_text: str
    precedent_case_no: Optional[str] = None
    precedent_decision_date: Optional[str] = None
    evaluation: CriteriaEvaluation


class LegalIssue(BaseModel):
    issue_name: str
    related_law: str
    legal_criteria: List[LegalCriterion]


class LegalCriteriaResponse(BaseModel):
    legal_issues: List[LegalIssue]