# app/config.py

from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    HUGGINGFACEHUB_API_TOKEN: str = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
    LAW_API_KEY: str = os.getenv("LAW_API_KEY", "")  # ✅ 법제처 API 키
    
    # 프로젝트 경로
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    APP_DIR: Path = BASE_DIR / "app"
    
    # 데이터 경로
    DATA_DIR: Path = APP_DIR / "data"
    FONTS_DIR: Path = APP_DIR / "fonts"
    IMAGES_DIR: Path = APP_DIR / "images"
    EVIDENCE_DIR: Path = APP_DIR / "evidence"
    REPORTS_DIR: Path = APP_DIR / "reports"
    
    # AI 모델 설정
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_VISION_MODEL: str = "gpt-4o"
    GEMINI_MODEL: str = "gemini-1.5-pro"
    
    # 임베딩 설정 (✅ KR-SBERT 사용)
    EMBEDDING_MODEL: str = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # 형법 RAG용
    
    # 파일 경로
    CRIMINAL_LAW_PDF: Path = DATA_DIR / "criminal_law.pdf"
    PRECEDENT_CSV: Path = DATA_DIR / "판례목록.csv"  # ✅ CSV 파일
    RAG_INDEX_PATH: Path = DATA_DIR / "criminal_law_rag_index.pkl"
    PRECEDENT_CACHE_PATH: Path = DATA_DIR / "precedent_embeddings.pt"
    
    # PDF 설정
    POLICE_LOGO_PATH: Path = IMAGES_DIR / "police_logo.png"
    FONT_PATH: Path = FONTS_DIR / "malgun.ttc"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# 디렉토리 생성
for directory in [
    settings.DATA_DIR,
    settings.FONTS_DIR,
    settings.IMAGES_DIR,
    settings.EVIDENCE_DIR,
    settings.REPORTS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)