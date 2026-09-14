# app/models/analysis_document_schema.py

from pydantic import BaseModel, Field
from typing import Optional


class AnalysisDocumentRequest(BaseModel):
    file_id: str
    case_id: str
    file_type: str
    file_path: str
    origin_name: str
    file_size: int
    created_at: str


class AnalysisDocumentResponse(BaseModel):
    analysis_id: str
    file_id: str
    analysis_type: str = "DOC"
    status: str = Field(default="COMPLETED", description="PROCESSING, COMPLETED, PENDING")
    result_data: str
    created_at: str