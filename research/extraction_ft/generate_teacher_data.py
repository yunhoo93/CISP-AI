"""
research/extraction_ft/generate_teacher_data.py

6필드 구조화 추출(action/object/interaction/place/time/result) 파인튜닝을 위한
synthetic teacher 데이터 생성 파이프라인.

흐름:
  1) gold JSON을 먼저 무작위로 정한다 (sampling.py)
  2) GPT-4o에게 그 gold를 반영한 사건 개요문을 쓰게 한다 (생성)
  3) 그 개요문을 app/services/case_service.py의 실제 추출 함수에 다시 넣어
     6필드를 뽑는다 (추출) -> 추출기는 gold를 보지 않으므로, gold와 비교하면
     GPT-4o 자체의 진짜 baseline EM/F1이 나온다
  4) 필터링 후 train/eval로 분리해 저장한다 (eval 정답은 사람이 라벨링할 필요 없음
     — 애초에 우리가 정답을 정했으므로)

실행 전에 반드시 app/services/case_service.py를 패치하세요:
  - temperature=0.3 -> 0.0
  - system_prompt에 "확인할 수 없는 항목은 '미상'으로 기재" 지시 추가
  - except 블록의 fallback을 빈 문자열 대신 "미상"으로
패치 전에 데이터를 생성하면 처음부터 다시 만들어야 합니다.

실행 (레포 루트에 app/.env 가 있는 상태에서):
  cd research/extraction_ft

  # 1) API 호출 없이 배선만 확인 (무료, 수 초)
  python generate_teacher_data.py --dry_run --n_train 20 --n_eval 5

  # 2) 실제로 소량만 만들어 눈으로 품질 확인 (강력 권장 - 전체 돌리기 전에 반드시)
  python generate_teacher_data.py --n_train 20 --n_eval 5

  # 3) 전체 규모
  python generate_teacher_data.py --n_train 3000 --n_eval 400
"""

import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List

from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parent            # research/extraction_ft
REPO_ROOT = Path(__file__).resolve().parents[2]          # app/ 이 보이는 레포 루트
sys.path.insert(0, str(SCRIPT_DIR))                      # field_pools, sampling, metrics
sys.path.insert(0, str(REPO_ROOT))                        # app.services.case_service

from field_pools import CASE_TYPE_TO_ARTICLE, FIELDS      # noqa: E402
from sampling import Task, build_task_plan                 # noqa: E402
from metrics import score_case, aggregate                  # noqa: E402


GEN_SYSTEM = """당신은 경찰 수사 사건 개요문을 작성하는 어시스턴트입니다.
아래 '정답 정보'를 반영해 자연스러운 사건 개요문(3~6문장)을 작성하세요.

규칙:
- '미상'으로 표시된 항목은 텍스트에서 절대 알 수 없게 하세요. 암시도 금지합니다.
- 나머지 항목은 항목명을 그대로 쓰지 말고, 실제 수사 기록처럼 문장에 자연스럽게 녹이세요.
- 문체는 '수사관 작성 사건 개요' 또는 '피해자 진술 녹취' 중 하나를 임의로 골라 일관되게 쓰세요.
- 사건 유형: {case_type} ({article})
"""

LEAK_MARKERS = ["미상", "확인불가", "알 수 없", "불명"]

# 크레딧 소진처럼 재시도해도 절대 성공하지 않는 오류의 신호.
# 이 문자열이 에러 메시지에 보이면 재시도 대기 없이 즉시 전체 실행을 중단한다.
QUOTA_ERROR_MARKERS = ["insufficient_quota", "credit_balance_exhausted"]


class FatalAPIError(Exception):
    """재시도로 해결되지 않는 오류. run_stage 전체를 즉시 중단시키는 용도."""


def is_fatal_quota_error(e: Exception) -> bool:
    msg = str(e)
    return any(m in msg for m in QUOTA_ERROR_MARKERS)


def build_gen_user_prompt(task: Task) -> str:
    lines = [f"- {f}: {v}" for f, v in task.gold.items()]
    return "정답 정보:\n" + "\n".join(lines)


