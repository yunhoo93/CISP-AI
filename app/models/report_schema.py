# app/models/report_schema.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ReportListItem(BaseModel):
    report_id: str
    case_id: Optional[str] = None
    report_type: str = Field(..., description="INTERIM|FINAL|DECISION")
    title: str
    created_at: str


class ReportDetail(BaseModel):
    report_id: str
    case_id: Optional[str] = None
    report_type: str = Field(..., description="INTERIM|FINAL|DECISION")
    title: str
    content: Dict[str, Any]
    created_at: str


class ReportListResponse(BaseModel):
    total: int
    reports: List[ReportListItem]