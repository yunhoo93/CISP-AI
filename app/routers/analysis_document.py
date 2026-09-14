# app/routers/analysis_document.py

from fastapi import APIRouter, HTTPException
from app.models.analysis_document_schema import AnalysisDocumentRequest, AnalysisDocumentResponse
from app.services.analysis_document_service import AnalysisDocumentService

router = APIRouter(prefix="/analysis", tags=["Analysis - Document"])


@router.post("/doc", response_model=AnalysisDocumentResponse)
async def analyze_document(request: AnalysisDocumentRequest):
    """
    문서 분석
    
    - PDF, DOCX, TXT 파일 텍스트 추출
    - GPT로 요약 및 핵심 내용 분석
    """
    try:
        response = AnalysisDocumentService.analyze_document(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 분석 실패: {str(e)}")