# app/services/analysis_image_service.py

import json
import uuid
import base64
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI
from app.config import settings
from app.models.analysis_image_schema import (
    AnalysisImageRequest,
    AnalysisImageResponse
)
from app.utils.file_validator import FileValidator

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisImageService:
    @staticmethod
    def analyze_image(request: AnalysisImageRequest) -> AnalysisImageResponse:
        """
        이미지 분석 (GPT-4o Vision)
        AI.ipynb의 이미지 분석 로직 이식
        """
        file_path = Path(request.file_path)
        
        # ✅ 파일 검증 추가
        FileValidator.validate_image(request.file_type, request.file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {request.file_path}")
        
        print(f"\n🔄 이미지 분석 시작: {request.origin_name}")
        
        # analysis_id 자동 생성
        analysis_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        status = "PROCESSING"
        
        try:
            # 이미지 base64 인코딩
            image_base64 = AnalysisImageService._encode_image(file_path)
            
            # GPT-4o Vision으로 분석
            analysis_text = AnalysisImageService._analyze_with_vision(
                image_base64,
                request.case_id
            )
            
            status = "COMPLETED"
            print(f"✅ 이미지 분석 완료")
            
        except Exception as e:
            analysis_text = f"분석 실패: {str(e)}"
            status = "PENDING"
            print(f"⚠️ 이미지 분석 실패: {e}")
        
        # ✅ AI.ipynb와 동일한 응답 형식
        return AnalysisImageResponse(
            analysis_id=analysis_id,
            file_id=request.file_id,
            analysis_type="IMG",
            status=status,
            result_data=analysis_text,
            created_at=created_at
        )
    
    @staticmethod
    def _encode_image(image_path: Path) -> str:
        """이미지를 base64로 인코딩"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    @staticmethod
    def _analyze_with_vision(image_base64: str, case_id: str) -> str:
        """GPT-4o Vision으로 이미지 분석"""
        
        # AI.ipynb의 이미지 분석 프롬프트
        system_prompt = """당신은 수사 보조 이미지 분석 담당자입니다.

제공된 이미지를 상세히 분석하여 다음 정보를 추출하십시오:

1. 이미지에 보이는 장소와 환경 (건물, 도로, 골목길, 주변 시설물 등)
2. 이미지에 등장하는 인물 (복장, 자세, 행동, 위치 등)
3. 이미지에 보이는 물체 (차량, 물건, 증거물 등)
4. 시간대 및 날씨 추정 (그림자, 조명, 날씨 등)
5. 사건과의 관련성 (공간적, 시간적 맥락)

절대 규칙:
- 이미지에 보이는 객관적 사실만 기술
- 추정은 명확히 '~으로 보입니다'로 표현
- 이미지에 없는 내용 추가 금지
- 법적 판단이나 결론 금지
- 자연스러운 설명문으로 작성 (8~12문장)"""

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_VISION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "이 이미지를 상세히 분석해주세요."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"⚠️ Vision API 호출 실패: {e}")
            return f"이미지 분석 실패: {str(e)}"