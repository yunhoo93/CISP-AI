"""
research/extraction_ft/refresh_teacher_labels.py

case_service.py 프롬프트를 패치한 뒤, 이미 만들어둔 train.jsonl + eval.jsonl의
'text'는 그대로 두고 'teacher_pred'만 패치된 프롬프트로 다시 뽑아 덮어쓴다.
generate_teacher_data.py를 처음부터 다시 돌리는 것보다 훨씬 싸고 빠르다 —
가장 오래 걸리는 생성 단계를 건너뛰고 추출만 다시 하기 때문이다.

왜 필요한가:
  LoRA 학습 타깃은 gold가 아니라 teacher_pred여야 한다. gold는 field_pools.py의
  좁은 값 집합(예: object는 전체 15종류뿐)이라, 이걸 그대로 학습 타깃으로 쓰면
  모델이 실제 문서를 읽는 대신 몇 개 안 되는 고정 문구를 암기하게 된다.
  teacher_pred는 GPT-4o가 자연스럽게 낸 다양한 표현이라 학습 타깃으로 적합하다.
  그런데 지금 저장된 teacher_pred는 프롬프트 패치 이전(예: 사기 사건 object를
  "금전"으로 추측하던 버전)에 뽑힌 값이라, 이대로 학습하면 방금 고친 버그를
  1.5B 모델에 그대로 복사해 넣게 된다.

실행 (레포 루트에 .env 있는 상태에서):
  cd research/extraction_ft
  python refresh_teacher_labels.py
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from field_pools import FIELDS  # noqa: E402
from metrics import score_case, aggregate  # noqa: E402
from generate_teacher_data import RealClient, retry, run_stage, FatalAPIError  # noqa: E402


def load_records(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def dump_jsonl(path: Path, rows: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def refresh(records: List[dict], ext_fn: Callable, max_workers: int, desc: str) -> Tuple[List[dict], int]:
    """records의 text만 뽑아 추출을 다시 돌리고, teacher_pred를 새 값으로 교체한다.
    추출 실패나 '6개 전부 미상'(API 실패가 위장됐을 가능성)인 건은 제외한다."""
    texts = [r["text"] for r in records]
    results = run_stage(ext_fn, texts, max_workers, desc)

    out, dropped = [], 0
    for r, pred in zip(records, results):
        if not isinstance(pred, dict) or sum(1 for v in pred.values() if v == "미상") == len(FIELDS):
            dropped += 1
            continue
        new_r = dict(r)
        new_r["teacher_pred"] = pred
        out.append(new_r)
    return out, dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", type=str, default=str(Path(__file__).resolve().parent / "data"))
    ap.add_argument("--model", type=str, default="gpt-4o")
    ap.add_argument("--max_workers", type=int, default=8)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    train = load_records(data_dir / "train.jsonl")
    eval_ = load_records(data_dir / "eval.jsonl")
    print(f"불러옴: train {len(train)}건, eval {len(eval_)}건 (text는 그대로 재사용)")

    client = RealClient(args.model)
    ext_fn = retry(client.extract_fields)

    try:
        new_train, dropped_train = refresh(train, ext_fn, args.max_workers, "train teacher_pred 갱신")
        new_eval, dropped_eval = refresh(eval_, ext_fn, args.max_workers, "eval teacher_pred 갱신")
    except FatalAPIError as e:
        print(f"\n중단: {e}")
        print("크레딧을 채운 뒤 다시 실행하세요: https://platform.openai.com/settings/organization/billing")
        sys.exit(1)

    print(f"\ntrain: {len(train)} -> {len(new_train)}건 (제외 {dropped_train}건)")
    print(f"eval:  {len(eval_)} -> {len(new_eval)}건 (제외 {dropped_eval}건)")

    old_baseline = data_dir / "baseline_metrics.json"
    if old_baseline.exists():
        old_baseline.replace(data_dir / "baseline_metrics_prepatch.json")
        print("기존 baseline_metrics.json -> baseline_metrics_prepatch.json 로 보존 (패치 전/후 비교용)")

    dump_jsonl(data_dir / "train.jsonl", new_train)
    dump_jsonl(data_dir / "eval.jsonl", new_eval)

    eval_scores = [score_case(r["gold"], r["teacher_pred"]) for r in new_eval]
    new_baseline = aggregate(eval_scores)
    with open(data_dir / "baseline_metrics.json", "w", encoding="utf-8") as f:
        json.dump(new_baseline, f, ensure_ascii=False, indent=2)

    print("\n=== 패치 후 baseline (eval 기준, 학습 시 LoRA 모델과 비교할 숫자) ===")
    for k, v in sorted(new_baseline.items()):
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")


if __name__ == "__main__":
    main()