# SWA 문서 인덱스 — Colab-Console + LangGraph + Local LLM 패턴

> 이 디렉토리의 문서들은 "Colab .ipynb를 콘솔로 사용하여 LangGraph 기반 ML 에이전트 패키지를 구동하는" 아키텍처 패턴을 기술합니다.  
> 새 LLM 또는 개발자에게 컨텍스트로 제공하기 위해 작성됩니다.

---

## 문서 목록

| 파일 | 유형 | 내용 |
|------|------|------|
| `handoff_memo.md` | 프로젝트 메모 | 내일 이어받을 LLM을 위한 현재 상태 및 다음 단계 |
| `swa_01_system_overview.md` | 시스템 개요 | 전체 아키텍처, 레이어 구조, 데이터 흐름, 확장 방향 |
| `swa_02_agent_pipeline.md` | 에이전트 설계 | LangGraph StateGraph, 노드 패턴, 에러 전파, 스트리밍 |
| `swa_03_llm_integration.md` | LLM 통합 | vLLM 서버 설정, HyperCLOVA X 특화, 양자화 전략 |
| `swa_04_notebook_console.md` | Colab 패턴 | .ipynb 콘솔, Drive 연동, 로컬 WSL2 실행 |
| `swa_05_gradio_ui.md` | UI 패턴 | threading + yield 진행 표시, 탭 구조, 파일 미리보기 |
| `swa_06_environment.md` | 환경 설정 | 의존성, 버전 충돌, CUDA 진단, 복구 절차 |
| `swa_07_prompt_engineering.md` | 프롬프트 | 구조화 출력, Think 모델 대응, 중복 제거, 폴백 파싱 |
| `swa_08_future_slide_analysis.md` | 외부 분석 | future-slide 아키텍처 비교 + index.html 기술 요소 적용 제안 |
| `swa_09_future_slide_deep_analysis.md` | 심층 분석 | template.html/SKILL.md 분석 + Mermaid.js 통합 계획 |

---

## 새 프로젝트에 이 패턴 적용 시 읽는 순서

1. `swa_01_system_overview.md` — 전체 그림 파악 (5분)
2. `swa_06_environment.md` — 환경 구축 (실행 전)
3. `swa_02_agent_pipeline.md` — 에이전트 코드 작성
4. `swa_03_llm_integration.md` — LLM 연결
5. `swa_04_notebook_console.md` — Colab 인터페이스
6. `swa_05_gradio_ui.md` — UI 구현
7. `swa_07_prompt_engineering.md` — 프롬프트 작성

---

## 이 패턴으로 만든 프로젝트

- **Hello-Clova-Agent** (2026-06): HyperCLOVA X Think-14B + LangGraph로 프레젠테이션 자동 생성
  - GitHub: `machine-artisan/Hello-Clova-Agent`
  - 상세 구현 이력: `wiki/implementation_log.md`

---

*작성일: 2026-06-14 | 작성자: Claude Sonnet 4.6*
