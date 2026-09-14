# app/routers/analysis_media.py

from fastapi import APIRouter, HTTPException
from app.models.analysis_media_schema import (
    AnalysisMediaRequest,
    AnalysisMediaResponse
)
from app.services.analysis_media_service import AnalysisMediaService

router = APIRouter(prefix="/analysis", tags=["Analysis - Media"])


@router.post("/stt-video", response_model=AnalysisMediaResponse)
async def analyze_media(request: AnalysisMediaRequest):
    """
    미디어 분석 (비디오 분석 또는 음성 전사)
    
    **file_type에 따라 자동 분기:**
    - "video" → 비디오 분석 (analysis_type: "VDO")
    - "audio" → 음성 전사 (analysis_type: "STT")
    
    **입력:**
    - file_id, case_id, file_type, file_path, origin_name, file_size, created_at
    
    **출력:**
    - analysis_id: 자동 생성
    - analysis_type: "VDO" 또는 "STT"
    - result_data: 분석 결과 텍스트
    
    **지원 형식:**
    - 비디오: .mp4, .avi, .mov, .mkv, .wmv, .flv
    - 오디오: .mp3, .wav, .m4a, .flac, .aac, .ogg
    """
    try:
        response = AnalysisMediaService.analyze_media(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"미디어 분석 실패: {str(e)}")