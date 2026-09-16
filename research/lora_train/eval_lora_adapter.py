"""
research/lora_train/eval_lora_adapter.py

학습된 LoRA 어댑터로 eval.jsonl 400건을 실제 추론하고, extraction_ft/metrics.py의
score_case로 채점한다. baseline_metrics.json(GPT-4o, 프롬프트 패치 후)과 나란히
비교할 수 있는 숫자를 만드는 게 목적이다.

train_extraction_lora.py의 SYSTEM_PROMPT를 그대로 재사용한다 — 학습 때와 다른
프롬프트로 평가하면 비교 자체가 무의미해진다.

실행 (Pod 안, /workspace/CISP-AI/research 에서):
  # 1) 먼저 10건만 — 출력이 말이 되는지 직접 읽어보기
  python lora_train/eval_lora_adapter.py --adapter_dir lora_train/runs/r16_lr2e-4 --limit 10

  # 2) 전체 400건
  python lora_train/eval_lora_adapter.py --adapter_dir lora_train/runs/r16_lr2e-4
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extraction_ft"))

from field_pools import FIELDS  # noqa: E402
from metrics import score_case, aggregate  # noqa: E402
from train_extraction_lora import (  # noqa: E402
    SYSTEM_PROMPT,
    load_records,
    patch_llama_config_validator,
)


def extract_json(text: str) -> Optional[dict]:
    """모델 출력에서 JSON 객체를 최대한 관대하게 뽑아낸다.
    학습 타깃이 순수 JSON 한 줄이었지만, 실제 생성 결과엔 여분의 텍스트나
    따옴표 스타일 차이가 섞일 수 있어 바로 실패시키지 않고 한 번 더 시도한다."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter_dir", required=True)
    ap.add_argument("--base_model_id", default="kakaocorp/kanana-1.5-2.1b-instruct-2505",
                     help="어댑터 폴더에 토크나이저가 없을 때 쓸 대체 경로")
    ap.add_argument(
        "--eval_path",
        default=str(Path(__file__).resolve().parents[1] / "extraction_ft" / "data" / "eval.jsonl"),
    )
    ap.add_argument(
        "--baseline_path",
        default=str(Path(__file__).resolve().parents[1] / "extraction_ft" / "data" / "baseline_metrics.json"),
    )
    ap.add_argument("--max_new_tokens", type=int, default=150)
    ap.add_argument("--limit", type=int, default=None, help="디버깅용 — 앞에서 N건만 돈다")
    args = ap.parse_args()

    import torch  # noqa: E402
    from peft import AutoPeftModelForCausalLM  # noqa: E402
    from transformers import AutoTokenizer  # noqa: E402
    from tqdm import tqdm  # noqa: E402

    patch_llama_config_validator()

    print(f"어댑터 로드: {args.adapter_dir}")
    model = AutoPeftModelForCausalLM.from_pretrained(
        args.adapter_dir, dtype=torch.bfloat16, trust_remote_code=True
    ).to("cuda")
    model.eval()

    try:
        tokenizer = AutoTokenizer.from_pretrained(args.adapter_dir)
    except Exception:
        print(f"(어댑터 폴더에 토크나이저가 없어 베이스 모델 {args.base_model_id}에서 불러옵니다)")
        tokenizer = AutoTokenizer.from_pretrained(args.base_model_id)

    records = load_records(Path(args.eval_path))
    if args.limit:
        records = records[: args.limit]

    results, parse_failures = [], 0

    for r in tqdm(records, desc="LoRA 모델 추론"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"사건 내용:\n{r['text']}"},
        ]
        input_ids = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt", return_dict=True,
        ).to("cuda")

        with torch.no_grad():
            output_ids = model.generate(
                **input_ids,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        gen_text = tokenizer.decode(output_ids[0][input_ids["input_ids"].shape[1]:], skip_special_tokens=True)

        parsed = extract_json(gen_text)
        if parsed is None or not all(f in parsed for f in FIELDS):
            parse_failures += 1
            pred = {f: "미상" for f in FIELDS}
        else:
            pred = {k: str(parsed.get(k, "미상")) for k in FIELDS}

        results.append(
            {"case_id": r["case_id"], "gold": r["gold"], "lora_pred": pred, "raw_output": gen_text}
        )

    print(f"\nJSON 파싱 실패: {parse_failures}/{len(records)}건 (실패분은 전부 '미상'으로 채점됨)")

    scores = [score_case(r["gold"], r["lora_pred"]) for r in results]
    agg = aggregate(scores)

    out_dir = Path(args.adapter_dir)
    with open(out_dir / "eval_predictions.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out_dir / "eval_metrics.json", "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)

    print(f"\n=== LoRA 모델 성능 (eval {len(records)}건) ===")
    for k, v in sorted(agg.items()):
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    baseline_path = Path(args.baseline_path)
    if baseline_path.exists():
        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)
        print("\n=== GPT-4o baseline(패치 후) 대비 ===")
        for k in sorted(agg.keys()):
            if k in baseline and isinstance(agg[k], float) and isinstance(baseline[k], float):
                diff = agg[k] - baseline[k]
                print(f"  {k}: LoRA {agg[k]:.3f} vs GPT-4o {baseline[k]:.3f} (차이 {diff:+.3f})")
    else:
        print(f"\n(baseline 파일을 못 찾음: {baseline_path})")

    print(f"\n결과 저장: {out_dir}/eval_predictions.jsonl, {out_dir}/eval_metrics.json")


if __name__ == "__main__":
    main()
