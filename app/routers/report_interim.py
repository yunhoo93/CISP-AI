# app/routers/report_interim.py

from fastapi import APIRouter, HTTPException
from app.models.report_interim_schema import (
    ReportInterimRequest,
    ReportInterimResponse
)
from app.services.report_interim_service import ReportInterimService

router = APIRouter(prefix="/reports/interim", tags=["Reports - Interim"])


@router.post("", response_model=ReportInterimResponse)
async def generate_interim_report(request: ReportInterimRequest):
    """
    중간보고서 생성
    
    **수사 활동 로그를 기반으로 중간보고서를 생성합니다.**
    
    **입력:**
    - case_detail: 사건 세부 정보
    - selected_activity_logs: 선택된 활동 로그 목록
    
    **출력:**
    - title: 보고서 제목
    - content: 보고서 내용 (JSON 구조)
      - 1. 사건 개요
      - 2. 수사 경과
      - 3. 현재 상황
      - 4. 향후 계획
    
    **활동 로그 필드:**
    - CASE: 사건 정보
    - ANALYSIS: 분석 작업
    - LEGAL_ISSUE: 법리 쟁점
    - LEGAL_CRITERIA: 법리 기준
    - CRITERIA_EVALUATION: 기준 평가
    - CHAT_LOG: 채팅 로그
    - REPORT: 보고서
    """
    try:
        response = ReportInterimService.generate_interim_report(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중간보고서 생성 실패: {str(e)}")