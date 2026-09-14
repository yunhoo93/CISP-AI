# app/routers/cases.py

from fastapi import APIRouter, HTTPException
from app.models.case_schema import CaseRequest, CaseResponse
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("/summary", response_model=CaseResponse)
async def create_case_summary(request: CaseRequest):
    """
    CASE 생성 및 Summary 추출
    
    - 사건 정보를 받아 6가지 요소로 구조화
    - action, object, interaction, place, time, result
    """
    try:
        response = CaseService.create_case(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CASE 생성 실패: {str(e)}")