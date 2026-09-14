# app/models/case_schema.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CaseSummary(BaseModel):
    action: str = Field(..., description="행위 (예: 강탈, 절도)")
    object: str = Field(..., description="대상/객체 (예: 스마트폰)")
    interaction: str = Field(..., description="상호작용 방식 (예: 물리적 접촉)")
    place: str = Field(..., description="장소")
    time: str = Field(..., description="시간")
    result: str = Field(..., description="결과")


class CaseRequest(BaseModel):
    title: str = Field(..., description="사건 제목")
    description: str = Field(..., description="사건 설명")
    type: str = Field(default="THEFT", description="사건 유형 (THEFT, ASSAULT, FRAUD 등)")
    occurred_at: str = Field(..., description="발생 일시 (ISO 8601)")
    location: str = Field(..., description="발생 장소")


class CaseResponse(BaseModel):
    case_id: str
    title: str
    description: str
    type: str
    occurred_at: str
    location: str
    summary: CaseSummary
    status: str = "OPEN"
    created_at: str
    updated_at: str