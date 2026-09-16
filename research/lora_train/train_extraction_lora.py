"""
research/lora_train/train_extraction_lora.py

Kanana-1.5-2.1B-Instruct를 6필드 정보 추출(action/object/interaction/place/time/result)에
LoRA로 파인튜닝한다.

학습 타깃은 gold가 아니라 teacher_pred다. gold는 field_pools.py의 좁은 값 집합(예: object는
전체 15종류뿐)이라, 그대로 학습 타깃으로 쓰면 모델이 실제 문서를 읽는 대신 몇 개 안 되는
고정 문구를 암기해버린다. teacher_pred는 GPT-4o(패치된 프롬프트 기준)가 자연스럽게 낸
다양한 표현이라, 실제 문서 일반화에 필요한 신호를 담고 있다.

TRL 1.13.0 / transformers 5.17.0 / peft 0.20.0의 공식 문서 기준으로 API를 확인하고 작성했다
(2026-09 기준). 데이터는 'conversational prompt-completion' 포맷을 쓴다 — prompt와
completion을 분리해서 넣으면 TRL이 기본값으로 completion(정답) 부분에만 loss를 걸어주므로,
프롬프트 마스킹을 직접 구현할 필요가 없다.

실행 (Pod 안, /workspace/CISP-AI/research 에서):
  cd /workspace/CISP-AI/research

  # 1) 배선 확인 — train 20건/eval 10건으로 몇 스텝만, 수 분 내 종료
  python lora_train/train_extraction_lora.py --smoke_test

  # 2) 전체 학습
  python lora_train/train_extraction_lora.py \
      --output_dir lora_train/runs/r16_lr2e-4 \
      --r 16 --lora_alpha 32 --learning_rate 2e-4 --num_train_epochs 3
"""

import argparse
import json
from pathlib import Path
from typing import Optional

FIELDS = ["action", "object", "interaction", "place", "time", "result"]

SYSTEM_PROMPT = """당신은 사건 분석 전문가입니다.

입력된 사건 내용을 다음 6가지 요소로 구조화하십시오:

1. action: 행위 (예: 강탈, 절도, 폭행)
2. object: 대상/객체 (예: 스마트폰, 현금, 귀금속)
3. interaction: 상호작용 방식 (예: 물리적 접촉, 대면, 비대면, 협박)
4. place: 장소 (예: 서울시 주택가 골목길)
5. time: 시간 (예: 낮 시간대, 오후 2시경, 야간)
6. result: 결과 (예: 물품 탈취 성공, 도주, 미수)

각 항목은 간결하게 핵심만 추출하십시오.
사건 내용에서 확인할 수 없는 항목은 절대 임의로 추측하지 말고, "미상"으로 기재하십시오.
사건 유형상 흔히 나타나는 값이라도, 해당 사건 내용에 구체적으로 언급되지 않았다면 추측해서
채우지 마십시오 (예: 사기 사건이라고 해서 object를 임의로 "금전"이라 쓰지 마십시오).
구체적인 수단·경로가 명시되어 있다면 그 구체성을 유지하고, 상위 범주어로 뭉뚱그리지
마십시오 (예: "전화로 기망"을 "비대면"으로 축약하지 마십시오)."""


def load_records(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def patch_llama_config_validator() -> None:
    """transformers 5.x의 LlamaConfig validate_architecture 검증기가
    head_dim을 독립적으로 명시하는 GQA 아키텍처(Kanana 포함)를 잘못 거부하는
    버그를 우회한다. transformers가 고치면 조용히 아무 일도 안 한다."""
    try:
        from transformers.models.llama.configuration_llama import LlamaConfig
        LlamaConfig.__class_validators__ = [
            v for v in LlamaConfig.__class_validators__
            if getattr(v, "__name__", "") != "validate_architecture"
        ]
    except (ImportError, AttributeError):
        pass


def to_prompt_completion(record: dict) -> dict:
    """{case_id, case_type, text, gold, teacher_pred} -> TRL conversational
    prompt-completion 포맷. teacher_pred가 학습 타깃(정답)이다."""
    completion_json = json.dumps(
        {k: record["teacher_pred"][k] for k in FIELDS}, ensure_ascii=False
    )
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"사건 내용:\n{record['text']}"},
        ],
        "completion": [
            {"role": "assistant", "content": completion_json},
        ],
    }


