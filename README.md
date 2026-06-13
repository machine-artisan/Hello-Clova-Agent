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

## HyperCLOVA X SEED Think-14B 운영 가이드

### Qwen(Ollama) 대비 복잡성이 높은 이유

Qwen은 Ollama가 CUDA·드라이버·모델 형식을 모두 추상화합니다.  
HCX Think-14B는 vLLM을 직접 사용해야 하므로 시스템 레벨 의존성이 노출됩니다.

| 항목 | Qwen 2.5-7B (Ollama) | HCX Think-14B (vLLM) |
|------|----------------------|----------------------|
| 설치 | `ollama pull qwen2.5:7b` 한 줄 | transformers + vLLM + bitsandbytes |
| CUDA 의존성 | Ollama 내부 처리 (노출 안 됨) | `libcudart.so.13` SONAME 직접 의존 |
| Colab CUDA 불일치 | 영향 없음 | **libcudart.so.13 누락 → ImportError** |
| transformers 버전 | 관계없음 | **>=5.9.0 필수** (미충족 시 ProcessorMixin 에러) |
| 모델 ID 주의 | 단순 (`qwen2.5:7b`) | `HyperCLOVAX` (대시 없음, 오타 주의) |
| pip 충돌 경고 | 없음 | Colab 사전설치 패키지와 충돌 (무해하지만 노이즈) |
| 모델 로딩 시간 | ~5분 | ~15-25분 (4-bit 변환 포함) |
| 메모리 | ~4.7 GB | ~8-10 GB (4-bit 양자화) |

### 실제 발생한 에러와 근본 원인

#### 1. `ImportError: libcudart.so.13: cannot open shared object file`

```
원인: PyPI의 Python 3.12용 vLLM 휠은 CUDA 13 으로 컴파일됩니다.
      Colab T4 환경에는 libcudart.so.12 만 존재하며 .13 이 없습니다.
      버전 핀(vllm<0.9.0)으로도 해결 불가 — 모든 휠이 동일하게 영향받음.

해결: libcudart.so.12 → libcudart.so.13 심볼릭 링크 생성
      (CUDA 런타임 API는 기본 추론 범위에서 12→13 호환)
      노트북 셀 1에서 자동 처리됩니다.
```

#### 2. `ModuleNotFoundError: Could not import module 'ProcessorMixin'`

```
원인: HCX Think-14B README에 명시된 transformers>=5.9.0 이 미설치 상태.
      Colab 기본 transformers 버전이 요구사항 미달.

해결: pip install transformers>=5.9.0 을 vLLM 설치 전에 실행.
      순서 중요 — 나중에 설치하면 vLLM이 구버전 API로 초기화됨.
```

#### 3. 모델 ID 오타 → 401 Unauthorized

```
틀린 ID: naver-hyperclovax/HyperCLOVA-X-SEED-Think-14B  ← 하이픈 있음
올바른 ID: naver-hyperclovax/HyperCLOVAX-SEED-Think-14B  ← HyperCLOVAX

두 ID 모두 HuggingFace에 존재하는 것처럼 보이지만, 실제 모델은
HyperCLOVAX (X 뒤에 하이픈 없음) 에만 있습니다.
```

#### 4. `ERROR: pip's dependency resolver ...` (무해, 무시 가능)

```
원인: vLLM이 starlette/opentelemetry 버전을 변경하면서
      Colab 사전설치 패키지(google-adk, prometheus-fastapi-instrumentator)와
      버전 충돌. ERROR 로 표시되지만 우리 패키지와는 무관합니다.

확인법: langgraph / openai / gradio import 가 성공하면 정상.
```

### 재발 방지 체크리스트

셀 1 실행 직후 아래 출력을 확인하세요.

```
✅ 의존성 설치 완료
🔗 생성: /usr/local/cuda/lib64/libcudart.so.13 → libcudart.so.12   ← 반드시 확인
✅ vLLM import 사전 검증 통과                                         ← 반드시 확인
✅ vLLM 프로세스 시작 (PID: xxxxx)
```

`libcudart.so.13 생성` 과 `vLLM import 검증 통과` 가 나오면  
셀 4 의 5분 대기에서 실패하지 않습니다.

`import 검증 통과` 없이 서버를 시작하면 반드시 5분 후 실패합니다.

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
