# app/services/analysis_media_service.py

import uuid
from datetime import datetime, timezone
from pathlib import Path
import google.generativeai as genai
from app.config import settings
from app.models.analysis_media_schema import (
    AnalysisMediaRequest,
    AnalysisMediaResponse
)
from app.utils.file_validator import FileValidator

# Gemini API 설정
genai.configure(api_key=settings.GOOGLE_API_KEY)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisMediaService:
    
    @staticmethod
    def analyze_media(request: AnalysisMediaRequest) -> AnalysisMediaResponse:
        """
        미디어 분석 (비디오 또는 오디오)
        file_type에 따라 자동 분기:
        - "video" → 비디오 분석 (VDO)
        - "audio" → 음성 전사 (STT)
        """
        file_path = Path(request.file_path)
        file_type_lower = request.file_type.lower()
        
        # 파일 타입 검증
        if file_type_lower == "video":
            FileValidator.validate_video(request.file_type, request.file_path)
            analysis_type = "VDO"
            action_name = "비디오 분석"
        elif file_type_lower == "audio":
            FileValidator.validate_audio(request.file_type, request.file_path)
            analysis_type = "STT"
            action_name = "음성 전사"
        else:
            raise ValueError(f"지원하지 않는 file_type입니다: {request.file_type}. 'video' 또는 'audio'여야 합니다.")
        
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {request.file_path}")
        
        print(f"\n🎬 {action_name} 시작: {request.origin_name}")
        
        analysis_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        status = "PROCESSING"
        
        try:
            # Gemini로 분석
            if file_type_lower == "video":
                analysis_text = AnalysisMediaService._analyze_video_with_gemini(file_path)
            else:  # audio
                analysis_text = AnalysisMediaService._transcribe_audio_with_gemini(file_path)
            
            status = "COMPLETED"
            print(f"✅ {action_name} 완료")
            
        except Exception as e:
            analysis_text = f"분석 실패: {str(e)}"
            status = "PENDING"
            print(f"⚠️ {action_name} 실패: {e}")
        
        return AnalysisMediaResponse(
            analysis_id=analysis_id,
            file_id=request.file_id,
            analysis_type=analysis_type,
            status=status,
            result_data=analysis_text,
            created_at=created_at
        )
    
    @staticmethod
    def _analyze_video_with_gemini(video_path: Path) -> str:
        """Gemini로 비디오 분석"""
        
        system_prompt = """당신은 수사 보조 영상 분석 담당자입니다.

제공된 영상을 상세히 분석하여 다음 정보를 추출하십시오:

1. 영상의 시간대 및 장소 (배경, 환경, 조명 등)
2. 등장 인물 (복장, 행동, 움직임, 상호작용)
3. 주요 사건 및 행위 (시간순 나열)
4. 물체 및 증거물 (차량, 물건, 흔적 등)
5. 특이사항 (의심스러운 행동, 중요한 디테일)

절대 규칙:
- 영상에 보이는 객관적 사실만 기술
- 시간 흐름에 따라 순서대로 설명
- 추정은 '~으로 보입니다'로 표현
- 영상에 없는 내용 추가 금지
- 법적 판단이나 결론 금지
- 자연스러운 설명문으로 작성 (10~15문장)"""
        
        try:
            uploaded_file = genai.upload_file(str(video_path))
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            response = model.generate_content(
                [system_prompt, uploaded_file],
                request_options={"timeout": 600}
            )
            
            uploaded_file.delete()
            return response.text.strip()
        
        except Exception as e:
            print(f"⚠️ Gemini API 호출 실패: {e}")
            return f"비디오 분석 실패: {str(e)}"
    
    @staticmethod
    def _transcribe_audio_with_gemini(audio_path: Path) -> str:
        """Gemini로 음성 전사"""
        
        system_prompt = """당신은 수사 보조 음성 전사 담당자입니다.

제공된 음성 파일을 정확하게 전사하십시오:

1. 발화자별로 구분하여 전사
2. 시간 정보 포함 (가능한 경우)
3. 배경 소음이나 특이사항 기록
4. 불명확한 부분은 [불명] 표시

절대 규칙:
- 들리는 내용을 정확하게 전사
- 문장 부호와 맞춤법 준수
- 욕설이나 비속어도 그대로 전사
- 추가 해석이나 요약 금지
- 전사 형식: "화자: 내용" 또는 "내용"
- 자연스러운 문장으로 작성"""
        
        try:
            uploaded_file = genai.upload_file(str(audio_path))
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            response = model.generate_content(
                [system_prompt, uploaded_file],
                request_options={"timeout": 600}
            )
            
            uploaded_file.delete()
            return response.text.strip()
        
        except Exception as e:
            print(f"⚠️ Gemini API 호출 실패: {e}")
            return f"음성 전사 실패: {str(e)}"