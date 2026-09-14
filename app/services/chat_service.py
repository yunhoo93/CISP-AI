# app/services/chat_service.py

from openai import OpenAI
from app.config import settings
from app.models.chat_schema import (
    ChatRequest,
    ChatResponse,
    UsedContext
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ChatService:
    """
    채팅 서비스
    사용자의 메시지에 대해 AI가 응답하며,
    필요시 분석 결과를 참조하여 답변
    """
    
    # 메모리 저장소 (대화 히스토리)
    _chat_history = []
    
    @staticmethod
    def chat(request: ChatRequest) -> ChatResponse:
        """
        채팅 처리
        
        - 사용자 메시지 수신
        - AI 응답 생성
        - 사용된 컨텍스트 정보 반환
        """
        print("\n" + "=" * 70)
        print(f"💬 채팅 요청: {request.role}")
        print(f"   - message: {request.message[:100]}...")
        print("=" * 70)
        
        # 대화 히스토리에 추가
        ChatService._chat_history.append({
            "role": request.role,
            "content": request.message
        })
        
        # 시스템 프롬프트
        system_prompt = """당신은 경찰 수사 보조 AI입니다.

사용자의 질문에 대해:
1. 분석 결과를 참조하여 답변
2. 법률 지식을 활용하여 설명
3. 명확하고 전문적인 답변 제공

규칙:
- 존댓말 사용
- 객관적이고 중립적인 태도
- 추측은 명확히 표시
- 법적 조언이 아님을 명시"""
        
        # GPT-4o로 응답 생성
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                *ChatService._chat_history[-10:]  # 최근 10개 대화만 유지
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_message = response.choices[0].message.content.strip()
            
            # 대화 히스토리에 AI 응답 추가
            ChatService._chat_history.append({
                "role": "assistant",
                "content": ai_message
            })
            
            # 사용된 컨텍스트 분석 (간단한 키워드 매칭)
            used_analysis_ids = []
            context_type = None
            
            # 메시지에서 분석 관련 키워드 감지
            message_lower = request.message.lower()
            
            if any(keyword in message_lower for keyword in ["문서", "압수물", "목록서", "서류"]):
                context_type = "DOC"
            elif any(keyword in message_lower for keyword in ["이미지", "사진", "영상", "cctv"]):
                context_type = "IMG"
            elif any(keyword in message_lower for keyword in ["전사", "음성", "녹취", "대화"]):
                context_type = "STT"
            elif any(keyword in message_lower for keyword in ["비디오", "동영상", "영상"]):
                context_type = "VDO"
            
            print(f"✅ AI 응답 생성 완료")
            print(f"   - used_context_type: {context_type}")
            print("=" * 70)
            
            return ChatResponse(
                message=ai_message,
                used_context=UsedContext(
                    analysis_ids=used_analysis_ids,
                    type=context_type
                )
            )
        
        except Exception as e:
            print(f"⚠️ 채팅 처리 실패: {e}")
            return ChatResponse(
                message=f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}",
                used_context=UsedContext(
                    analysis_ids=[],
                    type=None
                )
            )
    
    @staticmethod
    def clear_history():
        """대화 히스토리 초기화"""
        ChatService._chat_history.clear()
        print("💬 대화 히스토리 초기화 완료")