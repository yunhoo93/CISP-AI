# app/routers/analysis_callback.py

from fastapi import APIRouter, HTTPException
from app.models.analysis_callback_schema import (
    AnalysisCallbackRequest,
    AnalysisCallbackResponse
)
from app.services.analysis_callback_service import AnalysisCallbackService

router = APIRouter(prefix="/cases", tags=["Analysis - Callback"])


@router.post("/{case_id}/analysis/{analysis_id}/callback", response_model=AnalysisCallbackResponse)
async def handle_analysis_callback(
    case_id: str,
    analysis_id: str,
    request: AnalysisCallbackRequest
):
    """
    분석 콜백 처리
    
    **AI 서버가 분석 단계별 결과를 전달하는 콜백 API**
    
    **Path Parameters:**
    - case_id: 사건 ID
    - analysis_id: 분석 작업 ID
    
    **지원 stage:**
    - SUMMARY: 사건 요약 정보
    - TRANSCRIPT: 전사 내용
    - KEY_STATEMENT: 핵심 진술
    - CONTRADICTION: 진술 모순점
    - QUESTION: 질문 전략
    - VIDEO_EVENT: 영상 이벤트
    
    **사용 방법:**
    - 각 분석 단계 완료 시 해당 stage로 콜백 호출
    - 동일한 분석 작업에 대해 여러 번 호출 가능
    - 각 호출은 하나의 stage 결과만 포함
    
    **응답:**
    - 항상 200 OK와 "Callback received" 메시지 반환
    """
    try:
        response = AnalysisCallbackService.handle_callback(
            case_id=case_id,
            analysis_id=analysis_id,
            request=request
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"콜백 처리 실패: {str(e)}")