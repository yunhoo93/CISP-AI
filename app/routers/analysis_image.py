# app/routers/analysis_image.py

from fastapi import APIRouter, HTTPException
from app.models.analysis_image_schema import AnalysisImageRequest, AnalysisImageResponse
from app.services.analysis_image_service import AnalysisImageService

router = APIRouter(prefix="/analysis", tags=["Analysis - Image"])


@router.post("/img", response_model=AnalysisImageResponse)
async def analyze_image(request: AnalysisImageRequest):
    """
    이미지 분석
    
    - GPT-4o Vision으로 이미지 분석
    - 객체 감지, 장면 맥락, 증거 가치 평가
    """
    try:
        response = AnalysisImageService.analyze_image(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 실패: {str(e)}")