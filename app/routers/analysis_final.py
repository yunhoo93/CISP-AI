# app/routers/analysis_final.py

from fastapi import APIRouter, HTTPException
from app.models.analysis_final_schema import (
    AnalysisFinalRequest,
    AnalysisFinalResponse
)
from app.services.analysis_final_service import AnalysisFinalService

router = APIRouter(prefix="/analysis/final", tags=["Analysis - Final"])


@router.post("", response_model=AnalysisFinalResponse)
async def generate_final_analysis(request: AnalysisFinalRequest):
    """
    최종 수사 의견 생성
    
    **모든 분석 결과를 종합하여 최종 수사 의견을 생성합니다.**
    
    **입력:**
    - case_detail: 사건 세부 정보
    - legal_criteria: 법리 판단 기준 (평가 포함)
    - analysys: 분석 결과 목록
    - chat_logs: 채팅 로그 (선택)
    
    **출력:**
    - recommended_decision: 송치/불송치/수사중지
    - decision_summary: 사건 판단 요약
    - legal_issues_summary: 법리 판단 요약
    - evidence_sufficiency_summary: 증거 충분성 요약
    - remaining_risk_summary: 잔여 리스크 요약
    """
    try:
        response = AnalysisFinalService.generate_final_analysis(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최종 분석 생성 실패: {str(e)}")