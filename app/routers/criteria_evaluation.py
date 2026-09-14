# app/routers/criteria_evaluation.py

from fastapi import APIRouter, HTTPException
from app.models.criteria_evaluation_schema import (
    CriteriaEvaluationRequest,
    CriteriaEvaluationResponse
)
from app.services.criteria_evaluation_service import CriteriaEvaluationService

router = APIRouter(prefix="/criteria-evaluation", tags=["Criteria Evaluation"])


@router.post("", response_model=CriteriaEvaluationResponse)
async def evaluate_criteria(request: CriteriaEvaluationRequest):
    """
    법리 판단 기준 충족 평가
    
    **두 가지 모드:**
    
    **모드 1: ANALYSIS 없음**
    - 입력: case_detail + legal_criteria
    - 출력: INSUFFICIENT (증거 부족)
    - 사용: 증거 분석 전 초기 평가
    
    **모드 2: ANALYSIS 있음**
    - 입력: analysis + legal_criteria
    - 출력: INSUFFICIENT | MET | NOT_MET
    - 사용: 증거 분석 후 종합 평가
    
    **응답:**
    - status: INSUFFICIENT (불충분) | MET (충족) | NOT_MET (미충족)
    - reason: 평가 이유
    - evidence_gap: 부족한 증거 (INSUFFICIENT일 때만)
    """
    try:
        response = CriteriaEvaluationService.evaluate_criteria(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 실패: {str(e)}")