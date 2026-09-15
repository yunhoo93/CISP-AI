"""
research/extraction_ft/metrics.py

6필드 구조화 추출 결과를 채점하는 지표. GPT-4o baseline과 이후 LoRA 모델
평가에 동일하게 재사용한다.

- 필드별 Exact Match (정규화 후)
- 자유 서술형 필드(place/time)를 위한 음절 단위 F1 (완전일치보다 관대한 보조 지표)
- '미상' 탐지 recall / false-positive rate
  -> 이게 case_service.py에 넣은 환각 방지 지시가 실제로 작동하는지 확인하는 핵심 지표.
     recall만 보면 안 된다: 모델이 무조건 '미상'만 뱉어도 recall은 100%가 되므로
     반드시 false-positive rate와 같이 봐야 한다.
"""

import re
from typing import Dict, List

from field_pools import FIELDS, UNKNOWN_ALIASES


def normalize(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[.,!?~·・]", "", s)
    return s


def is_unknown(s: str) -> bool:
    return normalize(s) in UNKNOWN_ALIASES


def exact_match(pred: str, gold: str) -> bool:
    if is_unknown(gold):
        return is_unknown(pred)
    return normalize(pred) == normalize(gold)


def token_f1(pred: str, gold: str) -> float:
    """음절 단위 토큰 F1. 형태소 분석기 없이 쓸 수 있는 가벼운 근사치.
    나중에 여유가 되면 KR-SBERT 임베딩 코사인 유사도로 바꾸면 더 정확해진다."""
    if is_unknown(gold) or is_unknown(pred):
        return 1.0 if is_unknown(gold) == is_unknown(pred) else 0.0

    p_tokens = list(normalize(pred).replace(" ", ""))
    g_tokens = list(normalize(gold).replace(" ", ""))
    if not p_tokens or not g_tokens:
        return 0.0

    g_pool = list(g_tokens)
    overlap = 0
    for ch in p_tokens:
        if ch in g_pool:
            g_pool.remove(ch)
            overlap += 1
    if overlap == 0:
        return 0.0

    precision = overlap / len(p_tokens)
    recall = overlap / len(g_tokens)
    return 2 * precision * recall / (precision + recall)


def score_case(gold: Dict[str, str], pred: Dict[str, str]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for f in FIELDS:
        g, p = gold.get(f, ""), pred.get(f, "")
        result[f"{f}_em"] = float(exact_match(p, g))
        result[f"{f}_f1"] = token_f1(p, g)

    unk_fields = [f for f in FIELDS if is_unknown(gold.get(f, ""))]
    if unk_fields:
        hits = sum(1 for f in unk_fields if is_unknown(pred.get(f, "")))
        result["unknown_recall"] = hits / len(unk_fields)

    known_fields = [f for f in FIELDS if not is_unknown(gold.get(f, ""))]
    if known_fields:
        false_unknowns = sum(1 for f in known_fields if is_unknown(pred.get(f, "")))
        result["unknown_false_positive_rate"] = false_unknowns / len(known_fields)

    return result


def aggregate(scores: List[Dict[str, float]]) -> Dict[str, float]:
    if not scores:
        return {"n_cases": 0}
    keys = set()
    for s in scores:
        keys.update(s.keys())
    agg: Dict[str, float] = {}
    for k in sorted(keys):
        vals = [s[k] for s in scores if k in s]
        agg[k] = sum(vals) / len(vals) if vals else float("nan")
    agg["n_cases"] = float(len(scores))
    return agg
