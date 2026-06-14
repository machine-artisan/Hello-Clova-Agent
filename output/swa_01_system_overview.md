# SWA-01: 시스템 개요 (System Overview)

> **패턴명**: Colab-Console + LangGraph Agent + Local LLM  
> **목적**: 이 문서는 "Colab .ipynb를 콘솔로 사용하여 LangGraph 기반 ML 에이전트 패키지를 구동하는" 아키텍처 패턴을 기술합니다.  
> 새 LLM이 이 패턴을 이해하고 유사한 패키지를 처음부터 구축할 수 있도록 작성됩니다.

---

## 1. 이 패턴이 해결하는 문제

| 문제 | 이 패턴의 답 |
|------|------------|
| ML 파이프라인 실행 환경이 없다 | Colab GPU 또는 WSL2 로컬 GPU 활용 |
| 비개발자도 ML 기능을 써야 한다 | Gradio UI를 통한 웹 인터페이스 |
| LLM 호출 로직이 복잡하다 | LangGraph로 노드 단위 선언적 파이프라인 |
| API 키 / 비용 문제 | 로컬 vLLM 서버 (자체 모델) |
| 여러 ML 기능을 패키지화하고 싶다 | Python 패키지 구조 + Colab .ipynb 인터페이스 |

---

## 2. 아키텍처 전체 그림

```
┌─────────────────────────────────────────────────────────────────┐
│  사용자 계층                                                      │
│                                                                   │
│  [Colab .ipynb]  또는  [Gradio Web UI]  또는  [CLI Python]       │
│  (콘솔 역할)             (일반 사용자)         (개발/테스트)       │
└────────────────────────────┬────────────────────────────────────┘
                             │ 함수 호출 / HTTP
┌────────────────────────────▼────────────────────────────────────┐
│  에이전트 레이어 (agent/)                                         │
│                                                                   │
│  graph.py → StateGraph                                            │
│    ├── Node 1: input_parser   (LLM 없음, 빠름)                   │
│    ├── Node 2: [domain_node]  (LLM 호출, 핵심 로직)              │
│    └── Node 3: output_node    (LLM 없음, 포맷/저장)              │
│                                                                   │
│  state.py → TypedDict 상태 스키마                                 │
│  llm.py   → OpenAI 호환 클라이언트                               │
│  prompts.py → 시스템 프롬프트 모음                                │
└────────────────────────────┬────────────────────────────────────┘
                             │ OpenAI REST API (HTTP)
┌────────────────────────────▼────────────────────────────────────┐
│  LLM 서버 레이어                                                  │
│                                                                   │
│  vLLM API Server (localhost:8000)                                 │
│    - OpenAI /v1/chat/completions 호환                             │
│    - 모델: 자체 보유 LLM (HuggingFace Hub)                       │
│    - 양자화: BitsAndBytes 4-bit (대형 모델), 또는 FP16/BF16      │
│    - 가속: CUDA Graph (RTX/A100 계열)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 레이어별 책임

### 3-1. 사용자 인터페이스 레이어

**Colab .ipynb (콘솔 모드)**
- `.ipynb`를 실행 환경이자 설정/실행 콘솔로 사용
- 셀 단위로 설치, 설정, 실행, 결과 확인
- 반복 실행 편의: 셀을 수정하면 즉시 재실행
- Google Drive 마운트로 영구 저장

**Gradio Web UI**
- 비개발자용 웹 인터페이스
- `gr.Blocks` + 복수 `gr.Tab`으로 기능 분리
- `threading.Thread` + generator `yield`로 블로킹 LLM 호출 중 실시간 진행 표시
- `gr.Progress` 또는 `gr.HTML`로 상태 피드백

**CLI (Python 직접)**
- 개발/테스트용: `python -c "from agent.graph import run; run(...)"`
- 배치 처리 시 유용

### 3-2. 에이전트 레이어

- **StateGraph**: 선언적 파이프라인 (노드 + 엣지)
- **TypedDict State**: 노드 간 데이터 계약 (컴파일 타임 타입 체크)
- **Node 함수**: `(state: S) -> S` 시그니처, 순수 함수에 가깝게 유지
- **LLM 클라이언트**: OpenAI SDK → 로컬 vLLM 또는 외부 API 모두 지원

### 3-3. LLM 서버 레이어

- **vLLM**: HuggingFace 모델을 OpenAI 호환 REST API로 서빙
- **BitsAndBytes 4-bit**: 24GB VRAM에서 14B 모델 구동 가능
- **CUDA Graph**: 첫 기동 시 그래프 캡처 후 이후 추론에서 +50% 속도

---

## 4. 데이터 흐름

```
사용자 입력 (문자열 or 구조화 폼)
    │
    ▼
State 초기화 (TypedDict)
    │
    ▼ graph.invoke() / graph.stream()
Node 1: 파싱/검증  →  State 업데이트
    │
    ▼
Node N: LLM 호출  →  State 업데이트
    │
    ▼
Node Last: 포맷/저장  →  최종 State
    │
    ▼
결과물 반환 (파일 / 문자열 / UI 업데이트)
```

---

## 5. 확장 방향

| 확장 목표 | 추가할 것 |
|----------|----------|
| 새 ML 기능 추가 | `agent/nodes/`에 새 노드 + `graph.py`에 엣지 추가 |
| 다른 모델 사용 | `LLM_MODEL` 환경변수만 교체 |
| RAG 연동 | 노드 하나를 문서 검색 노드로 추가 |
| 외부 API (GPT, Claude) | `LLM_API_BASE` 변경 + `LLM_API_KEY` 설정 |
| 멀티 에이전트 | `StateGraph`에 분기 엣지 (`add_conditional_edges`) 추가 |
| 배치 처리 | `graph.invoke()` 루프 또는 `asyncio` |

---

## 6. 이 패턴이 적합한 유스케이스

- 한국어 특화 LLM을 활용하는 ML 자동화 (네이버 HyperCLOVA X, KoGPT 등)
- 문서 생성 에이전트 (보고서, 프레젠테이션, 요약)
- 데이터 처리 파이프라인 (수집 → 변환 → 출력)
- 연구/실험용 파이프라인 (Colab에서 빠르게 프로토타이핑)
- 내부 도구 (팀 내 공유, 외부 API 비용 없이)

---

*문서 유형: SWA-01 시스템 개요 | 작성일: 2026-06-14*
