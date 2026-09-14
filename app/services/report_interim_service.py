# app/services/report_interim_service.py

import json
from datetime import datetime
from openai import OpenAI
from app.config import settings
from app.models.report_interim_schema import (
    ReportInterimRequest,
    ReportInterimResponse
)
from app.services.report_storage_service import ReportStorageService

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ReportInterimService:
    """
    중간보고서 생성 서비스
    
    수사 활동 로그를 기반으로 중간보고서 작성
    """
    
    @staticmethod
    def generate_interim_report(request: ReportInterimRequest) -> ReportInterimResponse:
        """
        중간보고서 생성 + 자동 저장
        
        - 사건 정보와 활동 로그를 분석
        - GPT-4o로 중간보고서 작성
        - 자동으로 저장
        """
        print("\n" + "=" * 70)
        print("📄 중간보고서 생성")
        print("=" * 70)
        print(f"사건: {request.case_detail.title}")
        print(f"활동 로그: {len(request.selected_activity_logs)}건")
        
        # 활동 로그 통계
        activity_stats = {}
        for log in request.selected_activity_logs:
            key = f"{log.field}_{log.activity_type}"
            activity_stats[key] = activity_stats.get(key, 0) + 1
        
        print(f"활동 통계: {json.dumps(activity_stats, ensure_ascii=False)}")
        
        # 프롬프트 구성
        prompt = ReportInterimService._build_prompt(request)
        
        # GPT-4o로 보고서 생성
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 경찰 중간보고서 작성 전문가입니다."},
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
            
            title = result.get("title", "")
            content = result.get("content", {})
            
            # 자동 저장
            saved_report = ReportStorageService.save_report(
                report_type="INTERIM",
                case_id=request.case_detail.case_id,
                title=title,
                content=content
            )
            
            print("=" * 70)
            print(f"✅ 중간보고서 생성 및 저장 완료")
            print("=" * 70)
            
            return ReportInterimResponse(
                report_id=saved_report["report_id"],
                case_id=saved_report["case_id"],
                report_type=saved_report["report_type"],
                title=saved_report["title"],
                content=saved_report["content"],
                pdf_path=saved_report["pdf_path"],  # ✅ 추가
                created_at=saved_report["created_at"]
            )
        
        except Exception as e:
            print(f"⚠️ 중간보고서 생성 실패: {e}")
            
            # 오류 시에도 저장 시도
            error_content = {
                "오류": f"자동 생성 실패: {str(e)}",
                "수동작성필요": "true"
            }
            
            saved_report = ReportStorageService.save_report(
                report_type="INTERIM",
                case_id=request.case_detail.case_id,
                title=f"{request.case_detail.title} 중간보고서",
                content=error_content
            )
            
            return ReportInterimResponse(
                report_id=saved_report["report_id"],
                case_id=saved_report["case_id"],
                report_type=saved_report["report_type"],
                title=saved_report["title"],
                content=saved_report["content"],
                pdf_path=saved_report["pdf_path"],  # ✅ 추가
                created_at=saved_report["created_at"]
            )
    
    @staticmethod
    def _build_prompt(request: ReportInterimRequest) -> str:
        """중간보고서 생성 프롬프트 구성"""
        
        # 활동 로그를 시간순으로 정리
        logs_by_time = sorted(
            request.selected_activity_logs,
            key=lambda x: x.created_at
        )
        
        # 활동 로그를 카테고리별로 분류
        logs_by_field = {}
        for log in logs_by_time:
            if log.field not in logs_by_field:
                logs_by_field[log.field] = []
            logs_by_field[log.field].append({
                "activity_type": log.activity_type,
                "payload": log.payload,
                "created_at": log.created_at
            })
        
        prompt = f"""다음 수사 정보를 바탕으로 중간보고서를 작성하십시오.

**사건 정보:**
제목: {request.case_detail.title}
사건번호: {request.case_detail.case_id}
담당자: {request.case_detail.assignee_user_id}
사건유형: {request.case_detail.type}
발생일시: {request.case_detail.occurred_at}
발생장소: {request.case_detail.location}
사건개요: {request.case_detail.description}

**사건 요약:**
{json.dumps(request.case_detail.summary.model_dump(by_alias=True), ensure_ascii=False, indent=2)}

**수사 활동 내역 ({len(request.selected_activity_logs)}건):**
{json.dumps(logs_by_field, ensure_ascii=False, indent=2)}

**중간보고서 작성 기준:**
1. 사건 개요: 사건의 기본 정보 요약
2. 수사 경과: 활동 로그를 기반으로 수사 진행 상황 서술
3. 현재 상황: 현재까지 확보된 증거와 분석 결과
4. 향후 계획: 추가 수사 방향 및 필요 조치

**출력 형식 (JSON만 출력):**
{{
  "title": "사건명 중간보고서",
  "content": {{
    "1. 사건 개요": "사건의 기본 정보 (3-5문장)",
    "2. 수사 경과": "시간순 수사 활동 내역 (5-7문장)",
    "3. 현재 상황": {{
      "확보 증거": "증거 목록 및 분석 결과",
      "법리 검토": "법리 쟁점 및 판단 기준 검토 상황",
      "진행률": "전체 수사 진행률 (예: 60%)"
    }},
    "4. 향후 계획": "추가 수사 방향 및 예상 일정 (3-5문장)"
  }}
}}

**작성 원칙:**
- 객관적이고 명확한 서술
- 시간순 정리
- 구체적인 수치와 일자 포함
- 전문적인 용어 사용
"""
        
        return prompt