# app/models/analysis_final_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any


# ============================================================
# 공통 스키마
# ============================================================

class CaseSummary(BaseModel):
    action: str
    object: str
    interaction: str
    place: str
    time: str
    result: str


class CaseDetail(BaseModel):
    title: str
    description: str
    summary: CaseSummary
    type: str
    status: str
    occurred_at: str
    location: str


class LegalIssueInfo(BaseModel):
    issue_name: str
    related_law: str


class CriteriaEvaluationInfo(BaseModel):
    analysis_id: Optional[str] = None
    status: str
    reason: str
    evidence_gap: str


class LegalCriterionWithEvaluation(BaseModel):
    criterion_text: str
    precedent_case_no: Optional[str] = None
    precedent_decision_date: Optional[str] = None
    legal_issue: LegalIssueInfo
    criteria_evaluation: CriteriaEvaluationInfo


class AnalysisInfo(BaseModel):
    analysis_id: str
    analysis_type: str = Field(..., description="DOC|STT|VDO|IMG")
    status: str
    result_data: Any


class UsedContext(BaseModel):
    analysis_ids: List[str] = Field(default_factory=list)
    type: Optional[str] = None


class ChatLog(BaseModel):
    role: str = Field(..., description="USER|AI")
    message: str
    used_context: Optional[UsedContext] = None
    created_at: str


# ============================================================
# 요청 스키마
# ============================================================

class AnalysisFinalRequest(BaseModel):
    case_detail: CaseDetail
    legal_criteria: List[LegalCriterionWithEvaluation]
    analysys: List[AnalysisInfo]  # 오타 그대로 유지 (요청 명세에 맞춤)
    chat_logs: List[ChatLog] = Field(default_factory=list)


# ============================================================
# 응답 스키마
# ============================================================

class AnalysisFinalResponse(BaseModel):
    recommended_decision: str = Field(..., description="TRANSFER|NON_TRANSFER|SUSPENSION")
    decision_summary: str
    legal_issues_summary: str
    evidence_sufficiency_summary: str
    remaining_risk_summary: str