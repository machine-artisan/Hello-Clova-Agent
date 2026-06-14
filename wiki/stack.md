# Technology Stack

## Tools and Frameworks

### Agent Framework
- **LangGraph** `>=0.2.0` — 상태 머신 기반 에이전트 파이프라인 (Node 단위 조합)
- **LangChain Core** `>=0.3.0` — LLM / 프롬프트 추상화 레이어

### LLM Serving
- **vLLM 0.19.1** — OpenAI 호환 REST API 서버 (로컬 / Colab vLLM)
  - Python 3.12 / PyTorch 2.10.0+cu128 / CUDA 12.8 기준 확인됨
  - HyperCLOVA X SEED 내장 지원 버전 (`hyperclovax` 모듈 포함)
- **Ollama** — 일반 LLM (Qwen 등) 서빙용. HCX SEED 미지원.

### LLM API Client
- **openai** `>=1.0.0` — Python SDK. vLLM / Ollama의 `/v1/chat/completions` 엔드포인트 호출에 사용

### Web UI
- **Gradio** `>=4.44.0` — 브라우저 기반 UI. threading + yield 패턴으로 실시간 진행 표시

### Frontend Rendering
- **Reveal.js** (CDN) — HTML 슬라이드 프레임워크
- **Mermaid.js v11** (CDN) — 텍스트 기반 다이어그램 (`:::mermaid` 블록)
- **Pretendard Variable** (CDN, jsdelivr) — 한국어 최적화 가변 폰트

### Environment
- **python-dotenv** `>=1.0.0` — `.env` 파일 로드
- **huggingface_hub** — HuggingFace 모델 다운로드 / 인증

### Quantization (로컬 환경 선택)
- **bitsandbytes** — Think-14B 4-bit 양자화용 (Colab T4에서 필요, 1.5B에서는 불필요)

---

## Infrastructure

### 로컬 개발 환경
| 항목 | 값 |
|------|-----|
| OS | WSL2 Ubuntu (kernel 6.6.87.2-microsoft-standard-WSL2) |
| GPU | NVIDIA RTX A5000 24.5 GB (Ampere, sm_86) |
| CUDA Driver | 576.28 (Windows host) → CUDA 12.9 지원 |
| Python | 3.12.3 |
| venv | `.venv/` (프로젝트 루트) |
| vLLM | 0.19.1 |

### Colab 배포 환경
| 항목 | 값 |
|------|-----|
| GPU | NVIDIA T4 15GB (Turing, sm_75, Compute 7.5) |
| CUDA (Colab 기본) | 12.x (12.8) |
| CUDA 13 런타임 | `apt-get install cuda-cudart-13-0` 으로 추가 설치 (vLLM ABI 요구) |
| dtype 제약 | float16(half)만 지원 — bfloat16은 Ampere(8.0+)부터 |

---

## Models

| 모델 | 크기 | dtype | 양자화 | VRAM | 환경 |
|------|------|-------|--------|------|------|
| `HyperCLOVAX-SEED-Think-14B` | 14B | half | bitsandbytes 4-bit | ~9 GB | Colab T4 (Pro 권장) |
| `HyperCLOVAX-SEED-Text-Instruct-1.5B` | 1.5B | half | 없음 | ~3 GB | Colab T4 Free ✅ |
| `HyperCLOVAX-SEED-Text-Instruct-0.5B` | 0.57B | half | 없음 | ~1.2 GB | CPU 가능 |
| `HyperCLOVAX-SEED-Vision-Instruct-3B` | 3.63B | float16 | 없음 | ~7.5 GB | Colab T4 (커스텀 vLLM 필요) |
| `HyperCLOVAX-SEED-Think-32B` | 32B | half | bitsandbytes 4-bit | ~18 GB | A100 40GB |
| `qwen2.5:7b` (Ollama) | 7B | auto | Ollama 자동 | ~14 GB | Colab T4 (Ollama) |

---

## Data Sources / Integrations

- **HuggingFace Hub** (`naver-hyperclovax`) — HCX SEED 모델 다운로드
- **GitHub** (`machine-artisan/Hello-Clova-Agent`) — Colab에서 `git clone`으로 코드 주입
- **Reveal.js CDN** — 슬라이드 렌더링 (오프라인 불가)
- **Mermaid.js CDN** — 다이어그램 렌더링
- **Pretendard CDN** — 한국어 폰트
