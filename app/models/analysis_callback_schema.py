# app/models/analysis_callback_schema.py

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Any


# ============================================================
# Payload 스키마들
# ============================================================

class SummaryPayload(BaseModel):
    summary: str
    confidence: float
    keywords: List[str]


class TranscriptPayload(BaseModel):
    content: str


class KeyStatement(BaseModel):
    tempId: str
    content: str


class Contradiction(BaseModel):
    statementTempId: str
    description: str
    type: str  # TIME, LOCATION, CONTENT 등


class Question(BaseModel):
    statementTempId: str
    question: str


class VideoEvent(BaseModel):
    startTime: float
    endTime: float
    eventType: str  # ASSAULT, THEFT 등
    description: str


# ============================================================
# 요청/응답 스키마
# ============================================================

class AnalysisCallbackRequest(BaseModel):
    stage: str = Field(
        ..., 
        description="SUMMARY | TRANSCRIPT | KEY_STATEMENT | CONTRADICTION | QUESTION | VIDEO_EVENT"
    )
    payload: Union[
        SummaryPayload,
        TranscriptPayload,
        List[KeyStatement],
        List[Contradiction],
        List[Question],
        List[VideoEvent],
        dict  # 기타 payload
    ]


class AnalysisCallbackResponse(BaseModel):
    message: str = "Callback received"