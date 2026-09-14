# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.core.embeddings import initialize_embeddings

# 라우터 임포트
from app.routers import (
    cases_router,
    legal_criteria_router,
    criteria_evaluation_router,
    investigation_files_router,
    analysis_document_router,
    analysis_image_router,
    analysis_media_router,
    analysis_callback_router,
    analysis_final_router,
    report_interim_router,
    report_final_router,
    report_decision_router,
    chat_router,
    reports_router,  # ✅ 추가
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    앱 시작/종료 이벤트 핸들러
    """
    # 시작 시: 임베딩 초기화
    print("\n" + "=" * 70)
    print("🚀 FastAPI 서버 시작")
    print("=" * 70)
    
    initialize_embeddings()
    
    print("\n" + "=" * 70)
    print("✅ 모든 초기화 완료")
    print("=" * 70 + "\n")
    
    yield
    
    # 종료 시
    print("\n" + "=" * 70)
    print("🛑 FastAPI 서버 종료")
    print("=" * 70 + "\n")


# FastAPI 앱 생성
app = FastAPI(
    title="경찰 사건 분석 AI 시스템",
    description="AI.ipynb를 FastAPI로 변환한 경찰 수사 분석 시스템",
    version="1.0.0",
    lifespan=lifespan
)


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록
app.include_router(cases_router)
app.include_router(legal_criteria_router)
app.include_router(criteria_evaluation_router)
app.include_router(investigation_files_router)
app.include_router(analysis_document_router)
app.include_router(analysis_image_router)
app.include_router(analysis_media_router)
app.include_router(analysis_callback_router)
app.include_router(analysis_final_router)
app.include_router(report_interim_router)
app.include_router(report_final_router)
app.include_router(report_decision_router)
app.include_router(chat_router)
app.include_router(reports_router)  # ✅ 추가


# 루트 엔드포인트
@app.get("/")
async def root():
    """
    API 상태 확인
    """
    return JSONResponse(content={
        "message": "경찰 사건 분석 AI 시스템",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "1. CASE": "POST /cases/summary",
            "2. LEGAL_CRITERIA": "POST /legal-criteria",
            "3. CRITERIA_EVALUATION": "POST /legal-criteria/evaluate",
            "4. ANALYSIS_DOC": "POST /analysis/doc",
            "5. ANALYSIS_IMG": "POST /analysis/img",
            "6. ANALYSIS_VDO": "POST /analysis/vdo",
            "7. ANALYSIS_STT": "POST /analysis/stt",
            "8. INVESTIGATE_FILE": "POST /analysis/upload",
            "9. CHAT_LOG": "POST /chat/respond",
            "10-15. CALLBACKS": "POST /cases/{case_id}/analysis/{analysis_id}/callback",
            "16. FINAL_ANALYSIS": "POST /analysis/final",
            "17. REPORTS": "POST /reports/interim-draft",
            "18. REPORT_A": "POST /reports/final-draft",
            "19. REPORT_B": "POST /reports/decision-draft"
        }
    })


@app.get("/health")
async def health_check():
    """
    헬스 체크
    """
    return JSONResponse(content={
        "status": "healthy",
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "gemini_configured": bool(settings.GOOGLE_API_KEY),
        "data_dir": str(settings.DATA_DIR),
        "reports_dir": str(settings.REPORTS_DIR)
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )