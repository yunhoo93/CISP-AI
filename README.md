# AI 기반 수사 분석 시스템

## 구조

```
└── app/
   ├── main.py                  # FastAPI 진입점
   ├── config.py                # 환경변수 (LAW_API_KEY 포함)
   ├── core/                    # 임베딩, 벡터스토어
   ├── services/                # 비즈니스 로직 (14개)
   ├── models/                  # Pydantic 스키마 (14개)
   ├── routers/                 # API 엔드포인트 (14개)
   └── data/                    # 형법, 판례
```

## 실행

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## API 문서

http://localhost:8000/docs
