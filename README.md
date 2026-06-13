# Local Deck Gen Agent

한국어 프롬프트 → Reveal.js 발표 슬라이드 자동 생성 에이전트

> Gamma, SkyAI, Manus 같은 서비스를 **로컬 환경에서 직접 구현**하며 AI 에이전트 기술을 체험합니다.

---

## 핵심 개념 — 이 프로젝트를 통해 배우는 것

### 웹서버 · 앱서버 · API 서버 란?

```
[브라우저] ──HTTP──► [웹서버: Gradio]
                            │ Python 호출
                     [앱서버: LangGraph]
                            │ HTTP (OpenAI API)
                     [API서버: vLLM :8000]
                            │ GPU
                     [LLM: HyperCLOVA X]
```

| 레이어 | 역할 | 이 프로젝트에서 |
|--------|------|----------------|
| **웹서버** | 브라우저 ↔ 앱 사이의 HTTP 통신 처리 | `ui/app.py` (Gradio) |
| **앱서버** | 비즈니스 로직 실행 (에이전트 파이프라인) | `agent/graph.py` (LangGraph) |
| **API서버** | LLM 추론을 REST API로 제공 | vLLM `:8000` |

### LangGraph 에이전트 파이프라인

```
입력 (한국어 텍스트)
     │
[Node 1] input_parser      → 슬라이드 수 추출, 요청 구조화 (LLM ❌)
     │
[Node 2] outline_generator → 슬라이드 목차 JSON 생성         (LLM ✅)
     │
[Node 3] slide_writer      → 슬라이드별 마크다운 내용 작성   (LLM ✅)
     │
[Node 4] html_renderer     → Reveal.js HTML 변환             (LLM ❌)
     │
출력 (Reveal.js HTML)
```

---

## Colab 체험 가이드 (3단계)

### 1단계: 설치
```bash
git clone https://github.com/<username>/local-deck-gen.git
cd local-deck-gen
bash setup/colab_setup.sh
```

### 2단계: vLLM API 서버 시작 (백그라운드)
```bash
bash setup/start_vllm.sh &
sleep 90   # 모델 로딩 대기 (~1분)
```

