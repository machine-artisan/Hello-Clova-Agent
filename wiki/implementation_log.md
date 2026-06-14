# Implementation Log — Local Deck Gen Agent (Phase 1)

> **대상 독자**: 이 프로젝트를 이어 받는 LLM 또는 개발자.
> 환경 재현, 버그 원인, 설계 결정을 빠르게 파악하기 위한 문서입니다.

---

## 1. 환경 스냅샷

| 항목 | 값 |
|------|-----|
| OS | WSL2 Ubuntu (kernel 6.6.87.2-microsoft-standard-WSL2) |
| GPU | NVIDIA RTX A5000 24.5 GB (Ampere, sm_86) |
| CUDA Driver | 576.28 (Windows) → CUDA **12.9** 지원 |
| Python | 3.12.3 |
| venv 경로 | `/home/machine/Hello-Clova-Agent/.venv` |
| vLLM | **0.19.1** (PyTorch 2.10.0+cu128) |
| Gradio | 최신 (설치 시점 기준) |
| 모델 | `naver-hyperclovax/HyperCLOVAX-SEED-Think-14B` |
| 모델 가중치 | HuggingFace Hub 자동 다운로드 (~48 GB, 첫 실행 시 캐시) |

---

## 2. vLLM 버전 선정 이유 (매우 중요)

### 충돌 매트릭스

| vLLM 버전 | PyTorch (내장) | CUDA 요구 | HyperCLOVAX 지원 | 결과 |
|-----------|---------------|-----------|-----------------|------|
| 0.8.5     | 2.6.0+cu124   | 12.4      | ❌ 없음          | 불가 |
| 0.23.0    | 2.11.0+cu130  | **13.0**  | ✅ 있음          | 불가 (드라이버 12.9) |
| **0.19.1** | 2.10.0+cu128 | 12.8 ✅   | ✅ 있음          | **선택** |

- vLLM 0.8.5: `configuration_hyperclovax.py`를 HF 레포에서 찾으려다 실패 → 아키텍처 미지원
- vLLM 0.23.0: PyTorch가 내부적으로 CUDA 13.0 runtime을 링크 → Windows 드라이버 576.28 (CUDA 12.9) 에서 `libcuda.so` 버전 불일치 오류
- vLLM 0.19.1: PyTorch cu128 (CUDA 12.8)은 CUDA 12.9 드라이버와 호환 + `hyperclovax` 모듈 내장

### 설치 명령 (재현용)

```bash
# venv 기준
pip install vllm==0.19.1
# torch 2.10.0+cu128 자동 설치됨
```

---

## 3. vLLM 서버 기동 명령 (현재 작동 확인된 명령)

```bash
.venv/bin/python3 -m vllm.entrypoints.openai.api_server \
  --model naver-hyperclovax/HyperCLOVAX-SEED-Think-14B \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager \
  --quantization bitsandbytes \
  --load-format bitsandbytes \
  --served-model-name naver-hyperclovax/HyperCLOVAX-SEED-Think-14B
```

**플래그 설명:**

| 플래그 | 이유 |
|--------|------|
| `--dtype auto` | 모델이 bfloat16 선언 → 자동 선택 |
| `--max-model-len 4096` | 모델 최대 컨텍스트. 4096을 넘으면 OOM |
| `--gpu-memory-utilization 0.90` | KV cache에 VRAM 90% 할당 |
| `--enforce-eager` | CUDA Graph 비활성화 (vLLM 0.19.1 초기화 안정성) |
| `--quantization bitsandbytes` | BnB 4-bit 양자화 (14B → ~10 GB VRAM) |
| `--load-format bitsandbytes` | 위와 함께 필수 |
| ~~`--trust-remote-code`~~ | **제거됨** — vLLM 0.19.1은 hyperclovax 내장 지원, 이 플래그 시 HF repo에서 config 파일 다운로드 시도 → 실패 |

**모델 초기 로딩**: BnB 4-bit 양자화 weight 로딩은 **30분+** 소요. 이후 HF 캐시에서 재로딩하면 훨씬 빠름.

---

## 4. LangGraph 파이프라인 상세

