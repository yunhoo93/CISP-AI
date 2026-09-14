# app/routers/report_final.py

from fastapi import APIRouter, HTTPException
from app.models.report_final_schema import (
    ReportFinalRequest,
    ReportFinalResponse
)
from app.services.report_final_service import ReportFinalService

router = APIRouter(prefix="/reports/final", tags=["Reports - Final"])


@router.post("", response_model=ReportFinalResponse)
async def generate_final_report(request: ReportFinalRequest):
    """
    최종보고서 (송치의견서) 생성
    
    **최종 분석 결과를 바탕으로 송치의견서를 생성합니다.**
    
    **입력:**
    - case_detail: 사건 세부 정보
    - final_analysis: 최종 분석 결과
    
    **출력:**
    - title: 보고서 제목 (송치/불송치/수사중지 의견서)
    - content: 보고서 내용 (JSON 구조)
      - 문서번호, 기안일자
      - 1. 사건 개요
      - 2. 수사 결과
      - 3. 법리 검토
      - 4. 송치 의견
      - 5. 특이사항
    
    **송치의견:**
    - TRANSFER: 송치
    - NON_TRANSFER: 불송치
    - SUSPENSION: 수사중지
    """
    try:
        response = ReportFinalService.generate_final_report(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최종보고서 생성 실패: {str(e)}")