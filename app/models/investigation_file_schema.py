# app/models/investigation_file_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional


# ============================================================
# 파일 업로드 응답 (POST /analysis/upload - multipart)
# ============================================================

class FileUploadResponse(BaseModel):
    file_id: str
    case_id: str
    file_type: str
    file_path: str
    origin_name: str
    file_size: int
    created_at: str


# ============================================================
# Investigation Files 요청/응답 (POST /analysis/upload - json)
# ============================================================

class CaseSummary(BaseModel):
    action: str
    object: str
    interaction: str
    place: str
    time: str
    result: str


class CaseDetail(BaseModel):
    case_id: str
    title: str
    description: str
    summary: CaseSummary
    type: str = Field(..., description="ASSAULT|THEFT|FRAUD|TRAFFIC|OTHER")
    status: str = Field(..., description="OPEN|ONGOING|DONE")
    occurred_at: str
    location: str


class LegalIssueInfo(BaseModel):
    issue_name: str
    related_law: str


class LegalCriterionInfo(BaseModel):
    criterion_text: str
    precedent_case_no: Optional[str] = None
    precedent_decision_date: Optional[str] = None
    legal_issue: LegalIssueInfo


class InvestigationFileInfo(BaseModel):
    job_id: str
    file_type: str = Field(..., description="VIDEO|AUDIO|IMAGE|DOCUMENT")
    origin_name: str
    presigned_url: str
    content_type: str


class InvestigationFilesRequest(BaseModel):
    case_detail: CaseDetail
    investigation_files: List[InvestigationFileInfo]
    legal_criteria: List[LegalCriterionInfo]


class AnalysisTarget(BaseModel):
    origin_name: str
    file_type: str
    analysis_type: str = Field(..., description="DOC|STT|VDO|IMG")


class InvestigationFilesResponse(BaseModel):
    status: str = "PENDING"
    targets: List[AnalysisTarget]