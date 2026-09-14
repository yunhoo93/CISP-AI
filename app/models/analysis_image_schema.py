# app/models/analysis_image_schema.py

from pydantic import BaseModel, Field
from typing import Optional


class AnalysisImageRequest(BaseModel):
    file_id: str
    case_id: str
    file_type: str
    file_path: str
    origin_name: str
    file_size: int
    created_at: str


class AnalysisImageResponse(BaseModel):
    analysis_id: str
    file_id: str
    analysis_type: str = "IMG"
    status: str = Field(default="COMPLETED", description="PROCESSING, COMPLETED, PENDING")
    result_data: str
    created_at: str