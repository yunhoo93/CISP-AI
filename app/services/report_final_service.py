# app/services/report_final_service.py

import json
from datetime import datetime
from openai import OpenAI
from app.config import settings
from app.models.report_final_schema import (
    ReportFinalRequest,
    ReportFinalResponse
)
from app.services.report_storage_service import ReportStorageService

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ReportFinalService:
    """
    최종보고서 생성 서비스
    
    최종 분석 결과를 바탕으로 송치의견서 작성
    """
    
    @staticmethod
    def generate_final_report(request: ReportFinalRequest) -> ReportFinalResponse:
        """
        최종보고서 생성 + 자동 저장
        
        - 사건 정보와 최종 분석 결과 통합
        - GPT-4o로 최종보고서 작성
        - 자동으로 저장
        """
        print("\n" + "=" * 70)
        print("📋 최종보고서 생성")
        print("=" * 70)
        print(f"사건: {request.case_detail.title}")
        print(f"송치의견: {request.final_analysis.recommended_decision}")
        
        # 프롬프트 구성
        prompt = ReportFinalService._build_prompt(request)
        
        # GPT-4o로 보고서 생성
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 경찰 송치의견서 작성 전문가입니다."},
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
                report_type="FINAL",
                case_id=request.final_analysis.case_id,
                title=title,
                content=content
            )
            
            print("=" * 70)
            print(f"✅ 최종보고서 생성 및 저장 완료")
            print("=" * 70)
            
            return ReportFinalResponse(
                report_id=saved_report["report_id"],
                case_id=saved_report["case_id"],
                report_type=saved_report["report_type"],
                title=saved_report["title"],
                content=saved_report["content"],
                pdf_path=saved_report["pdf_path"],  # ✅ 추가
                created_at=saved_report["created_at"]
            )
        
        except Exception as e:
            print(f"⚠️ 최종보고서 생성 실패: {e}")
            
            # 오류 시에도 저장 시도
            error_content = {
                "오류": f"자동 생성 실패: {str(e)}",
                "수동작성필요": "true"
            }
            
            saved_report = ReportStorageService.save_report(
                report_type="FINAL",
                case_id=request.final_analysis.case_id,
                title=f"{request.case_detail.title} 송치의견서",
                content=error_content
            )
            
            return ReportFinalResponse(
                report_id=saved_report["report_id"],
                case_id=saved_report["case_id"],
                report_type=saved_report["report_type"],
                title=saved_report["title"],
                content=saved_report["content"],
                pdf_path=saved_report["pdf_path"],  # ✅ 추가
                created_at=saved_report["created_at"]
            )
    
    @staticmethod
    def _build_prompt(request: ReportFinalRequest) -> str:
        """최종보고서 생성 프롬프트 구성"""
        
        # 송치의견 한글 변환
        decision_map = {
            "TRANSFER": "송치",
            "NON_TRANSFER": "불송치",
            "SUSPENSION": "수사중지"
        }
        decision_kr = decision_map.get(
            request.final_analysis.recommended_decision,
            request.final_analysis.recommended_decision
        )
        
        prompt = f"""다음 수사 결과를 바탕으로 송치의견서를 작성하십시오.

**사건 정보:**
사건번호: {request.case_detail.case_id}
사건명: {request.case_detail.title}
담당자: {request.case_detail.assignee_user_id}
사건유형: {request.case_detail.type}
사건상태: {request.case_detail.status}
발생일시: {request.case_detail.occurred_at}
발생장소: {request.case_detail.location}
사건개요: {request.case_detail.description}

**사건 요약:**
{json.dumps(request.case_detail.summary.model_dump(by_alias=True), ensure_ascii=False, indent=2)}

**최종 분석 결과:**
송치의견: {decision_kr}

사건 판단 요약:
{request.final_analysis.decision_summary}

법리 판단 요약:
{request.final_analysis.legal_issue_summary}

증거 충분성 요약:
{request.final_analysis.evidence_sufficiency_summary}

잔여 리스크 요약:
{request.final_analysis.remaining_risk_summary}

**송치의견서 작성 기준:**
1. 사건 개요: 사건의 기본 정보 및 경위
2. 수사 결과: 확보된 증거 및 분석 내용
3. 법리 검토: 적용 법조 및 구성요건 충족 여부
4. 송치 의견: 최종 판단 및 근거
5. 특이사항: 참고할 사항 (있는 경우)

**출력 형식 (JSON만 출력):**
{{
  "title": "{decision_kr} 의견서",
  "content": {{
    "문서번호": "자동생성 필요",
    "기안일자": "{datetime.now().strftime('%Y년 %m월 %d일')}",
    "사건명": "{request.case_detail.title}",
    "피의자": "미상",
    "죄명": "사건유형 기반 추정",
    
    "1. 사건 개요": {{
      "발생일시": "{request.case_detail.occurred_at}",
      "발생장소": "{request.case_detail.location}",
      "사건경위": "사건 요약 내용을 서술형으로 재구성 (5-7문장)"
    }},
    
    "2. 수사 결과": {{
      "확보 증거": "증거 충분성 요약 내용 기반",
      "분석 내용": "각 증거에 대한 분석 결과"
    }},
    
    "3. 법리 검토": {{
      "적용 법조": "법리 쟁점 요약에서 추출",
      "구성요건": "각 구성요건별 충족 여부",
      "종합 판단": "법리 판단 요약 내용"
    }},
    
    "4. 송치 의견": {{
      "의견": "{decision_kr}",
      "판단 근거": "사건 판단 요약 내용 (5-7문장)",
      "잔여 리스크": "잔여 리스크 요약 내용"
    }},
    
    "5. 특이사항": "특이사항이 있으면 기재, 없으면 '없음'"
  }}
}}

**작성 원칙:**
- 공문서 형식 준수
- 객관적이고 명확한 서술
- 법률 용어 정확히 사용
- 근거와 결론 명확히 구분
- 송치의견에 부합하는 논리적 전개
"""
        
        return prompt