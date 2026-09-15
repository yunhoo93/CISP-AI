"""
research/extraction_ft/field_pools.py

6필드(action/object/interaction/place/time/result) 합성 데이터 생성을 위한
사건 유형별 값 풀. 형법 조항은 CISP PDF Figure 4에 나온 매칭을 그대로 따름.
"""

from typing import Dict, List

CASE_TYPE_TO_ARTICLE: Dict[str, str] = {
    "절도": "형법 제329조",
    "강도": "형법 제333조",
    "폭행": "형법 제260조",
    "사기": "형법 제347조",
}

FIELDS: List[str] = ["action", "object", "interaction", "place", "time", "result"]

FIELD_POOLS: Dict[str, Dict[str, List[str]]] = {
    "절도": {
        "action": ["절도", "소매치기", "차량 부품 절취"],
        "object": ["스마트폰", "지갑", "자전거", "현금 20만원", "노트북", "금목걸이"],
        "interaction": ["비대면(부재중 침입)", "대면하지 않고 가져감", "손버릇을 이용한 소매치기"],
        "place": ["편의점 앞", "지하철역 승강장", "아파트 단지 주차장", "대학가 원룸촌 골목", "재래시장 노점"],
        "time": ["오전 시간대", "심야 시간대", "퇴근 시간대", "새벽 시간대"],
        "result": ["탈취 성공", "미수(발각되어 도주)", "일부 물품만 탈취"],
    },
    "강도": {
        "action": ["강도", "특수강도"],
        "object": ["현금", "가방 속 소지품", "매장 시재금", "스마트폰과 지갑"],
        "interaction": ["흉기 위협", "폭행을 동반한 위협", "다수인이 에워싸는 방식의 위협"],
        "place": ["주택가 골목길", "편의점 내부", "인적 드문 공원", "노상 ATM 앞"],
        "time": ["심야 시간대", "새벽 시간대", "인적이 드문 저녁 시간대"],
        "result": ["탈취 성공", "미수(저항으로 실패)", "일부 탈취 후 도주"],
    },
    "폭행": {
        "action": ["폭행", "협박"],
        "object": ["피해자 본인"],
        "interaction": ["물리적 접촉", "언어적 위협", "몸싸움(흉기 없음)"],
        "place": ["주점 앞 골목", "직장 사무실", "공동주택 복도", "지하철 내부"],
        "time": ["야간 시간대", "저녁 시간대", "점심시간대"],
        "result": ["경상 발생", "합의 시도", "신고 후 현행범 체포"],
    },
    "사기": {
        "action": ["사기", "보이스피싱", "투자사기"],
        "object": ["현금 500만원", "가상자산", "예금 전액", "물품대금"],
        "interaction": ["전화를 이용한 기망", "메신저를 통한 기망", "대면 계약을 이용한 기망"],
        "place": ["피해자 자택(비대면)", "카페에서의 대면 계약", "온라인 중고거래 플랫폼"],
        "time": ["평일 업무 시간대", "저녁 시간대", "주말 오전 시간대"],
        "result": ["편취 성공", "송금 직전 인지하여 미수", "일부 금액만 편취"],
    },
}

UNKNOWN_LABEL = "미상"
UNKNOWN_ALIASES = {"미상", "확인불가", "알 수 없음", "알수없음", "불명"}


def _validate_pools() -> None:
    for case_type, pools in FIELD_POOLS.items():
        missing = [f for f in FIELDS if f not in pools]
        if missing:
            raise ValueError(f"{case_type}: 누락된 필드 {missing}")
        empty = [f for f in FIELDS if not pools[f]]
        if empty:
            raise ValueError(f"{case_type}: 값이 비어있는 필드 {empty}")


_validate_pools()
