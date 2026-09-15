"""
research/extraction_ft/inspect_mismatches.py

train.jsonl + eval.jsonl을 다시 채점해서, EM이 0인 사례와 '미상'을 놓친
사례를 gold/pred 나란히 출력한다. baseline_metrics.json은 평균만 보여주므로,
실제로 뭐가 틀렸는지 눈으로 확인할 때 쓴다. API 호출 없이 로컬에서 즉시 실행된다.

실행:
  python inspect_mismatches.py
  python inspect_mismatches.py --fields action object
  python inspect_mismatches.py --max_show 15
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from field_pools import FIELDS   # noqa: E402
from metrics import score_case, aggregate  # noqa: E402


def load_records(paths):
    records = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            print(f"(건너뜀 — 없음: {p})")
            continue
        with open(p, encoding="utf-8") as f:
            records += [json.loads(line) for line in f]
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", default=["data/train.jsonl", "data/eval.jsonl"])
    ap.add_argument(
        "--fields",
        nargs="+",
        default=["interaction", "result"],
        help="EM=0 사례를 살펴볼 필드. 기본은 실전 첫 배치에서 가장 낮게 나온 두 필드.",
    )
    ap.add_argument("--max_show", type=int, default=8, help="필드당/항목당 최대 출력 건수")
    args = ap.parse_args()

    records = load_records(args.files)
    if not records:
        print("레코드를 못 찾았습니다. --files 로 경로를 확인하세요.")
        return

    scores = [score_case(r["gold"], r["teacher_pred"]) for r in records]
    agg = aggregate(scores)

    print(f"=== 재채점 결과 ({len(records)}건) ===")
    for k in sorted(agg):
        v = agg[k]
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    print("  (baseline_metrics.json의 n_cases와 다를 수 있음 — 그쪽은 오버샘플로 더 뽑힌 뒤\n"
          "   train/eval에 담기지 못하고 버려진 케이스까지 포함해서 계산됨)")

    for field in args.fields:
        misses = [r for r, s in zip(records, scores) if s.get(f"{field}_em") == 0.0]
        print(f"\n=== '{field}' EM 불일치 ({len(misses)}건 중 최대 {args.max_show}건) ===")
        for r in misses[: args.max_show]:
            print(f"[{r['case_id']}]")
            print(f"  gold: {r['gold'][field]!r}")
            print(f"  pred: {r['teacher_pred'][field]!r}")
            print(f"  원문: {r['text'][:120]}...")

    print(f"\n=== '미상'인데 다른 값으로 채운 사례 (최대 {args.max_show}건) ===")
    shown = 0
    for r in records:
        if shown >= args.max_show:
            break
        for f in FIELDS:
            if r["gold"][f] == "미상" and r["teacher_pred"][f] != "미상":
                print(f"[{r['case_id']}] {f}: 실제로는 미상인데 -> {r['teacher_pred'][f]!r}")
                shown += 1
                if shown >= args.max_show:
                    break
    if shown == 0:
        print("  없음 — 미상 탐지가 전부 맞았습니다.")


if __name__ == "__main__":
    main()