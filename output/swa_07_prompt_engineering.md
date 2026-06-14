# SWA-07: 프롬프트 엔지니어링 가이드 (Prompt Engineering Guide)

> 한국어 LLM (HyperCLOVA X, KoGPT 등)을 LangGraph 에이전트에서 사용할 때의 프롬프트 설계 패턴.  
> 구조화 출력, Think 모델 특성, 반복 출력 방지, 폴백 파싱을 다룹니다.

---

## 1. 기본 프롬프트 구조

```python
# agent/prompts.py 구성 패턴

MY_SYSTEM_PROMPT = """당신은 [역할 설명]입니다.
[배경/컨텍스트]

출력 형식 (반드시 준수):

===ITEM_1===
[내용 구조 설명]

===ITEM_2===
[내용 구조 설명]

규칙:
- ===ITEM_N=== 구분자 필수 (N은 1부터 시작)
- [세부 형식 규칙 1]
- [세부 형식 규칙 2]
- 구분자와 내용 이외 텍스트 절대 금지"""
```

**핵심 설계 원칙:**
1. **역할 먼저** — "당신은 X입니다"로 시작
2. **출력 형식 명시** — 구분자 기반 구조화 출력
3. **규칙은 네거티브로** — "~하지 마라"가 한국어 LLM에 효과적
4. **예시 포함** — 형식이 복잡할수록 예시 필수

---

## 2. Hello-Clova-Agent 실제 프롬프트

### 2-1. 슬라이드 직접 생성 (현재 사용 중)

```python
DIRECT_SLIDE_SYSTEM = """당신은 프레젠테이션 전문가입니다.
사용자의 요청을 받아 슬라이드 내용을 바로 작성합니다.

출력 형식 (반드시 준수):

===SLIDE_1===
## 발표 제목
부제목: 한 줄 소개
대상: 대상 독자 / 날짜: 오늘

===SLIDE_2===
## 슬라이드 제목
- **핵심어:** 구체적인 설명 문장으로 내용을 충분히 기술합니다.
- **핵심어:** 또 다른 포인트를 완전한 문장으로 설명합니다.

규칙:
- ===SLIDE_N=== 구분자 필수 (N은 1부터 시작)
- 첫 번째 슬라이드: 표지
- 마지막 슬라이드: 요약 및 결론
- 본문 슬라이드: 불릿 포인트 3~5개, **핵심어:** 형식 (완전한 문장)
- 요청한 슬라이드 수 정확히 출력
- 구분자와 내용 이외 텍스트 절대 금지"""
```

### 2-2. 유저 메시지 패턴

```python
# 슬라이드 수를 명시적으로 포함
user_msg = (
    f"아래 요청을 바탕으로 {num_slides}장 분량의 슬라이드를 작성해 주세요.\n\n"
    f"요청:\n{original_prompt}"
)
```

---

## 3. Think 모델 특성과 대응

HyperCLOVA X SEED **Think** 모델은 추론 과정 블록을 먼저 출력합니다:

```
<think>
[수백~수천 토큰의 내부 추론]
[동일 내용 반복 가능]
</think>

===SLIDE_1===
[실제 출력]
===SLIDE_1===    ← 반복 출력 가능
[동일 내용]
===SLIDE_2===
[실제 출력]
```

### 3-1. 반복 출력 중복 제거

```python
import re

raw = llm_response  # Think 모델 전체 출력

# ===ITEM_N=== 패턴으로 파싱 + 중복 제거
blocks = re.findall(
    r"===SLIDE_(\d+)===(.*?)(?====SLIDE_\d+===|$)",
    raw,
    re.DOTALL
)

seen: set[str] = set()
items = []
for num_str, content in blocks:
    if num_str not in seen:
        seen.add(num_str)
        c = content.strip()
        if c:
            items.append(c)
```

### 3-2. JSON 출력 중복 제거

Think 모델이 JSON을 반복 출력할 때:

```python
import json

def extract_first_json(raw: str) -> dict:
    """Think 모델 반복 JSON에서 첫 번째 JSON 객체만 추출"""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(raw):
        if ch == '{':
            try:
                obj, _ = decoder.raw_decode(raw, i)
                return obj
            except json.JSONDecodeError:
                continue
    raise ValueError(f"JSON 추출 실패: {raw[:200]}")
```

