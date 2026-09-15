"""
research/extraction_ft/sampling.py

정답(gold) 6필드를 먼저 정하고, 텍스트는 나중에 GPT-4o가 쓰게 하는 방식의
샘플링 로직. 텍스트가 없는 상태에서 학습/평가 데이터를 동시에 만들기 위한
핵심 트릭 — 정답을 우리가 정하므로 eval set을 사람이 라벨링할 필요가 없다.
"""

import random
from dataclasses import dataclass
from typing import Dict, List

from field_pools import FIELD_POOLS, FIELDS, UNKNOWN_LABEL


@dataclass
class Task:
    case_id: str
    case_type: str
    gold: Dict[str, str]
    n_unknown: int


def sample_gold(case_type: str, n_unknown: int, rng: random.Random) -> Dict[str, str]:
    pools = FIELD_POOLS[case_type]
    gold = {f: rng.choice(pools[f]) for f in FIELDS}
    if n_unknown > 0:
        for f in rng.sample(FIELDS, k=n_unknown):
            gold[f] = UNKNOWN_LABEL
    return gold


def difficulty_plan(total: int, rng: random.Random) -> List[int]:
    """
    60%는 0개 미상(6필드 전부 명시), 30%는 1개 미상, 10%는 2개 미상.
    전부 명시된 쉬운 케이스만 있으면 모델이 '모른다고 말하기'를 배우지 못하므로
    의도적으로 미상 비율을 섞는다. 반올림 오차는 0개 미상 쪽에 흡수시킨다.
    """
    n2 = int(total * 0.10)
    n1 = int(total * 0.30)
    n0 = total - n1 - n2
    plan = [0] * n0 + [1] * n1 + [2] * n2
    rng.shuffle(plan)
    return plan


def build_task_plan(total: int, case_types: List[str], seed: int) -> List[Task]:
    rng = random.Random(seed)

    types_cycle = [case_types[i % len(case_types)] for i in range(total)]
    rng.shuffle(types_cycle)
    diffs = difficulty_plan(total, rng)

    tasks: List[Task] = []
    for i, (ctype, n_unk) in enumerate(zip(types_cycle, diffs)):
        gold = sample_gold(ctype, n_unk, rng)
        tasks.append(Task(case_id=f"syn-{i:05d}", case_type=ctype, gold=gold, n_unknown=n_unk))
    return tasks
