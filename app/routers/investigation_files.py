# app/routers/investigation_files.py

from fastapi import APIRouter, HTTPException
from app.models.investigation_file_schema import (
    InvestigationFilesRequest,
    InvestigationFilesResponse
)
from app.services.investigation_file_service import InvestigationFileService

router = APIRouter(prefix="/analysis", tags=["Investigation Files"])


@router.post("/upload", response_model=InvestigationFilesResponse)
async def schedule_investigation_analysis(request: InvestigationFilesRequest):
    """
    조사 파일 분석 작업 등록
    
    **입력:**
    - case_detail: 사건 세부 정보 (Cases에서 받은 정보)
    - investigation_files: 이미 업로드된 파일들의 정보 (presigned_url 포함)
    - legal_criteria: 법리 판단 기준 (Legal Criteria에서 받은 정보)
    
    **출력:**
    - status: PENDING (분석 대기 상태)
    - targets: 각 파일별 분석 타입 (DOC/STT/VDO/IMG)
    
    **참고:**
    - 파일은 이미 업로드되어 있어야 합니다
    - 이 API는 분석 작업만 스케줄링합니다
    - 실제 분석은 백그라운드에서 비동기로 처리됩니다
    """
    try:
        response = InvestigationFileService.schedule_analysis(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 작업 등록 실패: {str(e)}")