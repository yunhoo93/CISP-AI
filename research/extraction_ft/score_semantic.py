"""
research/extraction_ft/score_semantic.py

EM/token_f1이 패러프레이즈를 과소평가하는 문제를 보완하기 위해, KR-SBERT 임베딩
코사인 유사도로 gold vs teacher_pred(GPT-4o) / gold vs lora_pred를 다시 채점한다.
CISP 프로젝트에서 판례 제목 임베딩에 쓴 것과 동일한 방식(CLS pooling + L2 정규화)을
그대로 재사용한다.

이미 저장된 예측 결과(eval.jsonl의 teacher_pred, eval_lora_adapter.py가 저장한
eval_predictions.jsonl)를 재사용하므로, API 호출도 GPU 생성 추론도 다시 필요 없다 —
순수 재채점이다.

실행 (Pod 안, /workspace/CISP-AI/research 에서):
  python extraction_ft/score_semantic.py \
      --lora_predictions lora_train/runs/r16_lr2e-4_v2/eval_predictions.jsonl
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

FIELDS = ["action", "object", "interaction", "place", "time", "result"]
UNKNOWN_ALIASES = {"미상", "확인불가", "알 수 없음", "알수없음", "불명"}


def is_unknown(s: str) -> bool:
    return (s or "").strip() in UNKNOWN_ALIASES


def load_jsonl(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--eval_path",
        default=str(Path(__file__).resolve().parent / "data" / "eval.jsonl"),
    )
    ap.add_argument(
        "--lora_predictions", required=True,
        help="eval_lora_adapter.py가 저장한 eval_predictions.jsonl 경로",
    )
    ap.add_argument("--sbert_model", default="snunlp/KR-SBERT-V40K-klueNLI-augSTS")
    ap.add_argument("--batch_size", type=int, default=64)
    ap.add_argument("--max_length", type=int, default=32,
                     help="필드 값은 판례 제목보다 짧은 구(句)라 32면 충분히 여유 있음")
    ap.add_argument("--diagnose_field", default="interaction",
                     help="이 필드에서 LoRA 유사도가 가장 낮은 사례를 마지막에 출력한다")
    ap.add_argument("--top_n", type=int, default=8)
    args = ap.parse_args()

    import torch  # noqa: E402
    from transformers import AutoModel, AutoTokenizer  # noqa: E402

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"KR-SBERT 로드 중... (device={device})")
    tokenizer = AutoTokenizer.from_pretrained(args.sbert_model)
    model = AutoModel.from_pretrained(args.sbert_model).to(device)
    model.eval()

    def encode(texts: List[str]):
        """CLS pooling + L2 정규화. 짧은 필드 값 배치를 한 번에 인코딩한다."""
        embs = []
        for i in range(0, len(texts), args.batch_size):
            batch = texts[i : i + args.batch_size]
            inputs = tokenizer(
                batch, padding=True, truncation=True,
                max_length=args.max_length, return_tensors="pt",
            ).to(device)
            with torch.no_grad():
                out = model(**inputs)
                e = out.last_hidden_state[:, 0, :]
                e = torch.nn.functional.normalize(e, p=2, dim=1)
            embs.append(e.cpu())
        return torch.cat(embs, dim=0)

    eval_records = {r["case_id"]: r for r in load_jsonl(Path(args.eval_path))}
    lora_records = {r["case_id"]: r for r in load_jsonl(Path(args.lora_predictions))}

    common_ids = sorted(set(eval_records) & set(lora_records))
    print(
        f"공통 case_id {len(common_ids)}건 "
        f"(eval.jsonl {len(eval_records)}건, lora 예측 {len(lora_records)}건)"
    )
    if not common_ids:
        raise SystemExit("공통 case_id가 없습니다 — eval_path와 lora_predictions가 같은 데이터셋인지 확인하세요.")

    field_scores_gpt4o: Dict[str, List[float]] = {f: [] for f in FIELDS}
    field_scores_lora: Dict[str, List[float]] = {f: [] for f in FIELDS}
    percase: Dict[str, List[dict]] = {f: [] for f in FIELDS}

    for field in FIELDS:
        golds = [eval_records[cid]["gold"][field] for cid in common_ids]
        teachers = [eval_records[cid]["teacher_pred"][field] for cid in common_ids]
        loras = [lora_records[cid]["lora_pred"][field] for cid in common_ids]

        gold_emb = encode(golds)
        teacher_emb = encode(teachers)
        lora_emb = encode(loras)

        sim_teacher = (gold_emb * teacher_emb).sum(dim=1)  # 둘 다 정규화됐으니 내적=코사인
        sim_lora = (gold_emb * lora_emb).sum(dim=1)

        for i in range(len(common_ids)):
            g, t, lp = golds[i], teachers[i], loras[i]
            if is_unknown(g):
                # '미상'끼리는 임베딩 유사도가 의미 없어 이진 일치로 대체
                s_t = 1.0 if is_unknown(t) else 0.0
                s_l = 1.0 if is_unknown(lp) else 0.0
            else:
                s_t = float(sim_teacher[i])
                s_l = float(sim_lora[i])
            field_scores_gpt4o[field].append(s_t)
            field_scores_lora[field].append(s_l)
            percase[field].append(
                {
                    "case_id": common_ids[i],
                    "gold": g,
                    "teacher_pred": t,
                    "sim_teacher": s_t,
                    "lora_pred": lp,
                    "sim_lora": s_l,
                }
            )

    print(f"\n=== 의미 유사도 기반 채점 (KR-SBERT 코사인, {len(common_ids)}건) ===")
    print(f"{'필드':<12} {'GPT-4o':>10} {'LoRA v2':>10} {'차이':>8}")
    macro_gpt4o, macro_lora = [], []
    for field in FIELDS:
        avg_gpt4o = sum(field_scores_gpt4o[field]) / len(field_scores_gpt4o[field])
        avg_lora = sum(field_scores_lora[field]) / len(field_scores_lora[field])
        macro_gpt4o.append(avg_gpt4o)
        macro_lora.append(avg_lora)
        print(f"{field:<12} {avg_gpt4o:>10.3f} {avg_lora:>10.3f} {avg_lora - avg_gpt4o:>+8.3f}")
    m_gpt4o, m_lora = sum(macro_gpt4o) / 6, sum(macro_lora) / 6
    print(f"{'macro 평균':<12} {m_gpt4o:>10.3f} {m_lora:>10.3f} {m_lora - m_gpt4o:>+8.3f}")

    out = {
        "gpt4o": {f: sum(field_scores_gpt4o[f]) / len(field_scores_gpt4o[f]) for f in FIELDS},
        "lora_v2": {f: sum(field_scores_lora[f]) / len(field_scores_lora[f]) for f in FIELDS},
        "n_cases": len(common_ids),
    }
    out_path = Path(args.lora_predictions).parent / "semantic_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out_path}")

    if args.diagnose_field in FIELDS:
        candidates = [r for r in percase[args.diagnose_field] if not is_unknown(r["gold"])]
        worst = sorted(candidates, key=lambda r: r["sim_lora"])[: args.top_n]
        print(f"\n=== '{args.diagnose_field}' LoRA 의미 유사도 최저 {len(worst)}건 ===")
        for r in worst:
            print(f"[{r['case_id']}] sim(LoRA)={r['sim_lora']:.3f}  sim(GPT-4o)={r['sim_teacher']:.3f}")
            print(f"  gold        : {r['gold']!r}")
            print(f"  teacher_pred: {r['teacher_pred']!r}")
            print(f"  lora_pred   : {r['lora_pred']!r}")

    percase_path = Path(args.lora_predictions).parent / "semantic_percase.jsonl"
    with open(percase_path, "w", encoding="utf-8") as f:
        for field in FIELDS:
            for r in percase[field]:
                f.write(json.dumps({"field": field, **r}, ensure_ascii=False) + "\n")
    print(f"건별 상세: {percase_path}")


if __name__ == "__main__":
    main()
