# app/models/report_final_schema.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class CaseSummary(BaseModel):
    action: Optional[str] = Field(None, alias="행위")
    object: Optional[str] = Field(None, alias="객체")
    place: Optional[str] = Field(None, alias="장소")
    time: Optional[str] = Field(None, alias="시간")
    result: Optional[str] = Field(None, alias="결과")
    
    class Config:
        populate_by_name = True


class CaseDetail(BaseModel):
    case_id: str
    assignee_user_id: str
    title: str
    description: str
    summary: CaseSummary
    type: str
    status: str
    occurred_at: str
    location: str
    created_at: str
    updated_at: str


class FinalAnalysis(BaseModel):
    final_id: str
    case_id: str
    recommended_decision: str = Field(..., description="TRANSFER|NON_TRANSFER|SUSPENSION")
    decision_summary: str
    legal_issue_summary: str
    evidence_sufficiency_summary: str
    remaining_risk_summary: str
    created_at: str


class ReportFinalRequest(BaseModel):
    case_detail: CaseDetail
    final_analysis: FinalAnalysis


class ReportFinalResponse(BaseModel):
    report_id: str
    case_id: str
    report_type: str = "FINAL"
    title: str
    content: Dict[str, Any]
    pdf_path: str  # ✅ 추가
    created_at: str