```
[Node 1] input_parser        LLM 없음  ~0.01s
[Node 2] outline_generator   LLM 호출  ~90-120s   → JSON 목차 생성
[Node 3] slide_writer        LLM 호출  ~90-150s   → 슬라이드 마크다운
[Node 4] html_renderer       LLM 없음  ~0.01s     → Reveal.js HTML
```

총 소요: **4~5분** (LLM 추론이 99% 차지)

### 상태 스키마 (`agent/state.py`)

```python
class DeckState(TypedDict):
    user_prompt: str        # 원문 입력
    num_slides: int         # 파싱된 슬라이드 수
    parsed_request: dict    # {original_prompt, num_slides}
    outline: dict           # 슬라이드 목차 JSON
    slides_md: list[str]    # 슬라이드별 마크다운
    html_output: str        # 최종 Reveal.js HTML
    status: str             # UI 진행 표시용
    error: Optional[str]    # 오류 메시지
```

---

## 5. 버그 수정 기록

### 5-1. `max_tokens` 400 오류

**증상**: `❌ 400 - This model's maximum context length is 4096 tokens. However, you requested 4096 output tokens`

**원인**: 모델 컨텍스트 한도 = 4096 (input + output 합산). `max_tokens=4096`으로 설정하면 입력 토큰 분이 없음.

**수정**: `agent/llm.py` 기본값 `max_tokens=2048`, `agent/nodes/slide_writer.py` 하드코딩 제거.

---

### 5-2. 슬라이드 51페이지 출력

**증상**: 12페이지 요청 시 51장 HTML 생성.

**원인**: HyperCLOVA X SEED Think 모델의 특성 — 동일한 JSON·텍스트 블록을 여러 번 반복 출력.

**수정 1 (`outline_generator.py`)**: `json.loads()` 대신 `json.JSONDecoder().raw_decode(raw, start)` 사용 → 첫 번째 JSON 객체만 추출.

**수정 2 (`slide_writer.py`)**: 슬라이드 번호 중복 제거:
```python
blocks = re.findall(r"===SLIDE_(\d+)===(.*?)(?====SLIDE_\d+===|$)", raw, re.DOTALL)
seen: set[str] = set()
for num, content in blocks:
    if num not in seen:
        seen.add(num)
        slides_md.append(content.strip())
```

**수정 3 (`html_renderer.py`)**: 목차 슬라이드 수를 상한으로 고정:
```python
n = len(slide_infos) if slide_infos else len(slides_md)
# 변경 전: n = max(len(slides_md), len(slide_infos))
```

---

### 5-3. 슬라이드 내용이 단어 나열 수준

**증상**: `- **핵심어:** 내용` 형태가 아닌 단어 나열만 출력.

**원인**: `SLIDE_SYSTEM` 프롬프트에 "핵심만 간결하게" 지시 → 모델이 압축된 출력.

**수정 (`agent/prompts.py`)**: 형식 명확화:
```
- 내용은 - 불릿 포인트, 형식: **핵심어:** 구체적 설명
- 슬라이드당 3~5개 불릿, 각 불릿은 완전한 문장으로 충분히 설명
```

---

### 5-4. HTML에 `<p>assistant</p>` 태그 출력

**증상**: 슬라이드 첫 줄에 "assistant" 텍스트가 렌더링.

**원인**: Think 모델이 assistant role prefix를 출력에 포함.

**수정**: 슬라이드 중복 제거 로직에서 `===SLIDE_N===` 이전의 모든 텍스트가 자동 폐기됨 → 암묵적 해결.

---

## 6. Gradio UI 아키텍처 (`ui/app.py`)

### 스레드 기반 진행 표시 (핵심 패턴)

LangGraph가 블로킹 LLM 호출을 실행하는 동안 Gradio가 2초마다 상태를 갱신하는 패턴:

```python
def _run_graph_in_thread(prompt: str, shared: dict):
    # 별도 스레드에서 LangGraph 실행
    for state_update in graph.stream(initial_state, stream_mode="updates"):
        node_name = list(state_update.keys())[0]
        shared["node"] = node_name
        shared["node_label"] = NODE_LABELS[node_name]
        shared["node_progress"] = NODE_PROGRESS[node_name]
    shared["done"] = True

def generate_deck(prompt: str, progress=gr.Progress()):
    # generator 함수: yield로 Gradio 실시간 갱신
    thread = threading.Thread(target=_run_graph_in_thread, ...)
    thread.start()
    while not shared["done"]:
        time.sleep(2)
        yield LOADING_HTML, None, f"⏱️ {elapsed}초 경과..."
    yield iframe_html, out_path, "✅ 완료"
```

