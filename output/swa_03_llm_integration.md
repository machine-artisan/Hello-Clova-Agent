# SWA-03: LLM 통합 가이드 (LLM Integration Guide)

> vLLM 로컬 서버 또는 외부 LLM API를 에이전트와 연결하는 방법.  
> HyperCLOVA X 특화 사항, 버전 선택 이유, 양자화 전략을 포함합니다.

---

## 1. LLM 클라이언트 패턴

모든 에이전트 노드는 이 모듈 하나를 통해 LLM을 호출합니다:

```python
# agent/llm.py
import os
from openai import OpenAI

def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY", "EMPTY"),
        base_url=os.getenv("LLM_API_BASE", "http://localhost:8000/v1"),
    )

def get_model_name() -> str:
    return os.getenv("LLM_MODEL", "default-model-name")

def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=get_model_name(),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
```

**환경변수로 LLM 대상 전환:**

| 환경변수 | 로컬 vLLM | OpenAI API | Claude API |
|---------|----------|-----------|-----------|
| `LLM_API_BASE` | `http://localhost:8000/v1` | `https://api.openai.com/v1` | `https://api.anthropic.com/v1` |
| `LLM_API_KEY` | `EMPTY` | `sk-...` | `sk-ant-...` |
| `LLM_MODEL` | `naver-hyperclovax/...` | `gpt-4o` | `claude-opus-4-7` |

---

## 2. vLLM 서버 설정

### 2-1. 최소 실행 명령

```bash
python -m vllm.entrypoints.openai.api_server \
    --model <huggingface-model-id> \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --served-model-name <same-as-model-id>
```

### 2-2. 대형 모델 (14B+) BitsAndBytes 4-bit 추가

```bash
    --quantization bitsandbytes \
    --load-format bitsandbytes
# → 28GB FP16 모델을 ~10GB VRAM으로 압축
```

### 2-3. CUDA Graph 활성 (기본값, --enforce-eager 없을 때)

- `--enforce-eager` 플래그를 **쓰지 않으면** 자동으로 CUDA Graph 활성
- 첫 기동 시 graph 캡처 (~1분), 이후 +50% 추론 속도
- RTX A5000 / A100 / 3090 계열에서 안정 동작

### 2-4. 핵심 파라미터 의미

| 파라미터 | 설명 | 추천값 |
|---------|------|--------|
| `--dtype auto` | 모델 선언 dtype 자동 선택 (bf16/fp16) | `auto` |
| `--max-model-len` | 입력+출력 합산 토큰 한도 | `4096` (14B 기준) |
| `--gpu-memory-utilization` | KV cache VRAM 비율 | `0.90` |
| `--quantization` | 양자화 방식 | `bitsandbytes` (14B+) |
| `--load-format` | 가중치 로드 방식 | `bitsandbytes` (양자화 시 필수) |

---

## 3. HyperCLOVA X 특화 사항

### 3-1. 지원 버전 매트릭스

| vLLM 버전 | PyTorch | CUDA 요구 | HyperCLOVAX 지원 |
|-----------|---------|-----------|-----------------|
| 0.8.5     | 2.6+cu124 | 12.4    | ❌ 내장 없음     |
| **0.19.1** | 2.10+cu128 | 12.8  | ✅ 내장          |
| 0.23.0    | 2.11+cu130 | **13.0** | ✅ 내장 (드라이버 제약) |

CUDA 12.9 드라이버 (Windows 576.28 기준) → **vLLM 0.19.1** 선택

### 3-2. Think 모델 특성

`HyperCLOVAX-SEED-Think-14B`는 추론 과정을 반복 출력합니다:

```
<think>
[내부 추론 과정 — 매우 길고 반복됨]
</think>

===SLIDE_1===
[내용]
===SLIDE_1===    ← 동일 내용 반복 출력
[내용]
===SLIDE_2===
[내용]
===SLIDE_2===    ← 반복
```

