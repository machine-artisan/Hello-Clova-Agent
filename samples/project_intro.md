# 발표 생성 요청 — Local Deck Gen Agent 프로젝트 소개

이 발표는 "Local Deck Gen Agent" 프로젝트를 기업 담당자들에게 소개하는 내용입니다.
아래 주제를 포함한 **12페이지** 분량의 슬라이드를 생성해 주세요.

## 포함할 주제

1. **프로젝트 개요**
   - Gamma, SkyAI, Manus 같은 발표 자동 생성 서비스를 로컬에서 직접 구현
   - 오프라인 동작, 데이터 외부 유출 없음, 도메인 지식 누적 가능

2. **기술 스택**
   - LangGraph: 멀티 에이전트 파이프라인 프레임워크
   - HyperCLOVA X SEED: 한국어 특화 sLLM
   - vLLM: OpenAI 호환 로컬 API 서버
   - Gradio: 웹 UI 프레임워크
   - Reveal.js: HTML 기반 슬라이드 렌더링

3. **핵심 개념: 웹서버 · 앱서버 · API 서버**
   - 세 가지 서버 계층의 역할 구분 및 실제 코드와의 대응관계

4. **LangGraph 4-노드 파이프라인**
   - Node 1: input_parser (입력 분석)
   - Node 2: outline_generator (목차 생성 — LLM 호출)
   - Node 3: slide_writer (내용 작성 — LLM 호출)
   - Node 4: html_renderer (HTML 변환)

5. **Phase 1 구현 결과 및 데모**
   - Colab에서 git pull → 3단계로 즉시 체험 가능

6. **Phase 2 로드맵**
   - RAG 기반 도메인 지식 연동 (LLM-Wiki 개념)
   - 동적 CSS 테마 자동 생성

7. **기대 효과 및 결론**
   - 에이전트 기술의 실용적 이해
   - 도메인 지식 누적 체계 구축

**대상 청중:** 기업 담당자 (기술 배경 비전문가)
**스타일:** Flutter 디자인 시스템, 파란 계열 색상, 깔끔하고 전문적인 느낌
