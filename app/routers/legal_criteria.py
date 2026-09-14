# app/routers/legal_criteria.py

from fastapi import APIRouter, HTTPException
from app.models.legal_criteria_schema import LegalCriteriaRequest, LegalCriteriaResponse
from app.services.legal_criteria_service import LegalCriteriaService

router = APIRouter(prefix="/legal-criteria", tags=["Legal Criteria"])


@router.post("", response_model=LegalCriteriaResponse)
async def search_legal_criteria(request: LegalCriteriaRequest):
    """
    법률 기준 검색 및 분석
    
    - 벡터 검색으로 관련 법조문 추출
    - 법리 쟁점 도출
    - 판단 기준 생성
    - 판례 검색 및 연결
    """
    try:
        # ✅ 수정: analyze_legal_criteria 메서드 호출
        response = LegalCriteriaService.analyze_legal_criteria(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"법률 기준 검색 실패: {str(e)}")