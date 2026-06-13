# Karpathy 개념으로 읽는 Hello Clova Agent

## Andrej Karpathy가 말하는 두 가지 개념

### 1. LLM Wiki (Knowledge Base as OS Memory)

> "LLM은 학습 시점에 고정된 지식을 갖는다.
>  운영 중 새 지식을 주입하려면 외부 메모리가 필요하다.
>  그것이 Wiki이다."

Karpathy는 LLM을 **CPU**에, 컨텍스트 윈도우를 **RAM**에, 외부 저장소를 **디스크**에 비유합니다.
Wiki는 이 구조에서 **디스크 — 영구 도메인 지식 저장소**입니다.

```
Karpathy의 LLM OS 비유          이 프로젝트에서
─────────────────────────────────────────────────
CPU                         →   vLLM (LLM 추론 엔진)
RAM (Context Window)        →   agent/prompts.py 에 주입되는 텍스트
Disk (Long-term Memory)     →   wiki/ 디렉토리
I/O (Input/Output)          →   Gradio UI (ui/app.py)
Process                     →   LangGraph 파이프라인 (agent/graph.py)
```

### 2. Harness Engineering

> "모델을 평가하고 반복 개선하려면,
>  일관된 입력-출력 환경이 필요하다.
>  그것이 Harness이다."

Harness = 모델을 감싸는 **표준화된 실행 환경**.
입력을 주면 출력이 나오고, 그 결과를 측정/비교할 수 있는 틀.

---

## 이 프로젝트 디렉토리를 Karpathy 개념으로 읽기

```
local-deck-gen/
│
├── wiki/                        ← LLM의 외부 디스크 메모리
│   ├── domain.md                   도메인 지식 (Disk: Domain RAM)
│   ├── stack.md                    기술 스택 지식
│   └── glossary.md                 용어 사전
│
├── sources/                     ← 지식 원천 (Raw I/O)
│   ├── raw/                        PDF, ipynb 원본 입력
│   ├── md/                         변환된 중간 형태
│   └── processed/                  처리 완료 아카이브
│
├── wiki_agent/                  ← 지식 파이프라인 (OS Kernel)
│   ├── convert.py                  원천 → 구조화 변환기
│   ├── ingest.py                   구조화 → Wiki 병합기
│   └── wiki_loader.py              Wiki → 컨텍스트 주입기
│
├── agent/                       ← LLM Harness (실행 환경)
│   ├── state.py                    Harness: 입출력 스키마 정의
│   ├── llm.py                      Harness: LLM 호출 인터페이스
│   ├── prompts.py                  Harness: 컨텍스트 주입 지점
│   ├── graph.py                    Harness: 파이프라인 조립
│   └── nodes/                      Harness: 각 처리 단계
│       ├── input_parser.py             Node 1: I/O 정규화
│       ├── outline_generator.py        Node 2: LLM 호출 (RAM → CPU)
│       ├── slide_writer.py             Node 3: LLM 호출 (RAM → CPU)
│       └── html_renderer.py            Node 4: 출력 직렬화
│
├── ui/                          ← OS Shell (사용자 인터페이스)
│   └── app.py                      Gradio: 사용자 ↔ Harness 연결
│
└── setup/                       ← OS Boot (환경 초기화)
    ├── colab_setup.sh              부팅 스크립트
    └── start_vllm.sh               API 서버 데몬 시작
```

---

## Harness Engineering 관점에서 본 agent/ 구조

Harness의 핵심 원칙: **모델을 격리하고, 입출력을 표준화한다.**

### state.py — Harness의 데이터 계약

```python
class DeckState(TypedDict):
    user_prompt: str        # 입력 (표준화된 형태)
    num_slides: int
    parsed_request: dict
    outline: dict
    slides_md: list[str]
    html_output: str        # 출력 (표준화된 형태)
    error: Optional[str]    # 오류 상태
```

Karpathy가 말하는 Harness는 "모델이 무엇을 받고 무엇을 돌려줘야 하는지 명시적으로 정의한 것"입니다.
`DeckState`가 바로 이 계약입니다.

### llm.py — Harness의 모델 격리

```python
def chat(messages, temperature=0.7, max_tokens=4096) -> str:
    # 모델의 실제 구현(vLLM, OpenAI, Ollama)과
    # 나머지 파이프라인을 완전히 분리
```

Harness의 핵심: **나머지 코드가 어떤 모델을 쓰는지 몰라야 한다.**
`llm.py`만 바꾸면 vLLM → OpenAI → Claude API 교체가 가능합니다.

### graph.py — Harness의 실행 오케스트레이터

```
입력 → [Node1] → [Node2] → [Node3] → [Node4] → 출력
```

LangGraph의 `StateGraph`는 Karpathy가 말하는
"모델 호출을 체인처럼 조립하는 오케스트레이터"입니다.
각 노드는 독립 평가 가능한 단위입니다.

---

## LLM Wiki 파이프라인: Karpathy의 RAG 확장

Karpathy의 RAG 개념을 이 프로젝트 파이프라인에 매핑:

```
[사용자 문서 (PDF/ipynb)]
        ↓  wiki_agent/convert.py
[구조화 Markdown]
        ↓  wiki_agent/ingest.py  (LLM이 요약·분류)
[wiki/domain.md, stack.md, glossary.md]
        ↓  wiki_agent/wiki_loader.py
[컨텍스트 문자열]
        ↓  agent/prompts.py에 주입
[LLM 호출 — 도메인 지식을 가진 상태로]
        ↓
[도메인 특화 슬라이드 생성]
```

Karpathy의 표현으로: **"디스크에서 RAM으로 로드한 다음 CPU에게 건넨다."**

---

## 이 구조가 가르쳐주는 것

| Karpathy 개념 | 이 프로젝트에서 배울 수 있는 것 |
|--------------|-------------------------------|
| LLM은 stateless | wiki/ 없이는 도메인 지식이 없다 |
| Context = RAM | prompts.py가 RAM 크기를 결정한다 |
| Harness = 재현성 | state.py가 있어야 A/B 테스트 가능 |
| 모델 교체 가능성 | llm.py 격리가 그것을 보장한다 |
| 평가 루프 | 지금 없음 → Phase 2 과제 |

---

## Phase 2에서 추가해야 할 Harness 요소

Karpathy가 강조하는 **평가 루프(Eval Loop)**가 현재 없습니다.

```python
# 제안: workspace/eval/ 디렉토리
# 슬라이드 품질 자동 평가 harness

def eval_deck(html_output: str, expected_slides: int) -> dict:
    return {
        "slide_count_match": ...,
        "has_title":         ...,
        "korean_ratio":      ...,  # 한국어 비율
        "avg_bullet_length": ...,  # 글머리 기호 길이
    }
```

이 Harness가 있어야 모델 교체(HCX → Qwen → Claude)의 품질 차이를 측정할 수 있습니다.
