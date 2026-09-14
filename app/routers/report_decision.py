# app/routers/report_decision.py

from fastapi import APIRouter, HTTPException
from app.models.report_decision_schema import (
    ReportDecisionRequest,
    ReportDecisionResponse
)
from app.services.report_decision_service import ReportDecisionService

router = APIRouter(prefix="/reports/decision", tags=["Reports - Decision"])


@router.post("", response_model=ReportDecisionResponse)
async def generate_decision_report(request: ReportDecisionRequest):
    """
    최종결정서 생성
    
    **사용자가 선택한 최종 판단을 기준으로 결정서를 생성합니다.**
    
    **입력:**
    - case_detail: 사건 세부 정보
    - decision_type: 사용자 최종 판단 (TRANSFER|NON_TRANSFER|SUSPENSION)
    - final_analysis: AI 분석 결과 (참고용)
    
    **출력:**
    - title: 결정서 제목
    - content: 결정서 내용 (JSON 구조)
      - 주문
      - 1. 사건 개요
      - 2. 판단 이유
      - 3. 증거 평가
      - 4. 법리 검토
      - 5. 결론
    
    **특징:**
    - 사용자 판단(decision_type)을 우선으로 작성
    - AI 추천과 다를 경우 판단 변경 사유 포함
    
    **결정 유형:**
    - TRANSFER: 송치 결정
    - NON_TRANSFER: 불송치 결정
    - SUSPENSION: 수사중지 결정
    """
    try:
        response = ReportDecisionService.generate_decision_report(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최종결정서 생성 실패: {str(e)}")