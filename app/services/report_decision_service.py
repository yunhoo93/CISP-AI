# app/services/report_decision_service.py

import json
from datetime import datetime
from openai import OpenAI
from app.config import settings
from app.models.report_decision_schema import (
    ReportDecisionRequest,
    ReportDecisionResponse
)
from app.services.report_storage_service import ReportStorageService

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ReportDecisionService:
    """
    최종결정서 생성 서비스
    
    사용자가 선택한 decision_type을 기준으로 결정서 작성
    (AI 추천과 다를 수 있음)
    """
    
    @staticmethod
    def generate_decision_report(request: ReportDecisionRequest) -> ReportDecisionResponse:
        """
        최종결정서 생성 + 자동 저장
        
        - 사용자 판단(decision_type)을 우선으로 적용
        - AI 추천과 다를 경우 그 사유도 포함
        - 자동으로 저장
        """
        print("\n" + "=" * 70)
        print("⚖️ 최종결정서 생성")
        print("=" * 70)
        print(f"사건: {request.case_detail.title}")
        print(f"사용자 판단: {request.decision_type}")
        print(f"AI 추천: {request.final_analysis.recommended_decision}")
        
        # 판단 일치 여부 확인
        is_different = (request.decision_type != request.final_analysis.recommended_decision)
        if is_different:
            print(f"⚠️ 사용자 판단과 AI 추천이 다릅니다!")
        
        # 프롬프트 구성
        prompt = ReportDecisionService._build_prompt(request, is_different)
        
        # GPT-4o로 결정서 생성
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 경찰 최종결정서 작성 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱
            import re
            result_text = re.sub(r"```json|```", "", result_text).strip()
            result = json.loads(result_text)
            
            title = result.get("title", "")
            content = result.get("content", {})
            
            # 자동 저장
            saved_report = ReportStorageService.save_report(
                report_type="DECISION",
                case_id=request.final_analysis.case_id,
                title=title,
                content=content
            )
            
            print("=" * 70)
            print(f"✅ 최종결정서 생성 및 저장 완료")
            print("=" * 70)
            
            return ReportDecisionResponse(
                report_id=saved_report["report_id"],
                case_id=saved_report["case_id"],
                report_type=saved_report["report_type"],
                title=saved_report["title"],
                content=saved_report["content"],
                pdf_path=saved_report["pdf_path"],  # ✅ 추가
                created_at=saved_report["created_at"]
            )
        
        except Exception as e:
            print(f"⚠️ 최종결정서 생성 실패: {e}")
            
            # 오류 시에도 저장 시도
            error_content = {
                "오류": f"자동 생성 실패: {str(e)}",
                "수동작성필요": "true"
            }
            
            saved_report = ReportStorageService.save_report(
                report_type="DECISION",
                case_id=request.final_analysis.case_id,
                title=f"{request.case_detail.title} 최종결정서",
                content=error_content
            )
            
            return ReportDecisionResponse(
                report_id=saved_report["report_id"],
                case_id=saved_report["case_id"],
                report_type=saved_report["report_type"],
                title=saved_report["title"],
                content=saved_report["content"],
                pdf_path=saved_report["pdf_path"],  # ✅ 추가
                created_at=saved_report["created_at"]
            )
    
    @staticmethod
    def _build_prompt(request: ReportDecisionRequest, is_different: bool) -> str:
        """최종결정서 생성 프롬프트 구성"""
        
        # 판단 한글 변환
        decision_map = {
            "TRANSFER": "송치",
            "NON_TRANSFER": "불송치",
            "SUSPENSION": "수사중지"
        }
        user_decision_kr = decision_map.get(request.decision_type, request.decision_type)
        ai_decision_kr = decision_map.get(
            request.final_analysis.recommended_decision,
            request.final_analysis.recommended_decision
        )
        
        # 판단 불일치 시 추가 안내
        decision_note = ""
        if is_different:
            decision_note = f"""
**중요: 사용자 판단과 AI 추천 불일치**
- AI 추천: {ai_decision_kr}
- 사용자 판단: {user_decision_kr} ← 이것을 기준으로 작성
- 결정서에 판단 변경 사유를 포함하십시오.
"""
        
        prompt = f"""다음 정보를 바탕으로 최종결정서를 작성하십시오.

**사건 정보:**
사건명: {request.case_detail.title}
사건유형: {request.case_detail.type}
사건상태: {request.case_detail.status}
발생일시: {request.case_detail.occurred_at}
발생장소: {request.case_detail.location}
사건개요: {request.case_detail.description}

**사건 요약:**
{json.dumps(request.case_detail.summary.model_dump(by_alias=True), ensure_ascii=False, indent=2)}

**최종 판단:**
사용자 결정: {user_decision_kr}

{decision_note}

**분석 결과 (참고):**
사건 판단 요약:
{request.final_analysis.decision_summary}

법리 판단 요약:
{request.final_analysis.legal_issue_summary}

증거 충분성 요약:
{request.final_analysis.evidence_sufficiency_summary}

잔여 리스크 요약:
{request.final_analysis.remaining_risk_summary}

**최종결정서 작성 기준:**
1. 결정 주문: 최종 결정 내용 (송치/불송치/수사중지)
2. 사건 개요: 사건의 기본 정보
3. 판단 이유: 해당 결정에 이른 구체적 근거
4. 증거 평가: 확보된 증거에 대한 평가
5. 법리 검토: 법적 판단 근거
6. 결론: 최종 의견 및 조치사항

**출력 형식 (JSON만 출력):**
{{
  "title": "{user_decision_kr} 결정서",
  "content": {{
    "문서번호": "결정-2026-00001",
    "결정일자": "{datetime.now().strftime('%Y년 %m월 %d일')}",
    "사건명": "{request.case_detail.title}",
    "피의자": "미상",
    
    "주문": "{user_decision_kr} 결정함",
    
    "1. 사건 개요": {{
      "발생일시": "{request.case_detail.occurred_at}",
      "발생장소": "{request.case_detail.location}",
      "사건경위": "사건 요약 내용을 서술형으로 재구성 (5-7문장)"
    }},
    
    "2. 판단 이유": {{
      "핵심 판단": "{user_decision_kr} 결정의 핵심 근거 (3-5문장)",
      "세부 사유": "구체적인 판단 이유 (7-10문장)",
      {'"판단 변경 사유": "AI 추천과 다른 이유 (해당시에만)"' if is_different else ''}
    }},
    
    "3. 증거 평가": {{
      "확보 증거": "증거 목록 및 내용",
      "증거 가치": "각 증거의 증명력 평가",
      "종합 평가": "증거 충분성에 대한 최종 판단"
    }},
    
    "4. 법리 검토": {{
      "적용 법조": "관련 법률 조항",
      "구성요건": "범죄 구성요건 충족 여부",
      "법리 판단": "법적 판단 근거 및 결론"
    }},
    
    "5. 결론": {{
      "최종 의견": "{user_decision_kr}",
      "조치사항": "후속 조치 또는 유의사항",
      "비고": "기타 참고사항"
    }}
  }}
}}

**작성 원칙:**
- 사용자 판단({user_decision_kr})을 확고히 뒷받침하는 논리 전개
- 공문서 형식 및 법률 용어 정확히 사용
- 객관적이고 설득력 있는 근거 제시
- 판단과 근거의 명확한 연결
{f"- AI 추천({ai_decision_kr})과 다른 이유를 명확히 설명" if is_different else ""}
"""
        
        return prompt