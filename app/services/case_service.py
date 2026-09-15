# app/services/case_service.py

import json
import uuid
from datetime import datetime, timezone
from openai import OpenAI
from app.config import settings
from app.models.case_schema import CaseRequest, CaseResponse, CaseSummary

client = OpenAI(api_key=settings.OPENAI_API_KEY)

UNKNOWN = "미상"


def utc_now_iso() -> str:
    """현재 UTC 시간을 ISO 8601 형식으로 반환"""
    return datetime.now(timezone.utc).isoformat()


class CaseService:
    @staticmethod
    def generate_case_summary(case_description: str) -> dict:
        """
        사건 내용을 6가지 요소로 구조화
        AI.ipynb의 generate_case_summary() 함수 이식
        """
        system_prompt = """당신은 사건 분석 전문가입니다.

입력된 사건 내용을 다음 6가지 요소로 구조화하십시오:

1. action: 행위 (예: 강탈, 절도, 폭행)
2. object: 대상/객체 (예: 스마트폰, 현금, 귀금속)
3. interaction: 상호작용 방식 (예: 물리적 접촉, 대면, 비대면, 협박)
4. place: 장소 (예: 서울시 주택가 골목길)
5. time: 시간 (예: 낮 시간대, 오후 2시경, 야간)
6. result: 결과 (예: 물품 탈취 성공, 도주, 미수)

각 항목은 간결하게 핵심만 추출하십시오.
사건 내용에서 확인할 수 없는 항목은 절대 임의로 추측하지 말고, "미상"으로 기재하십시오.
사건 유형상 흔히 나타나는 값이라도, 해당 사건 내용에 구체적으로 언급되지 않았다면 추측해서
채우지 마십시오 (예: 사기 사건이라고 해서 object를 임의로 "금전"이라 쓰지 마십시오).
구체적인 수단·경로가 명시되어 있다면 그 구체성을 유지하고, 상위 범주어로 뭉뚱그리지
마십시오 (예: "전화로 기망"을 "비대면"으로 축약하지 마십시오)."""
        # ✅ 수정: 3400건 실측 진단에서 확인된 두 가지 패턴에 대한 명시적 금지 추가
        # 1) 사건 유형(사기 등)의 통계적 개연성만으로 미상 필드를 채우는 경향 (object->"금전")
        # 2) 원문에 있는 구체적 수단·경로 정보를 상위 범주어로 뭉개는 경향 (전화->비대면)

        schema = {
            "name": "case_summary",
            "schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "object": {"type": "string"},
                    "interaction": {"type": "string"},
                    "place": {"type": "string"},
                    "time": {"type": "string"},
                    "result": {"type": "string"}
                },
                "required": ["action", "object", "interaction", "place", "time", "result"]
            }
        }

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"사건 내용:\n{case_description}"}
                ],
                temperature=0.0,  # ✅ 수정: 0.3 → 0.0 (문서화된 설계와 일치, 재현성 확보)
                response_format={"type": "json_schema", "json_schema": schema}
            )

            summary = json.loads(response.choices[0].message.content)
            return summary

        except Exception as e:
            print(f"⚠️ Summary 생성 실패: {e}")
            # ✅ 수정: 빈 문자열 대신 "미상" — 다운스트림(검색·평가 단계)에서
            # "값이 비어있음"과 "확인하지 못함"을 같은 의미로 다룰 수 있도록 통일
            return {
                "action": UNKNOWN,
                "object": UNKNOWN,
                "interaction": UNKNOWN,
                "place": UNKNOWN,
                "time": UNKNOWN,
                "result": UNKNOWN
            }

    @staticmethod
    def create_case(request: CaseRequest) -> CaseResponse:
        """
        CASE 생성 (Summary 포함)
        AI.ipynb의 CASE 생성 로직 이식
        """
        # Summary 생성
        summary_dict = CaseService.generate_case_summary(request.description)
        
        # CASE 객체 생성
        case_id = str(uuid.uuid4())
        now = utc_now_iso()
        
        case_response = CaseResponse(
            case_id=case_id,
            title=request.title,
            description=request.description,
            type=request.type,
            occurred_at=request.occurred_at,
            location=request.location,
            summary=CaseSummary(**summary_dict),
            status="OPEN",
            created_at=now,
            updated_at=now
        )
        
        print("\n" + "=" * 70)
        print("📋 CASE Summary 생성 (API 명세서 준수)")
        print("=" * 70)
        print(f"\n[API 응답]\n{json.dumps(summary_dict, ensure_ascii=False, indent=2)}")
        
        # ✅ 수정: model_dump()로 dict 변환 후 json.dumps() 사용
        print(f"\n[내부 CASE 객체]\n{json.dumps(case_response.model_dump(), ensure_ascii=False, indent=2)}")
        
        print("\n" + "=" * 70)
        print("✅ CASE 생성 완료")
        print("=" * 70)
        
        return case_response