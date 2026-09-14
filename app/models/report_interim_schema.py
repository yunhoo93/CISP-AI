# app/models/report_interim_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


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


class ActivityLog(BaseModel):
    log_id: str
    field: str = Field(..., description="CASE|ANALYSIS|LEGAL_ISSUE|LEGAL_CRITERIA|CRITERIA_EVALUATION|CHAT_LOG|REPORT")
    activity_type: str = Field(..., description="CREATE|UPDATE|DELETE")
    payload: str
    created_at: str


class ReportInterimRequest(BaseModel):
    case_detail: CaseDetail
    selected_activity_logs: List[ActivityLog]


class ReportInterimResponse(BaseModel):
    report_id: str
    case_id: str
    report_type: str = "INTERIM"
    title: str
    content: Dict[str, Any]
    pdf_path: str  # ✅ 추가
    created_at: str