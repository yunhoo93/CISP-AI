# app/services/analysis_callback_service.py

from typing import Dict, List, Any
from app.models.analysis_callback_schema import (
    AnalysisCallbackRequest,
    AnalysisCallbackResponse
)


class AnalysisCallbackService:
    """
    분석 콜백 처리 서비스
    AI 서버가 분석 단계별 결과를 전달하는 콜백 API
    """
    
    # 메모리 저장소 (실제 프로덕션에서는 DB 사용)
    # 구조: {case_id: {analysis_id: {stage: [data]}}}
    _callback_storage: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
    
    @staticmethod
    def handle_callback(
        case_id: str,
        analysis_id: str,
        request: AnalysisCallbackRequest
    ) -> AnalysisCallbackResponse:
        """
        분석 콜백 처리
        
        stage별로 다른 처리:
        - SUMMARY: 사건 요약 저장
        - TRANSCRIPT: 전사 내용 저장
        - KEY_STATEMENT: 핵심 진술 저장
        - CONTRADICTION: 모순점 저장
        - QUESTION: 질문 전략 저장
        - VIDEO_EVENT: 영상 이벤트 저장
        """
        stage = request.stage.upper()
        
        print("\n" + "=" * 70)
        print(f"📥 콜백 수신")
        print(f"   - case_id: {case_id}")
        print(f"   - analysis_id: {analysis_id}")
        print(f"   - stage: {stage}")
        print("=" * 70)
        
        # 저장소 초기화
        if case_id not in AnalysisCallbackService._callback_storage:
            AnalysisCallbackService._callback_storage[case_id] = {}
        
        if analysis_id not in AnalysisCallbackService._callback_storage[case_id]:
            AnalysisCallbackService._callback_storage[case_id][analysis_id] = {
                "SUMMARY": [],
                "TRANSCRIPT": [],
                "KEY_STATEMENT": [],
                "CONTRADICTION": [],
                "QUESTION": [],
                "VIDEO_EVENT": []
            }
        
        # stage별 처리
        if stage == "SUMMARY":
            AnalysisCallbackService._handle_summary(case_id, analysis_id, request.payload)
        
        elif stage == "TRANSCRIPT":
            AnalysisCallbackService._handle_transcript(case_id, analysis_id, request.payload)
        
        elif stage == "KEY_STATEMENT":
            AnalysisCallbackService._handle_key_statement(case_id, analysis_id, request.payload)
        
        elif stage == "CONTRADICTION":
            AnalysisCallbackService._handle_contradiction(case_id, analysis_id, request.payload)
        
        elif stage == "QUESTION":
            AnalysisCallbackService._handle_question(case_id, analysis_id, request.payload)
        
        elif stage == "VIDEO_EVENT":
            AnalysisCallbackService._handle_video_event(case_id, analysis_id, request.payload)
        
        else:
            print(f"⚠️ 알 수 없는 stage: {stage}")
        
        print("=" * 70)
        print(f"✅ 콜백 처리 완료: {stage}")
        print("=" * 70)
        
        return AnalysisCallbackResponse(message="Callback received")
    
    # ============================================================
    # Stage별 처리 메서드
    # ============================================================
    
    @staticmethod
    def _handle_summary(case_id: str, analysis_id: str, payload):
        """SUMMARY 처리"""
        # Pydantic 모델을 dict로 변환
        payload_dict = (
            payload.model_dump() if hasattr(payload, 'model_dump') 
            else dict(payload) if hasattr(payload, '__dict__') 
            else payload
        )
        
        print(f"📊 요약 저장:")
        print(f"   - summary: {payload_dict.get('summary', '')[:50]}...")
        print(f"   - confidence: {payload_dict.get('confidence', 0)}")
        print(f"   - keywords: {payload_dict.get('keywords', [])}")
        
        AnalysisCallbackService._callback_storage[case_id][analysis_id]["SUMMARY"].append(payload_dict)
    
    @staticmethod
    def _handle_transcript(case_id: str, analysis_id: str, payload):
        """TRANSCRIPT 처리"""
        # Pydantic 모델을 dict로 변환
        payload_dict = (
            payload.model_dump() if hasattr(payload, 'model_dump') 
            else dict(payload) if hasattr(payload, '__dict__') 
            else payload
        )
        
        content = payload_dict.get('content', '')
        print(f"📝 전사 내용 저장:")
        print(f"   - content: {content[:100]}...")
        
        AnalysisCallbackService._callback_storage[case_id][analysis_id]["TRANSCRIPT"].append(payload_dict)
    
    @staticmethod
    def _handle_key_statement(case_id: str, analysis_id: str, payload):
        """KEY_STATEMENT 처리"""
        statements = payload if isinstance(payload, list) else [payload]
        print(f"🔑 핵심 진술 저장: {len(statements)}개")
        
        statements_list = []
        for stmt in statements:
            # Pydantic 모델을 dict로 변환
            stmt_dict = (
                stmt.model_dump() if hasattr(stmt, 'model_dump') 
                else dict(stmt) if hasattr(stmt, '__dict__') 
                else stmt
            )
            print(f"   - [{stmt_dict.get('tempId')}] {stmt_dict.get('content', '')[:50]}...")
            statements_list.append(stmt_dict)
        
        AnalysisCallbackService._callback_storage[case_id][analysis_id]["KEY_STATEMENT"].extend(statements_list)
    
    @staticmethod
    def _handle_contradiction(case_id: str, analysis_id: str, payload):
        """CONTRADICTION 처리"""
        contradictions = payload if isinstance(payload, list) else [payload]
        print(f"⚠️ 모순점 저장: {len(contradictions)}개")
        
        contradictions_list = []
        for contra in contradictions:
            # Pydantic 모델을 dict로 변환
            contra_dict = (
                contra.model_dump() if hasattr(contra, 'model_dump') 
                else dict(contra) if hasattr(contra, '__dict__') 
                else contra
            )
            print(f"   - [{contra_dict.get('statementTempId')}] {contra_dict.get('description', '')}")
            contradictions_list.append(contra_dict)
        
        AnalysisCallbackService._callback_storage[case_id][analysis_id]["CONTRADICTION"].extend(contradictions_list)
    
    @staticmethod
    def _handle_question(case_id: str, analysis_id: str, payload):
        """QUESTION 처리"""
        questions = payload if isinstance(payload, list) else [payload]
        print(f"❓ 질문 전략 저장: {len(questions)}개")
        
        questions_list = []
        for q in questions:
            # Pydantic 모델을 dict로 변환
            q_dict = (
                q.model_dump() if hasattr(q, 'model_dump') 
                else dict(q) if hasattr(q, '__dict__') 
                else q
            )
            print(f"   - [{q_dict.get('statementTempId')}] {q_dict.get('question', '')}")
            questions_list.append(q_dict)
        
        AnalysisCallbackService._callback_storage[case_id][analysis_id]["QUESTION"].extend(questions_list)
    
    @staticmethod
    def _handle_video_event(case_id: str, analysis_id: str, payload):
        """VIDEO_EVENT 처리"""
        events = payload if isinstance(payload, list) else [payload]
        print(f"🎬 영상 이벤트 저장: {len(events)}개")
        
        events_list = []
        for event in events:
            # Pydantic 모델을 dict로 변환
            event_dict = (
                event.model_dump() if hasattr(event, 'model_dump') 
                else dict(event) if hasattr(event, '__dict__') 
                else event
            )
            print(f"   - [{event_dict.get('startTime')}-{event_dict.get('endTime')}s] {event_dict.get('eventType')}: {event_dict.get('description', '')}")
            events_list.append(event_dict)
        
        AnalysisCallbackService._callback_storage[case_id][analysis_id]["VIDEO_EVENT"].extend(events_list)
    
    # ============================================================
    # 조회 메서드
    # ============================================================
    
    @staticmethod
    def get_callbacks(case_id: str, analysis_id: str, stage: str = None) -> Any:
        """특정 분석의 콜백 데이터 조회"""
        if case_id not in AnalysisCallbackService._callback_storage:
            return []
        
        if analysis_id not in AnalysisCallbackService._callback_storage[case_id]:
            return []
        
        if stage:
            return AnalysisCallbackService._callback_storage[case_id][analysis_id].get(stage.upper(), [])
        else:
            return AnalysisCallbackService._callback_storage[case_id][analysis_id]
    
    @staticmethod
    def get_all_callbacks() -> Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]]:
        """모든 콜백 데이터 조회 (디버깅용)"""
        return AnalysisCallbackService._callback_storage