# 핸드오프 메모 — Hello-Clova-Agent (2026-06-14 세션 종료)

> **대상**: 이 프로젝트를 이어받는 다음 LLM  
> **목적**: 현재 상태와 다음 단계를 5분 안에 파악하기 위한 메모

---

## 1. 지금 당장 실행하면 되는 명령

```bash
# vLLM 서버 (CUDA Graph 활성, BnB 4-bit)
cd /home/machine/Hello-Clova-Agent
LLM_QUANTIZATION=bitsandbytes bash setup/start_vllm.sh
# → 포트 8000, 첫 기동 시 ~2분 소요 (torch.compile + CUDA Graph 캡처)

# Gradio UI (별도 터미널)
LLM_API_BASE="http://localhost:8000/v1" \
LLM_API_KEY="EMPTY" \
LLM_MODEL="naver-hyperclovax/HyperCLOVAX-SEED-Think-14B" \
GRADIO_SHARE="false" \
.venv/bin/python3 ui/app.py
# → http://localhost:7860
```

---

## 2. 프로젝트 현황

### 완료된 것 (건드리지 말 것)
| 항목 | 상태 |
|------|------|
| vLLM 0.19.1 + BnB 4-bit + CUDA Graph | ✅ 작동 확인 (31.7 tok/s) |
| 3-node 파이프라인 (input_parser → slide_writer → html_renderer) | ✅ 작동 |
| Gradio 3탭 UI (메모구성 / 직접입력 / 이전덱 보기) | ✅ 작동 |
| 환경 패키지 (transformers 5.12.0, vLLM 0.19.1) | ✅ 안정 |

### 손대면 안 되는 것
- `~/.cache/huggingface/hub/.../config.json` — `auto_map` 제거 상태. 되돌리면 vLLM 기동 실패
- `vLLM 버전` — 0.19.1 이외 버전 설치 금지 (AWQ 시도 때 환경 파괴 경험 있음)
- `transformers 버전` — 5.12.0 고정. 낮추면 hyperclovax 지원 소멸

---

## 3. 환경 스냅샷

| 항목 | 값 |
|------|-----|
| OS | WSL2 Ubuntu (kernel 6.6.87.2-microsoft-standard-WSL2) |
| GPU | NVIDIA RTX A5000 24.5GB (Ampere sm_86) |
| CUDA Driver | 576.28 → CUDA 12.9 지원 |
| Python | 3.12.3 / venv: `.venv/` |
| vLLM | **0.19.1** (PyTorch 2.10.0+cu128) |
| transformers | 5.12.0 |
| Gradio | 6.18.0 |
| 모델 | `naver-hyperclovax/HyperCLOVAX-SEED-Think-14B` |

---

## 4. 파이프라인 구조

```
사용자 입력 (Gradio)
  │
  ▼
[Node 1] input_parser    — LLM 없음, ~0.01s
  │   슬라이드 수 추출, parsed_request 구성
  ▼
[Node 2] slide_writer    — LLM 1회 호출, ~90-150s
  │   DIRECT_SLIDE_SYSTEM 프롬프트 → ===SLIDE_N=== 블록 파싱
  │   Think 모델 반복 출력 → seen set으로 중복 제거
  ▼
[Node 3] html_renderer   — LLM 없음, ~0.01s
  │   위치 기반 타입 추론 (0→cover, 끝→summary, 중간→content/section)
  │   Reveal.js 단일 HTML 생성
  ▼
output/deck_<timestamp>.html
```

---

## 5. 주요 파일 위치

```
agent/
  state.py            DeckState TypedDict 정의
  graph.py            3-node StateGraph 조립
  llm.py              OpenAI 호환 클라이언트 (vLLM 연결)
  prompts.py          DIRECT_SLIDE_SYSTEM (활성) + 레거시 OUTLINE/SLIDE_SYSTEM
  nodes/
    input_parser.py   슬라이드 수 파싱
    slide_writer.py   직접 슬라이드 생성
    html_renderer.py  Reveal.js HTML 렌더링
ui/app.py             Gradio 3탭 UI + threading 진행 표시
setup/start_vllm.sh   vLLM 시작 스크립트
wiki/implementation_log.md  전체 구현 이력 (상세)
```

---

## 6. 다음에 할 만한 작업 (Phase 2 아이디어)

아래는 지난 세션에서 언급된 기능 개선 후보. 우선순위는 사용자에게 확인:

### 🔥 높은 우선순위
- **슬라이드 품질 개선**: Think 모델 `<think>` 블록 내용 활용 (현재 버려짐)
- **RAG 연동**: `sources/` 디렉토리의 md/raw 파일을 컨텍스트로 주입
- **테마 선택**: HTML 렌더러에 다크/라이트/기업 테마 옵션 추가

### 🟡 중간 우선순위  
- **스트리밍 출력**: vLLM streaming → Gradio Chatbot 컴포넌트로 슬라이드 생성 과정 실시간 표시
- **슬라이드 편집**: 생성된 슬라이드 내용을 Gradio에서 직접 수정
- **PPTX 내보내기**: `python-pptx`로 PowerPoint 파일 생성

### 🟢 낮은 우선순위
- **AWQ 양자화**: Naver 공식 AWQ 모델 배포 대기 후 적용 (현재 불가)
- **멀티 GPU 지원**: `tensor_parallel_size` 파라미터 (RTX A5000 단일 GPU로 충분)

---

## 7. 알려진 함정

1. **Think 모델 반복 출력**: `===SLIDE_N===` 구분자 중복은 `seen set`으로 처리 중. 다른 구분자 방식 쓰면 다시 51페이지 문제 재현됨
2. **BnB 로딩 시간**: kill 후 재기동 시 ~2분 소요 (CUDA Graph 재캡처 포함). 프로세스 유지 권장
3. **4096 토큰 한도**: 입력이 길면 출력 품질 저하. `max_tokens=2048` 유지
4. **AWQ 시도 금지**: `pip install autoawq` 또는 `pip install llmcompressor` → 환경 파괴. transformers 버전 강제 다운그레이드됨
5. **LLM_API_BASE 필수**: `.bashrc` 비인터랙티브 가드 때문에 환경변수 자동 로드 안 됨. 항상 명시적으로 전달

---

## 8. 빠른 테스트

```bash
# 서버 상태 확인
curl http://localhost:8000/health

# 슬라이드 생성 직접 호출 (Gradio 없이)
LLM_API_BASE="http://localhost:8000/v1" \
LLM_API_KEY="EMPTY" \
LLM_MODEL="naver-hyperclovax/HyperCLOVAX-SEED-Think-14B" \
.venv/bin/python3 -c "
from agent.graph import run
result = run('LangGraph를 활용한 AI 에이전트 개발, 5페이지')
print('슬라이드 수:', len(result['slides_md']))
print('오류:', result.get('error'))
"
```

---

*작성일: 2026-06-14 | 작성자: Claude Sonnet 4.6 (세션 c473b7e9)*
