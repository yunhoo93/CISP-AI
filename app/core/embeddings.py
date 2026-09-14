# app/core/embeddings.py

import json
import pickle
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import pdfplumber
import torch
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# 전역 변수
CRIMINAL_LAW_RAG = None
PRECEDENT_INDEX = None


# ============================================================
# 법제처 API 함수
# ============================================================

def parse_precedent_xml(xml_text: str) -> Dict[str, Any]:
    """법제처 판례 XML 파싱"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"raw": xml_text, "precedent_decision_date": None}

    def get_text(tag):
        elem = root.find(f".//{tag}")
        return elem.text.strip() if elem is not None and elem.text else ""

    # 선고일자 파싱
    date_elem = root.find(".//선고일자")
    if date_elem is not None and date_elem.text:
        raw = date_elem.text.strip()
        if len(raw) == 8:
            precedent_decision_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        else:
            precedent_decision_date = raw
    else:
        precedent_decision_date = None

    return {
        "판시사항": get_text("판시사항"),
        "판결요지": get_text("판결요지"),
        "참조조문": get_text("참조조문"),
        "참조판례": get_text("참조판례"),
        "판례내용": get_text("판례내용"),
        "precedent_decision_date": precedent_decision_date
    }


# app/core/embeddings.py

def fetch_precedent_from_law_api(case_id: str) -> Dict[str, Any]:
    """법제처 API로 판례 전문 조회 (UTF-8 인코딩 수정)"""
    if not settings.LAW_API_KEY:
        print(f"⚠️ LAW_API_KEY 없음")
        return {"precedent_decision_date": None}
    
    case_id = int(case_id)
    cmd = [
        "curl", "-sS",
        "-H", "User-Agent: Mozilla/5.0",
        f"https://www.law.go.kr/DRF/lawService.do?OC={settings.LAW_API_KEY}&target=prec&type=XML&ID={case_id}"
    ]

    try:
        # ✅ 수정: encoding='utf-8' 명시 + errors='ignore'
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            encoding='utf-8',  # UTF-8로 명시
            errors='ignore',   # 디코딩 오류 무시
            timeout=30
        )
        return parse_precedent_xml(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"⚠️ API 타임아웃 (case_id={case_id})")
        return {"precedent_decision_date": None}
    except Exception as e:
        print(f"⚠️ API 호출 실패: {e}")
        return {"precedent_decision_date": None}


# ============================================================
# 형법 RAG 시스템
# ============================================================

class CriminalLawRAG:
    """형법 PDF RAG 시스템"""
    
    def __init__(self):
        self.chunks = []
        self.embeddings = []

    def load_and_chunk_pdf(self, pdf_path: Path) -> List[Dict[str, str]]:
        """형법 PDF를 조항 단위로 청크 분할"""
        print("📚 형법 PDF 로드 중...")
        
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        print(f"✅ PDF 로드 완료 ({len(full_text):,}자)")
        
        chunks = self._split_by_articles(full_text)
        print(f"✅ {len(chunks)}개 청크로 분할")
        
        return chunks

    def _split_by_articles(self, text: str) -> List[Dict[str, str]]:
        """조항 단위로 분할"""
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_article = "서론"

        for line in lines:
            if line.strip().startswith("제") and "조" in line[:10]:
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    if len(chunk_text.strip()) > 20:
                        chunks.append({
                            "article": current_article,
                            "text": chunk_text.strip()
                        })
                
                current_article = line.strip()[:20]
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            if len(chunk_text.strip()) > 20:
                chunks.append({
                    "article": current_article,
                    "text": chunk_text.strip()
                })

        return chunks

    def create_embeddings(self, chunks: List[Dict[str, str]]) -> List[List[float]]:
        """OpenAI 임베딩 생성 (형법용)"""
        print("🔢 임베딩 생성 중...")
        embeddings = []
        
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_texts = [chunk["text"] for chunk in batch]
            
            response = client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=batch_texts
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            print(f"   배치 {i//batch_size + 1} 완료...")
        
        print(f"✅ {len(embeddings)}개 임베딩 생성 완료")
        return embeddings

    def build_index(self, pdf_path: Path):
        """RAG 인덱스 구축"""
        self.chunks = self.load_and_chunk_pdf(pdf_path)
        self.embeddings = self.create_embeddings(self.chunks)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """유사 조문 검색"""
        query_response = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=[query]
        )
        query_embedding = query_response.data[0].embedding
        
        similarities = []
        for idx, chunk_embedding in enumerate(self.embeddings):
            similarity = self._cosine_similarity(query_embedding, chunk_embedding)
            similarities.append((idx, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, similarity in similarities[:top_k]:
            results.append({
                "article": self.chunks[idx]["article"],
                "text": self.chunks[idx]["text"],
                "similarity": similarity
            })
        
        return results

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def save_index(self, save_path: Path):
        """인덱스 저장"""
        data = {"chunks": self.chunks, "embeddings": self.embeddings}
        with open(save_path, "wb") as f:
            pickle.dump(data, f)
        print(f"💾 RAG 인덱스 저장: {save_path}")

    def load_index(self, load_path: Path):
        """인덱스 로드"""
        print(f"📂 RAG 인덱스 로드: {load_path}")
        with open(load_path, "rb") as f:
            data = pickle.load(f)
        self.chunks = data["chunks"]
        self.embeddings = data["embeddings"]
        print(f"✅ RAG 인덱스 로드 완료 ({len(self.chunks)}개 청크)")


# ============================================================
# 판례 임베딩 시스템 (KR-SBERT)
# ============================================================

class PrecedentIndex:
    """판례 임베딩 검색 시스템 (KR-SBERT)"""
    
    def __init__(self):
        print(f"🤖 KR-SBERT 모델 로드 중: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.pool_df = None
        self.embeddings = None

    def load_precedent_csv(self, csv_path: Path):
        """판례목록.csv 로드"""
        df = pd.read_csv(
            csv_path,
            sep=",",
            skiprows=1,
            header=None,
            encoding="utf-8"
        )
        
        df.columns = [
            '순번', "precedent_id", "title", "법원",
            '사건 유형', '판결 유형', "선고일자"
        ]
        
        # 형사 판례만 필터링
        pool_df = df[df["판결 유형"] == "형사"].reset_index(drop=True)
        
        print(f"✅ 총 판례: {len(df):,} / 형사 판례: {len(pool_df):,}")
        
        self.pool_df = pool_df

    def build_embeddings(self):
        """판례 제목 임베딩 생성 (KR-SBERT)"""
        titles = self.pool_df["title"].astype(str).tolist()
        print("📊 판례 제목 임베딩 생성 중 (KR-SBERT)...")
        self.embeddings = self.model.encode(
            titles,
            convert_to_tensor=True,
            show_progress_bar=True
        )

    def save_cache(self, cache_path: Path):
        """임베딩 캐시 저장"""
        torch.save({
            "embeddings": self.embeddings,
            "pool_df": self.pool_df
        }, cache_path)
        print(f"💾 판례 임베딩 캐시 저장: {cache_path}")

    def load_cache(self, cache_path: Path):
        """임베딩 캐시 로드"""
        data = torch.load(cache_path, weights_only=False)
        self.embeddings = data["embeddings"]
        self.pool_df = data["pool_df"]
        print("✅ 판례 임베딩 캐시 로드 완료")

    def init_index(self, csv_path: Path, cache_path: Path):
        """판례 인덱스 초기화"""
        if cache_path.exists():
            print("✅ 기존 판례 임베딩 캐시 발견")
            self.load_cache(cache_path)
        else:
            print("⚠️ 판례 임베딩 없음 → 새로 생성")
            self.load_precedent_csv(csv_path)
            self.build_embeddings()
            self.save_cache(cache_path)

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """유사 판례 검색"""
        query_vec = self.model.encode(query, convert_to_tensor=True)
        similarities = torch.nn.functional.cosine_similarity(
            query_vec, self.embeddings
        )
        
        top_indices = similarities.topk(top_k).indices.tolist()
        
        results = []
        for idx in top_indices:
            row = self.pool_df.iloc[idx]
            results.append({
                "precedent_id": str(row["precedent_id"]),
                "title": row["title"],
                "court": row["법원"],
                "decision_date": row["선고일자"],
                "similarity": float(similarities[idx])
            })
        return results


# ============================================================
# 초기화 함수
# ============================================================

def initialize_embeddings():
    """임베딩 시스템 초기화"""
    global CRIMINAL_LAW_RAG, PRECEDENT_INDEX
    
    print("\n" + "=" * 70)
    print("🔄 임베딩 초기화 시작")
    print("=" * 70)
    
    # 1. 형법 RAG
    print("\n📚 형법 RAG 시스템 초기화")
    CRIMINAL_LAW_RAG = CriminalLawRAG()
    
    if settings.RAG_INDEX_PATH.exists():
        print("✅ 기존 RAG 인덱스 발견")
        CRIMINAL_LAW_RAG.load_index(settings.RAG_INDEX_PATH)
    else:
        if settings.CRIMINAL_LAW_PDF.exists():
            print("⚠️ RAG 인덱스 없음 → 새로 구축")
            CRIMINAL_LAW_RAG.build_index(settings.CRIMINAL_LAW_PDF)
            CRIMINAL_LAW_RAG.save_index(settings.RAG_INDEX_PATH)
        else:
            print(f"❌ 형법 PDF 없음: {settings.CRIMINAL_LAW_PDF}")
    
    # 2. 판례 임베딩
    print("\n📊 판례 임베딩 시스템 초기화")
    if settings.PRECEDENT_CSV.exists():
        PRECEDENT_INDEX = PrecedentIndex()
        PRECEDENT_INDEX.init_index(
            settings.PRECEDENT_CSV,
            settings.PRECEDENT_CACHE_PATH
        )
    else:
        print(f"❌ 판례 CSV 없음: {settings.PRECEDENT_CSV}")
        PRECEDENT_INDEX = None
    
    print("=" * 70)
    print("✅ 임베딩 초기화 완료")
    print("=" * 70 + "\n")


def get_criminal_law_rag():
    """형법 RAG 반환"""
    return CRIMINAL_LAW_RAG


def get_precedent_index():
    """판례 인덱스 반환"""
    return PRECEDENT_INDEX