def build_rows(path: Path, limit: Optional[int] = None) -> list:
    records = load_records(path)
    if limit:
        records = records[:limit]
    return [to_prompt_completion(r) for r in records]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_id", default="kakaocorp/kanana-1.5-2.1b-instruct-2505")
    ap.add_argument(
        "--data_dir",
        default=str(Path(__file__).resolve().parents[1] / "extraction_ft" / "data"),
    )
    ap.add_argument(
        "--output_dir",
        default=str(Path(__file__).resolve().parent / "runs" / "run1"),
    )
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--lora_alpha", type=int, default=32)
    ap.add_argument("--lora_dropout", type=float, default=0.05)
    ap.add_argument("--learning_rate", type=float, default=2e-4)
    ap.add_argument("--num_train_epochs", type=float, default=3.0)
    ap.add_argument("--per_device_train_batch_size", type=int, default=4)
    ap.add_argument("--gradient_accumulation_steps", type=int, default=4)
    ap.add_argument("--max_length", type=int, default=768)
    ap.add_argument("--eval_steps", type=int, default=50)
    ap.add_argument("--save_steps", type=int, default=100)
    ap.add_argument(
        "--smoke_test",
        action="store_true",
        help="train 20건 / eval 10건으로 몇 스텝만 돌려 배선을 확인한다 (수 분 내 종료, 실제 학습 아님)",
    )
    args = ap.parse_args()

    import torch  # noqa: E402
    from datasets import Dataset  # noqa: E402
    from peft import LoraConfig  # noqa: E402
    from trl import SFTConfig, SFTTrainer  # noqa: E402

    patch_llama_config_validator()  # AutoConfig.from_pretrained 전에 반드시 먼저

    data_dir = Path(args.data_dir)

    if args.smoke_test:
        train_rows = build_rows(data_dir / "train.jsonl", limit=20)
        eval_rows = build_rows(data_dir / "eval.jsonl", limit=10)
        output_dir = str(Path(args.output_dir).parent / "smoke_test")
        max_steps, eval_steps, save_steps, logging_steps = 6, 2, 6, 1
        print("=== SMOKE TEST 모드: 20건/10건, 6스텝만. 실제 학습 품질과 무관 ===")
    else:
        train_rows = build_rows(data_dir / "train.jsonl")
        eval_rows = build_rows(data_dir / "eval.jsonl")
        output_dir = args.output_dir
        max_steps = -1
        eval_steps, save_steps, logging_steps = args.eval_steps, args.save_steps, 10

    train_ds = Dataset.from_list(train_rows)
    eval_ds = Dataset.from_list(eval_rows)

    print(f"train {len(train_ds)}건, eval {len(eval_ds)}건")
    print("샘플 1건:")
    print(json.dumps(train_ds[0], ensure_ascii=False, indent=2))

    peft_config = LoraConfig(
        r=args.r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    training_args = SFTConfig(
        output_dir=output_dir,
        model_init_kwargs={"dtype": torch.bfloat16, "trust_remote_code": True},
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_length=args.max_length,
        max_steps=max_steps,
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=2,
        load_best_model_at_end=True,  # eval_loss 기준 최적 체크포인트를 회전 삭제에서 보호
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=logging_steps,
        bf16=True,
        report_to="none",
        seed=42,
    )

    trainer = SFTTrainer(
        model=args.model_id,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        peft_config=peft_config,
    )

    trainer.train()
    if trainer.state.best_metric is not None:
        print(
            f"\n최적 체크포인트(eval_loss={trainer.state.best_metric:.4f})를 "
            f"로드한 상태로 저장합니다: {trainer.state.best_model_checkpoint}"
        )
    trainer.save_model(output_dir)
    print(f"\n저장 완료: {output_dir}")


if __name__ == "__main__":
    main()
