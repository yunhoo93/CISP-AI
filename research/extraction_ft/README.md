# extraction_ft — 6필드 정보 추출 파인튜닝 준비 (Track A, 1주차)

`app/services/case_service.py`의 `generate_case_summary()`를 1.5B급 모델로
대체하기 위한 첫 단계: distillation 학습 데이터 + 평가 하네스를 만든다.

## 왜 이런 순서인가

보통은 텍스트 → 정답 순서로 데이터를 만들지만, 실제 수사 사건 설명 텍스트가
없는 상태라 반대로 간다.

1. 6필드 gold JSON을 먼저 무작위로 정한다 (`sampling.py`, `field_pools.py`)
2. GPT-4o에게 그 gold를 반영한 사건 개요문을 쓰게 한다 (생성)
3. 그 개요문을 `CaseService.generate_case_summary()`(실제 프로덕션 함수)에
   다시 넣어 6필드를 추출한다 (추출) — 추출기는 gold를 보지 않으므로,
   결과를 gold와 비교하면 **GPT-4o 자체의 진짜 baseline EM/F1**이 나온다
4. 필터링 후 train/eval로 분리해 저장한다 — eval 정답은 사람이 라벨링할
   필요가 없다. 애초에 우리가 정답을 정했기 때문이다.

## 시작하기 전에 — case_service.py 패치가 먼저

이 스크립트는 `app/services/case_service.py`를 그대로 import해서 쓴다.
아직 반영 안 했다면 다음 세 가지를 먼저 고칠 것:

- `temperature=0.3` → `temperature=0.0`
- system_prompt에 `확인할 수 없는 항목은 임의로 추측하지 말고 "미상"으로
  기재하십시오` 지시 추가 (라벨은 "확인불가" 등 동의어 대신 **"미상" 하나로
  통일** — 작은 모델이 배울 라벨은 적을수록 좋다)
- except 블록의 fallback을 빈 문자열 대신 전부 `"미상"`으로

패치 전에 데이터를 생성하면 처음부터 다시 만들어야 한다.

## 실행

레포 루트에 `.env`(`OPENAI_API_KEY` 포함)가 있는 상태에서:

```bash
cd research/extraction_ft
pip install tqdm   # requirements.txt에도 추가해둘 것

# 1) API 호출 없이 배선만 확인 (무료, 수 초) — 반드시 먼저
python generate_teacher_data.py --dry_run --n_train 20 --n_eval 5

# 2) 실제로 소량만 만들어 눈으로 품질 확인 (강력 권장)
python generate_teacher_data.py --n_train 20 --n_eval 5

# 3) 전체 규모
python generate_teacher_data.py --n_train 3000 --n_eval 400
```

2번 단계에서 `data/train.jsonl`을 열어 문장이 너무 뻔하지 않은지, '미상'으로
지정한 필드가 텍스트에 새어나오지 않았는지 직접 읽고 넘어갈 것. 여기서
걸러야 전체 규모에서 같은 문제를 반복하지 않는다.

## 출력

- `data/train.jsonl`, `data/eval.jsonl` — 각 줄
  `{case_id, case_type, text, gold, teacher_pred}`
- `data/rejected.jsonl` — 필터링으로 제외된 케이스와 사유
- `data/baseline_metrics.json` — GPT-4o의 자체 추출 성능. 앞으로 만들
  1.5B 파인튜닝 모델과 비교할 기준선이 이 숫자다.

파일 크기는 3,400건 기준 수 MB 수준이라 그대로 커밋해도 부담 없다 — 다른
사람이 결과를 재현하려고 API 비용을 다시 쓸 필요가 없어진다.

## 알아둘 점

- `--model`은 사건 개요문을 **쓰는** 모델만 바꾼다. 6필드를 **추출**하는
  모델은 항상 `app/config.py`의 `OPENAI_MODEL`을 따른다 — baseline이 실제
  프로덕션 설정과 정확히 같아야 의미가 있기 때문이다.
- 6필드가 전부 `"미상"`으로 나온 케이스는 자동으로 제외된다
  (`rejected.jsonl`에서 `extraction_all_unknown_likely_api_failure` 확인
  가능). 진짜로 환각 방지가 작동한 게 아니라, API 실패가 `case_service.py`의
  fallback으로 조용히 가려졌을 가능성이 높기 때문이다.
- `metrics.py`의 `token_f1`은 음절 단위 겹침을 쓰는 가벼운 근사치다. 여유가
  되면 프로젝트에 이미 있는 KR-SBERT 임베딩 코사인 유사도로 바꾸면
  `place`/`time`처럼 자유 서술인 필드를 더 정확히 채점할 수 있다.
- GPT-4o가 쓴 사건 개요문은 실제 진술서보다 정형화돼 있을 수 있다. 나중에
  익명화된 실제 샘플을 소량이라도 구하면 eval set에 섞어 넣는 것을 권장한다.

## 모듈 구성

```
field_pools.py            사건 유형별(절도/강도/폭행/사기) 6필드 값 풀
sampling.py                gold 샘플링 + 난이도(미상 개수 0/1/2) 배분
metrics.py                 EM / F1 / 미상 탐지 recall·FP rate 채점
                            (LoRA 모델 평가 때도 그대로 재사용)
generate_teacher_data.py   생성 → 추출 → 필터링 → train/eval 분리 저장
```