### 탭 구조

| 탭 | 목적 |
|----|------|
| 📋 메모 내용 구성 (권장) | 구조화된 입력 (제목, 페이지 수, 주제, 대상, 스타일) |
| ✏️ 직접 입력 (고급) | 자유 형식 프롬프트 |
| 📂 이전 메모 덱 | `output/deck_*.html` 목록 → 클릭으로 미리보기 |

### Reveal.js iframe 렌더링

`srcdoc` 속성으로 직접 HTML 삽입:
```python
safe_html = html.replace('"', "&quot;")
iframe_html = f'<iframe srcdoc="{safe_html}" style="width:100%;height:600px;...">'
```
> **주의**: Gradio가 `<script>` 태그 경고를 출력하지만, `srcdoc`을 사용하는 `<iframe>` 내부에서는 스크립트가 정상 실행됨 (브라우저 보안 모델 상 독립 문서). Reveal.js 동작에 문제 없음.

---

## 7. 환경변수 주입 방법

Claude Code CLI에서 `~/.bashrc`의 비인터랙티브 가드(`case $- in *i*) ;; *) return;; esac`) 때문에 `.bashrc` 소싱이 안 됨.

**해결**: `.claude/settings.local.json`의 `env` 블록 활용:
```json
{
  "permissions": {
    "allow": ["Skill(update-config)", "Bash(python3 *)"]
  },
  "env": {
    "HF_TOKEN": "<HuggingFace 토큰>"
  }
}
```

Gradio 실행 시에는 명시적 환경변수 전달:
```bash
LLM_API_BASE="http://localhost:8000/v1" \
LLM_API_KEY="EMPTY" \
LLM_MODEL="naver-hyperclovax/HyperCLOVAX-SEED-Think-14B" \
GRADIO_SHARE="false" \
.venv/bin/python3 ui/app.py > /tmp/gradio.log 2>&1 &
```

---

## 8. 출력 결과물

- 저장 위치: `output/deck_<timestamp>.html`
- 형식: Reveal.js 단일 HTML 파일 (CDN 로드)
- 디자인: Flutter Material Design 3 컬러 시스템
  - cover: `#1565C0` (파란색)
  - section: `#006A6A` (틸)
  - content: `#FFFFFF` (흰색, 파란 강조)
  - summary: `#0D47A1` (다크 블루)

---

## 9. 속도 최적화 — 시도 결과

### ✅ Option 2: LLM 호출 2→1 통합 (구현 완료)

**before**: outline_generator(Node 2, LLM) + slide_writer(Node 3, LLM) = 4~5분  
**after**: slide_writer만(Node 2, LLM 1회) = **2~3분** (약 50% 단축)

변경 내역:
- `agent/graph.py`: `outline_generator` 노드 제거, 3-node 파이프라인으로 단순화
- `agent/nodes/slide_writer.py`: `parsed_request`에서 직접 슬라이드 생성 (`DIRECT_SLIDE_SYSTEM` 프롬프트)
- `agent/nodes/html_renderer.py`: `outline.get("slides", [])` 없을 때 위치 기반 타입 추론 추가
- `agent/prompts.py`: `DIRECT_SLIDE_SYSTEM` 추가 (기존 `OUTLINE_SYSTEM`, `SLIDE_SYSTEM`은 레거시로 보존)
- `ui/app.py`: `NODE_LABELS` 4개 → 3개 (`[1/3]`, `[2/3]`, `[3/3]`)

측정 결과: 3슬라이드 테스트 기준 **78.6초** (단순 요청 기준)

---

### ✅ Option 1: CUDA Graph 활성화 (구현 완료)

**변경**: vLLM 시작 인수에서 `--enforce-eager` 제거  
**결과**: **31.7 tok/s** (기준 ~21 tok/s 대비 **+50% 속도 향상**)