### 3단계: Gradio 앱 실행
```bash
python ui/app.py
```
→ 출력된 **공개 URL** (https://xxxx.gradio.live)을 브라우저에서 열기

---

## 프로젝트 구조

```
local-deck-gen/
├── agent/
│   ├── state.py              # LangGraph 상태 정의 (DeckState)
│   ├── llm.py                # LLM 클라이언트 (OpenAI-compatible)
│   ├── prompts.py            # 각 노드 시스템 프롬프트
│   ├── graph.py              # 파이프라인 조립 및 실행
│   └── nodes/
│       ├── input_parser.py   # Node 1: 입력 파싱
│       ├── outline_generator.py  # Node 2: 목차 생성
│       ├── slide_writer.py   # Node 3: 내용 작성
│       └── html_renderer.py  # Node 4: HTML 렌더링
├── ui/
│   └── app.py                # Gradio 웹 UI
├── setup/
│   ├── colab_setup.sh        # Colab 초기 설정
│   └── start_vllm.sh         # vLLM API 서버 시작
├── samples/
│   └── project_intro.md      # 첫 번째 샘플 덱 입력
├── output/                   # 생성된 HTML 저장
├── requirements.txt
└── .env.example
```

---

## 환경 설정

```bash
cp .env.example .env
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LLM_API_BASE` | `http://localhost:8000/v1` | vLLM API 서버 주소 |
| `LLM_API_KEY` | `EMPTY` | vLLM은 키 불필요 |
| `LLM_MODEL` | `naver-hyperclovax/HyperCLOVA-X-SEED-Instruct-3B` | 사용 모델명 |

---

## 지원 모델

| 모델 | VRAM | 권장 환경 | 비고 |
|------|------|-----------|------|
| **HyperCLOVA X SEED Think-14B** | **~8-10GB** (4-bit) | **Colab T4 (15GB)** ✅ | 국산 LLM 최적 선택 |
| HyperCLOVA X SEED Instruct 3B | ~8GB (fp16) | Colab T4 (15GB) | 빠른 추론 |
| HyperCLOVA X SEED Think-32B | ~18GB (4-bit) | A100 40GB | 최고 품질 |
| HyperCLOVA X SEED Instruct 0.5B | ~2GB | CPU 가능 | 가장 가벼움 |
| Qwen2.5-7B-Instruct (Ollama) | ~14GB (fp16) | Colab T4 | 기본 데모용 |

> **공공기관 프로젝트**: 국산 LLM 사용 요건 충족을 위해 `HyperCLOVA X SEED Think-14B`를 권장합니다.  
> 16GB VRAM 환경에서 4-bit 양자화 시 8-10GB로 구동 가능합니다.
>
> ```bash
> # Think-14B 실행 (vLLM + 4-bit 양자화)
> LLM_MODEL=naver-hyperclovax/HyperCLOVAX-SEED-Think-14B \
> LLM_QUANTIZATION=bitsandbytes \
> LLM_DTYPE=bfloat16 \
> bash setup/start_vllm.sh
> ```

---

## HyperCLOVA X SEED 사용 시 유의사항

> **이 섹션을 읽는 분께**
>
> 일반적인 LLM 서빙 환경(OpenAI API, Ollama 등)에서는 아래 내용이 필요하지 않습니다.
> HyperCLOVA X SEED 모델은 Ollama 공식 레지스트리에 등록되어 있지 않아
> vLLM을 통한 직접 서빙이 필요하며, 이 과정에서 시스템 레벨 의존성이 노출됩니다.
>
> **이 복잡성은 이 모델의 특성이지, LLM 서빙의 일반적인 모습이 아닙니다.**
> 국산 LLM 사용 요건이 없다면 Qwen/Llama 계열 + Ollama 조합을 권장합니다.

### 일반 LLM 서빙과의 차이

대부분의 LLM(Qwen, Llama 등)은 Ollama를 통해 한 줄로 사용할 수 있습니다.

```bash
# 일반적인 LLM 서빙 — 이게 정상입니다
ollama pull qwen2.5:7b   # 끝
```

HyperCLOVA X SEED는 Ollama 레지스트리에 없어 vLLM을 직접 사용해야 합니다.
그 결과 아래 시스템 레벨 의존성이 모두 사용자에게 노출됩니다.

| 항목 | 일반 LLM (Ollama) | HCX SEED Think-14B (vLLM) |
|------|-------------------|---------------------------|
| 설치 | `ollama pull` 한 줄 | transformers + vLLM + bitsandbytes 개별 설치 |
| CUDA 의존성 | Ollama가 내부 처리 | `libcudart.so.13` SONAME 직접 의존 |
| Colab 환경 충돌 | 없음 | libcudart 버전 불일치 → 심볼릭 링크 필요 |
| Python 패키지 요구 | 없음 | `transformers>=5.9.0` 필수, 설치 순서 중요 |
| 모델 ID | 직관적 | `HyperCLOVAX` (X 뒤 하이픈 없음) 오타 주의 |
| pip 충돌 경고 | 없음 | Colab 사전 패키지와 충돌 경고 발생 (무해) |
| 모델 로딩 시간 | ~5분 | ~15-25분 (4-bit 변환 포함) |

### 알려진 문제와 해결책

#### ❗ `ImportError: libcudart.so.13: cannot open shared object file`

```
원인: PyPI Python 3.12용 vLLM 휠이 CUDA 13으로 컴파일되어 있으나
      Colab T4 환경에는 libcudart.so.12 만 존재합니다.
      vLLM 버전을 낮춰도 해결되지 않습니다 — 모든 휠이 동일하게 영향받습니다.

해결: libcudart.so.12 → libcudart.so.13 심볼릭 링크 생성
      노트북 셀 1에서 자동 처리됩니다.
```

#### ❗ `ModuleNotFoundError: Could not import module 'ProcessorMixin'`

```
원인: 이 모델은 transformers>=5.9.0 을 요구합니다.
      Colab 기본 설치 버전이 이 요구사항을 충족하지 않습니다.

해결: pip install transformers>=5.9.0 을 vLLM 설치 전에 실행.
      순서가 중요합니다 — 역순이면 vLLM이 구버전 API로 초기화됩니다.
```

#### ❗ 모델 ID → 401 Unauthorized 또는 다운로드 실패

```
올바른 ID: naver-hyperclovax/HyperCLOVAX-SEED-Think-14B
            (HyperCLOVAX — X 뒤에 하이픈 없음)

틀린 ID:  naver-hyperclovax/HyperCLOVA-X-SEED-Think-14B
            (HyperCLOVA-X — 자주 혼동되는 표기)
```

#### ❗ `ERROR: pip's dependency resolver ...` (무해, 무시 가능)

```
vLLM이 starlette/opentelemetry 버전을 변경하면서 Colab 사전설치 패키지
(google-adk, prometheus-fastapi-instrumentator)와 충돌 경고가 발생합니다.
이 프로젝트의 패키지(langgraph, gradio, openai)와는 무관합니다.
셀 3에서 langgraph / openai / gradio import 가 ✅ 이면 정상입니다.
```

### 셀 1 정상 완료 확인

아래 출력이 모두 나와야 셀 4(서버 대기)로 진행할 수 있습니다.

```
✅ 의존성 설치 완료
🔗 생성: /usr/local/cuda/lib64/libcudart.so.13 → libcudart.so.12   ← 필수
✅ vLLM import 사전 검증 통과                                         ← 필수
✅ vLLM 프로세스 시작 (PID: xxxxx)
```

`vLLM import 사전 검증 통과` 없이 서버가 시작되었다면 셀 4에서 반드시 실패합니다.

---

## 로드맵

| Phase | 상태 | 주요 기능 |
|-------|------|-----------|
| **Phase 1 (MVP)** | ✅ 완료 | 한국어 입력 → 고정 테마 Reveal.js 덱 생성 |
| Phase 2 | 🚧 계획 | LLM-Wiki RAG 연동, 동적 CSS 테마 자동 생성 |

---

## 참고 상용 서비스

- [Gamma](https://gamma.app) — AI 발표 자동 생성
- [SkyAI](https://skyai.io) — 한국어 특화 발표 생성  
- [Manus](https://manus.im) — 멀티 에이전트 자동화

이 프로젝트는 위 서비스의 핵심 파이프라인을 직접 구현해보는 학습용 클론입니다.
