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

| 모델 | VRAM | 권장 환경 |
|------|------|-----------|
| HyperCLOVA X SEED Instruct 3B | ~8GB | Colab T4 (15GB) |
| HyperCLOVA X SEED Instruct 0.5B | ~2GB | CPU 가능 |
| Qwen2.5-7B-Instruct | ~14GB | Colab T4 |
| Llama-3.2-3B-Instruct | ~6GB | Colab T4 |

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