CUDA Graph 활성 시 부가 효과:
- `torch.compile` 자동 실행 (14.2s, 첫 기동 시 1회)
- CUDA Graph 캡처 (51 piecewise + 35 full, 약 1분 소요)
- 이후 추론마다 컴파일된 그래프 재사용

vLLM 기동 명령 (현재 확인된 최적 설정):
```bash
.venv/bin/python3 -m vllm.entrypoints.openai.api_server \
  --model naver-hyperclovax/HyperCLOVAX-SEED-Think-14B \
  --dtype auto --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --quantization bitsandbytes --load-format bitsandbytes \
  --served-model-name naver-hyperclovax/HyperCLOVAX-SEED-Think-14B
  # --enforce-eager 없음 → CUDA Graph 활성
```

---

### ❌ Option 3: AWQ 양자화 — 불가 (시도 완료, 근본 한계 확인)

**시도 1: AutoAWQ 0.2.9**

- `AWQ_CAUSAL_LM_MODEL_MAP["hyperclovax"] = LlamaAWQForCausalLM` 패치 성공
- `TRANSFORMERS_AUTO_MAPPING_DICT["hyperclovax"] = "AutoModelForCausalLM"` 패치 성공
- `config.json`의 `auto_map` 제거 (transformers 5.x 내장 지원 활성화)
- 모델 FP16 로드 성공 (421/421 weights, device_map=auto)
- **실패 지점**: `quantizer.py:566 torch.cat(): expected a non-empty list of Tensors`
  - LlamaAWQForCausalLM의 내부 hook이 HyperCLOVA X 레이어에 붙지 않음
  - 캘리브레이션 입력이 캡처되지 않아 samples 리스트가 비어있음

**시도 2: llm-compressor (vLLM 공식 후계)**

- `pip install llmcompressor` → transformers 5.12.0 → 4.57.6 다운그레이드 발생
- transformers 4.57.6에는 hyperclovax 내장 지원 없음 → `KeyError: 'hyperclovax'`
- **환경 파괴**: huggingface-hub 0.36.2로 다운그레이드 → Gradio 6.18.0 비호환
- 복구 필요: `pip install transformers==5.12.0 "huggingface-hub>=1.2.0,<2.0" compressed-tensors==0.15.0.1`

**근본 원인**:
HyperCLOVA X SEED Think-14B는 HuggingFace 레포에 `configuration_hyperclovax.py`/`modeling_hyperclovax.py` 파일이 없음.
vLLM 0.19.1은 이 모델을 내부적으로 지원하지만, AWQ/GPTQ 양자화 도구들은 외부 transformers API를 통해 모델을 로드하므로 이 경로가 막힘.

**향후 AWQ 가능성**:
- Naver가 공식 AWQ 양자화 버전 배포 시 즉시 사용 가능
- `--quantization awq --model <awq-model-path>`으로 vLLM에서 로드

---

### 최종 속도 비교

| 구성 | 토큰 속도 | 소요 시간(12슬라이드 추정) |
|------|---------|--------------------------|
| BnB + enforce-eager + 2 LLM calls (원래) | ~21 tok/s | ~4~5분 |
| BnB + CUDA Graph + 1 LLM call (현재) | ~32 tok/s | **~2~3분** |
| AWQ + CUDA Graph + 1 LLM call (미래) | ~60+ tok/s (예상) | ~1분 이내 (예상) |

---

## 10. 알려진 한계 / 주의사항

1. **Think 모델 출력 반복**: `===SLIDE_N===` 중복 제거 로직이 필수. LLM 교체 시 이 로직이 불필요할 수 있음.
2. **4096 토큰 컨텍스트 한도**: 입력 프롬프트가 길면 슬라이드 출력 품질 저하. 입력은 간결하게.
3. **BnB 4-bit 첫 로딩 30분+**: 프로세스 kill 후 재기동 시 마찬가지로 오래 걸림. vLLM 프로세스를 가능한 유지할 것.
4. **WSL2 네트워크**: WSL2 IP가 재부팅마다 바뀔 수 있음. `localhost`는 항상 유효.
5. **Gradio script 경고**: `gr.HTML` 컴포넌트의 `<script>` 경고는 무시 가능 (iframe srcdoc은 정상 실행).
