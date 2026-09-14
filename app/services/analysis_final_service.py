# app/services/analysis_final_service.py

import json
from openai import OpenAI
from app.config import settings
from app.models.analysis_final_schema import (
    AnalysisFinalRequest,
    AnalysisFinalResponse
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class AnalysisFinalService:
    """
    최종 수사 의견 생성 서비스
    
    모든 분석 결과를 종합하여:
    - 송치/불송치/수사중지 의견 제시
    - 사건 판단 요약
    - 법리 판단 요약
    - 증거 충분성 요약
    - 잔여 리스크 요약
    """
    
    @staticmethod
    def generate_final_analysis(request: AnalysisFinalRequest) -> AnalysisFinalResponse:
        """
        최종 수사 의견 생성
        
        모든 정보를 GPT-4o에 입력하여 종합 분석 수행
        """
        print("\n" + "=" * 70)
        print("📋 최종 수사 의견 생성")
        print("=" * 70)
        print(f"사건: {request.case_detail.title}")
        print(f"법리 기준: {len(request.legal_criteria)}개")
        print(f"분석 결과: {len(request.analysys)}개")
        print(f"채팅 로그: {len(request.chat_logs)}개")
        
        # 프롬프트 구성
        prompt = AnalysisFinalService._build_prompt(request)
        
        # GPT-4o로 최종 분석 생성
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 경찰 수사 종결 보고서 작성 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱
            import re
            result_text = re.sub(r"```json|```", "", result_text).strip()
            result = json.loads(result_text)
            
            print("=" * 70)
            print(f"✅ 최종 의견: {result.get('recommended_decision')}")
            print("=" * 70)
            
            return AnalysisFinalResponse(
                recommended_decision=result.get("recommended_decision", "NON_TRANSFER"),
                decision_summary=result.get("decision_summary", ""),
                legal_issues_summary=result.get("legal_issues_summary", ""),
                evidence_sufficiency_summary=result.get("evidence_sufficiency_summary", ""),
                remaining_risk_summary=result.get("remaining_risk_summary", "")
            )
        
        except Exception as e:
            print(f"⚠️ 최종 분석 생성 실패: {e}")
            
            # 오류 시 기본 응답
            return AnalysisFinalResponse(
                recommended_decision="SUSPENSION",
                decision_summary=f"최종 분석 생성 중 오류 발생: {str(e)}",
                legal_issues_summary="자동 생성 실패",
                evidence_sufficiency_summary="자동 생성 실패",
                remaining_risk_summary="자동 생성 실패. 수동 검토 필요."
            )
    
    @staticmethod
    def _build_prompt(request: AnalysisFinalRequest) -> str:
        """최종 분석 프롬프트 구성"""
        
        # 법리 기준 통계
        total_criteria = len(request.legal_criteria)
        insufficient_count = sum(
            1 for c in request.legal_criteria 
            if c.criteria_evaluation.status == "INSUFFICIENT"
        )
        met_count = sum(
            1 for c in request.legal_criteria 
            if c.criteria_evaluation.status == "MET"
        )
        not_met_count = sum(
            1 for c in request.legal_criteria 
            if c.criteria_evaluation.status == "NOT_MET"
        )
        
        # 분석 결과 통계
        total_analysis = len(request.analysys)
        analysis_types = {}
        for a in request.analysys:
            analysis_types[a.analysis_type] = analysis_types.get(a.analysis_type, 0) + 1
        
        # 법리 쟁점 정리
        legal_issues = {}
        for c in request.legal_criteria:
            issue_name = c.legal_issue.issue_name
            if issue_name not in legal_issues:
                legal_issues[issue_name] = {
                    "related_law": c.legal_issue.related_law,
                    "criteria": []
                }
            legal_issues[issue_name]["criteria"].append(c.criterion_text)
        
        prompt = f"""다음 수사 자료를 종합하여 최종 수사 의견을 작성하십시오.

**사건 정보:**
제목: {request.case_detail.title}
설명: {request.case_detail.description}
유형: {request.case_detail.type}
발생일시: {request.case_detail.occurred_at}
발생장소: {request.case_detail.location}

행위: {request.case_detail.summary.action}
대상: {request.case_detail.summary.object}
상호작용: {request.case_detail.summary.interaction}
장소: {request.case_detail.summary.place}
시간: {request.case_detail.summary.time}
결과: {request.case_detail.summary.result}

**법리 쟁점 ({len(legal_issues)}개):**
{json.dumps(legal_issues, ensure_ascii=False, indent=2)}

**증거 분석 결과 ({total_analysis}건):**
{json.dumps(analysis_types, ensure_ascii=False)}

**법리 기준 충족 평가 ({total_criteria}개):**
- INSUFFICIENT (불충분): {insufficient_count}건
- MET (충족): {met_count}건
- NOT_MET (미충족): {not_met_count}건

**출력 형식 (JSON만 출력):**
{{
  "recommended_decision": "TRANSFER|NON_TRANSFER|SUSPENSION",
  "decision_summary": "사건 판단 요약 (5-7문장)",
  "legal_issues_summary": "[법리 쟁점]\\n쟁점명\\n\\n[관련 법률]\\n법률명\\n\\n[구성요건]\\n기준1, 기준2...",
  "evidence_sufficiency_summary": "[증거 현황]\\n- 총 X건의 증거 분석 완료\\n- 증거 유형: Y가지\\n\\n[카테고리별 증거]\\n- 문서: Z건\\n\\n[평가]\\n평가 내용",
  "remaining_risk_summary": "[리스크 분석]\\n리스크 내용\\n\\n[불충분 항목]\\nX건의 법리 기준이 INSUFFICIENT 상태입니다."
}}

**판단 기준:**
- TRANSFER (송치): MET 기준이 과반수이고 핵심 증거가 충분한 경우
- NON_TRANSFER (불송치): INSUFFICIENT 또는 NOT_MET 기준이 과반수이거나 범죄 구성요건 미충족
- SUSPENSION (수사중지): 증거가 전혀 없거나 추가 수사가 불가능한 경우
"""
        
        return prompt