**대응 패턴:**
```python
# 구분자 기반 중복 제거
blocks = re.findall(r"===SLIDE_(\d+)===(.*?)(?====SLIDE_\d+===|$)", raw, re.DOTALL)
seen: set[str] = set()
slides = []
for num_str, content in blocks:
    if num_str not in seen:
        seen.add(num_str)
        if content.strip():
            slides.append(content.strip())
```

### 3-3. 토큰 한도 계산

```
max_model_len = 4096
= input_tokens + output_tokens

# 입력 프롬프트가 1000 토큰이면 → 출력 최대 3096 토큰
# max_tokens 설정: 입력 여유를 고려해 2048 이하 권장
```

### 3-4. config.json auto_map 문제

HyperCLOVA X HuggingFace 레포는 `config.json`에 `auto_map` 필드가 있어서,
transformers가 원격 코드 파일을 다운로드하려다 실패합니다.

**해결**: `~/.cache/huggingface/hub/.../config.json`에서 `auto_map` 섹션 제거

```bash
# 백업 후 수정
cp config.json config.json.bak
python3 -c "
import json
with open('config.json') as f: c = json.load(f)
c.pop('auto_map', None)
with open('config.json', 'w') as f: json.dump(c, f, indent=2, ensure_ascii=False)
"
```

---

## 4. 양자화 전략 비교

| 방식 | VRAM 절약 | 속도 | HyperCLOVAX 지원 | 비고 |
|------|----------|------|-----------------|------|
| FP16/BF16 | 없음 | 기준 | ✅ | 소형 모델 (3B~7B) |
| BitsAndBytes 4-bit | ~75% 감소 | 약간 느림 | ✅ vLLM에서 | 대형 모델 권장 |
| AWQ 4-bit | ~75% 감소 | 빠름 | ❌ AutoAWQ 미지원 | Naver 공식 배포 대기 |
| GPTQ 4-bit | ~75% 감소 | 빠름 | ❌ llm-compressor 환경 파괴 | 동일 |

**현재 권장**: BitsAndBytes 4-bit (`--quantization bitsandbytes --load-format bitsandbytes`)

---

## 5. LLM 호출 시 자주 발생하는 오류

### 오류 1: 400 context length exceeded

```
BadRequestError: 400 - maximum context length is 4096 tokens.
However, you requested 4096 output tokens.
```

**원인**: `max_tokens=4096`이면 입력 토큰 공간이 없음  
**수정**: `max_tokens=2048` (입력 ~1000 + 출력 ~2048 = 3048 < 4096)

### 오류 2: 모델 응답이 비어있거나 중단

**원인**: 생성 중 GPU OOM 또는 `max_tokens` 초과  
**수정**: `max_tokens` 줄이기, `--gpu-memory-utilization` 낮추기 (0.85 이하)

### 오류 3: 구분자 없이 자유 형식 출력

**원인**: Think 모델이 `<think>` 블록에서 구분자를 먼저 생성하고 본문에서 다른 형식 사용  
**수정**: 프롬프트에 "구분자와 내용 이외 텍스트 절대 금지" 명시 + 폴백 파서 추가

```python
# 폴백: 구분자 파싱 실패 시 "---"로 재분할
if not items:
    items = [s.strip() for s in raw.split("---") if s.strip()]
```

---

## 6. 외부 LLM API로 전환 시

환경변수만 교체:

```bash
# Claude API
LLM_API_BASE="https://api.anthropic.com/v1"
LLM_API_KEY="sk-ant-..."
LLM_MODEL="claude-opus-4-7"

# OpenAI API
LLM_API_BASE="https://api.openai.com/v1"
LLM_API_KEY="sk-..."
LLM_MODEL="gpt-4o"
```

**주의**: 외부 API는 `max_tokens` 의미가 다를 수 있음 (출력 토큰만 카운트하는 경우도 있음)

---

*문서 유형: SWA-03 LLM 통합 가이드 | 작성일: 2026-06-14*