def looks_leaked(text: str, gold: Dict[str, str]) -> bool:
    """gold에 미상 필드가 있는데 텍스트에 '미상'류 단어가 그대로 등장하면
    생성 모델이 규칙을 어기고 힌트를 흘린 것으로 간주한다."""
    if not any(v == "미상" for v in gold.values()):
        return False
    return any(m in text for m in LEAK_MARKERS)


class RealClient:
    def __init__(self, model: str):
        from openai import OpenAI
        from app.config import settings

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)  # case_service.py와 동일한 방식
        self.model = model

    def generate_text(self, task: Task) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": GEN_SYSTEM.format(
                        case_type=task.case_type,
                        article=CASE_TYPE_TO_ARTICLE[task.case_type],
                    ),
                },
                {"role": "user", "content": build_gen_user_prompt(task)},
            ],
            temperature=0.9,
        )
        return resp.choices[0].message.content.strip()

    def extract_fields(self, text: str) -> Dict[str, str]:
        # 실제 프로덕션 함수를 그대로 재사용한다. 프롬프트를 여기 따로 복사해두면
        # case_service.py를 고칠 때마다 baseline이 몰래 낡은 채로 남는 문제가 생긴다.
        from app.services.case_service import CaseService

        return CaseService.generate_case_summary(text)


class MockClient:
    """--dry_run 용. API를 호출하지 않고 배선과 필터링 로직을 검증한다.
    실패/짧은텍스트/누출/전체미상 케이스를 일부러 섞어 모든 필터 경로를 건드린다."""

    def generate_text(self, task: Task) -> str:
        r = random.random()
        if r < 0.05:
            raise RuntimeError("mock generation failure")
        if r < 0.08:
            return "너무 짧음"
        if r < 0.11:
            return f"[MOCK] {task.case_type} 사건입니다. 시간은 미상입니다."
        return (
            f"[MOCK] {task.case_type} 사건 개요 예시 텍스트입니다. "
            f"case_id={task.case_id}. 충분한 길이를 확보하기 위한 문장을 덧붙입니다."
        )

    def extract_fields(self, text: str) -> Dict[str, str]:
        r = random.random()
        if r < 0.05:
            raise RuntimeError("mock extraction failure")
        if r < 0.08:
            return {f: "미상" for f in FIELDS}
        return {f: f"mock-{f}" for f in FIELDS}


def retry(fn: Callable, tries: int = 3, base_delay: float = 2.0) -> Callable:
    def wrapped(*args, **kwargs):
        last_err = None
        for attempt in range(tries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                if is_fatal_quota_error(e):
                    raise FatalAPIError(f"크레딧 소진: {e}") from e
                last_err = e
                time.sleep(base_delay * (2**attempt))
        raise last_err

    return wrapped


def run_stage(fn: Callable, items: List, max_workers: int, desc: str) -> List:
    results: List = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fn, item): i for i, item in enumerate(items)}
        for fut in tqdm(as_completed(futures), total=len(items), desc=desc):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except FatalAPIError as e:
                print(f"\n🛑 치명적 오류로 중단합니다: {e}")
                for pending in futures:
                    pending.cancel()  # 아직 시작 안 한 작업만 취소됨 (이미 실행 중인 건 어쩔 수 없음)
                raise
            except Exception as e:  # noqa: BLE001
                results[i] = e
    return results