### 3-3. Think 블록 제거

```python
import re

def strip_think_blocks(text: str) -> str:
    """<think>...</think> 블록 제거"""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
```

---

## 4. 구조화 출력 파싱 전략

### 4-1. 구분자 기반 (권장)

```python
# 장점: 중복 제거 쉬움, 순서 명확
# 형식: ===ITEM_1===, ===ITEM_2===, ...

items = []
seen = set()
for num_str, content in re.findall(
    r"===ITEM_(\d+)===(.*?)(?====ITEM_\d+===|$)", raw, re.DOTALL
):
    if num_str not in seen:
        seen.add(num_str)
        if content.strip():
            items.append(content.strip())
```

### 4-2. 마크다운 구분선 기반

```python
# 형식: --- 또는 ***
items = [s.strip() for s in raw.split("---") if s.strip()]
```

### 4-3. JSON 기반

```python
# Think 모델에서 JSON은 반복 출력 주의
try:
    data = extract_first_json(raw)
except ValueError:
    data = {}  # 폴백 처리
```

### 4-4. 폴백 체인

```python
items = []

# 1차: 구분자 파싱
blocks = re.findall(r"===ITEM_(\d+)===(.*?)(?====ITEM_\d+===|$)", raw, re.DOTALL)
seen = set()
for num_str, content in blocks:
    if num_str not in seen:
        seen.add(num_str)
        if content.strip():
            items.append(content.strip())

# 2차 폴백: "---" 분리
if not items:
    items = [s.strip() for s in raw.split("---") if s.strip()]

# 3차 폴백: 전체를 하나의 아이템으로
if not items and raw.strip():
    items = [raw.strip()]

if not items:
    return {**state, "error": f"파싱 실패:\n{raw[:500]}", "status": "오류"}
```

---

## 5. 한국어 LLM 특성별 프롬프트 팁

### HyperCLOVA X (Naver)

| 특성 | 대응 |
|------|------|
| Think 모델이 긴 추론 블록 출력 | `<think>` 제거 또는 구분자 이후만 파싱 |
| 동일 블록 반복 출력 | `seen set` 중복 제거 필수 |
| 4096 토큰 컨텍스트 한도 | `max_tokens=2048`, 입력 간결하게 |
| 한국어 지시 충실 | "~하지 마라" 네거티브 규칙 효과적 |
| 형식 준수율 높음 | 예시 포함 시 구조화 출력 안정적 |

### 일반 한국어 LLM 공통

- **구체적 숫자 지시**: "3~5개" > "몇 가지"
- **완전한 문장 요구**: "완전한 문장으로 설명하세요" — 키워드 나열 방지
- **금지 규칙 명시**: "다른 텍스트 출력 금지" — 시스템 메시지 등 불필요 텍스트 방지

---

## 6. 프롬프트 파일 구성

```python
# agent/prompts.py 권장 구조

# ─── 활성 프롬프트 ────────────────────────────────────────────────────
MAIN_SYSTEM = """..."""   # 현재 파이프라인에서 사용 중

# ─── 레거시 (참고용) ──────────────────────────────────────────────────
LEGACY_OUTLINE_SYSTEM = """..."""    # 이전 2-call 파이프라인 outline 노드용
LEGACY_SLIDE_SYSTEM = """..."""      # 이전 2-call 파이프라인 slide 노드용

# ─── 실험적 ──────────────────────────────────────────────────────────
# EXPERIMENTAL_STREAM_SYSTEM = """..."""  # 스트리밍 출력 실험용 (미완성)
```

---

## 7. temperature / max_tokens 가이드

| 작업 | temperature | max_tokens | 이유 |
|------|------------|------------|------|
| 슬라이드 생성 (창의적) | 0.7 | 2048 | 다양성 + 컨텍스트 여유 |
| JSON 목차 생성 (구조적) | 0.3 | 1024 | 형식 일관성 중요 |
| 요약/분석 (사실 기반) | 0.2 | 1024 | 환각 최소화 |
| 번역 | 0.1 | 2048 | 직역 선호 |

---

*문서 유형: SWA-07 프롬프트 엔지니어링 가이드 | 작성일: 2026-06-14*