def dump_jsonl(path: Path, rows: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_train", type=int, default=3000)
    ap.add_argument("--n_eval", type=int, default=400)
    ap.add_argument(
        "--oversample",
        type=float,
        default=1.15,
        help="필터링으로 빠질 것을 감안해 여유있게 더 생성하는 비율",
    )
    ap.add_argument("--model", type=str, default="gpt-4o", help="사건 개요문을 '쓰는' 모델. "
                     "6필드를 '추출'하는 모델은 항상 app/config.py의 OPENAI_MODEL을 따른다.")
    ap.add_argument("--max_workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out_dir", type=str, default=str(SCRIPT_DIR / "data"))
    ap.add_argument("--dry_run", action="store_true")
    args = ap.parse_args()

    random.seed(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_target = args.n_train + args.n_eval
    total_request = int(total_target * args.oversample)

    case_types = list(CASE_TYPE_TO_ARTICLE.keys())
    tasks = build_task_plan(total_request, case_types, seed=args.seed)

    client = MockClient() if args.dry_run else RealClient(args.model)
    gen_fn = client.generate_text if args.dry_run else retry(client.generate_text)
    ext_fn = client.extract_fields if args.dry_run else retry(client.extract_fields)

    try:
        texts = run_stage(gen_fn, tasks, args.max_workers, "사건 개요문 생성")

        gen_ok_idx = [i for i, t in enumerate(texts) if isinstance(t, str)]
        ext_inputs = [texts[i] for i in gen_ok_idx]
        ext_results = run_stage(ext_fn, ext_inputs, args.max_workers, "6필드 추출 (baseline 채점용)")
    except FatalAPIError as e:
        print(f"\n중단: {e}")
        print("크레딧을 채운 뒤 다시 실행하세요: https://platform.openai.com/settings/organization/billing")
        print("(재시도로 해결되는 오류가 아니라 바로 멈췄습니다. 지금까지의 API 호출 비용은")
        print(" 이미 청구된 상태이니, 다시 돌리기 전에 청구 대시보드에서 확인해보세요.)")
        sys.exit(1)

    preds_by_idx: Dict[int, Dict[str, str]] = {}
    for pos, i in enumerate(gen_ok_idx):
        preds_by_idx[i] = ext_results[pos]

    records, rejected, scores = [], [], []

    for i, task in enumerate(tasks):
        text = texts[i]
        if not isinstance(text, str):
            rejected.append({"case_id": task.case_id, "reason": f"generation_error: {text}"})
            continue
        if len(text) < 30:
            rejected.append({"case_id": task.case_id, "reason": "text_too_short"})
            continue
        if looks_leaked(text, task.gold):
            rejected.append({"case_id": task.case_id, "reason": "unknown_field_leaked"})
            continue

        pred = preds_by_idx.get(i)
        if not isinstance(pred, dict):
            rejected.append({"case_id": task.case_id, "reason": f"extraction_error: {pred}"})
            continue
        if sum(1 for v in pred.values() if v == "미상") == len(FIELDS):
            # 6개 전부 미상은 진짜 환각 방지가 작동한 게 아니라 API 실패가
            # case_service.py의 fallback으로 조용히 가려졌을 가능성이 높다.
            rejected.append({"case_id": task.case_id, "reason": "extraction_all_unknown_likely_api_failure"})
            continue

        case_score = score_case(task.gold, pred)
        scores.append(case_score)
        records.append(
            {
                "case_id": task.case_id,
                "case_type": task.case_type,
                "text": text,
                "gold": task.gold,
                "teacher_pred": pred,
            }
        )

    print(f"\n생성 시도 {len(tasks)}건 중 {len(records)}건 통과, {len(rejected)}건 제외")
    if rejected:
        reason_counts: Dict[str, int] = {}
        for r in rejected:
            key = r["reason"].split(":")[0]
            reason_counts[key] = reason_counts.get(key, 0) + 1
        for k, v in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"  - {k}: {v}건")

    baseline = aggregate(scores)
    with open(out_dir / "baseline_metrics.json", "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    print("\n=== GPT-4o Baseline (teacher 자체 추출 성능) ===")
    for k, v in baseline.items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    random.Random(args.seed).shuffle(records)
    eval_records = records[: args.n_eval]
    train_records = records[args.n_eval :]  # 남은 것 전부 train — 오버샘플로 더 통과한 것도 버리지 않음

    if len(eval_records) < args.n_eval or len(train_records) < args.n_train:
        print(
            f"⚠️ 목표에 못 미칩니다 (train {len(train_records)}/{args.n_train}, "
            f"eval {len(eval_records)}/{args.n_eval}). --oversample 값을 높여 다시 실행하세요."
        )
    elif len(train_records) > args.n_train:
        print(f"  (오버샘플로 {len(train_records) - args.n_train}건 더 통과해 전부 train에 포함했습니다)")

    dump_jsonl(out_dir / "train.jsonl", train_records)
    dump_jsonl(out_dir / "eval.jsonl", eval_records)
    dump_jsonl(out_dir / "rejected.jsonl", rejected)

    print(f"\n저장 완료: train={len(train_records)}건, eval={len(eval_records)}건 -> {out_dir}/")


if __name__ == "__main__":
    main()