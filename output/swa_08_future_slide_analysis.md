# SWA-08: future-slide 분석 및 Hello-Clova-Agent 적용 제안

> 분석 대상: https://github.com/bytonylee/future-slide  
> 작성일: 2026-06-14  
> 목적: future-slide의 설계 철학과 기술 선택을 분석하여 Hello-Clova-Agent에 적용 가능한 개선점 도출

---

## 1. future-slide 핵심 요약

**무엇인가:** OpenAI Codex용 슬라이드 생성 스킬 번들 (4단계 파이프라인)

**핵심 철학:** "단일 프롬프트는 예측 가능한 방식으로 실패한다" → 책임을 단계별로 분리

```
[Stage 1] slide-design      → DESIGN.md      (디자인 시스템 추출)
[Stage 2] slide-plan        → slide_plan.json (내러티브 기획)
[Stage 3] slide-prompt      → prompts.json   (페이지별 상세 지시)
[Stage 4] slide-render      → page_N.png / index.html (렌더링)
```

**출력 형태:** PNG 이미지(gpt-image 모드) 또는 HTML(tightened-slide 모드)

---

## 2. 아키텍처 비교

| 항목 | future-slide | Hello-Clova-Agent (현재) |
|------|-------------|------------------------|
| 실행 환경 | OpenAI Codex CLI | WSL2 / Google Colab |
| LLM | GPT-4o + DALL-E 3 | HyperCLOVA X Think-14B |
| 파이프라인 단계 | 4단계 (분리) | 3단계 (통합) |
| 디자인 명세 | `DESIGN.md` (추출 → 재사용) | `html_renderer.py`에 하드코딩 |
| 중간 아티팩트 | slide_plan.json, prompts.json | 없음 (직접 생성) |
| 레이아웃 | S01~S22 명명 패밀리 | cover/section/content/summary 4종 |
| 검증 | `validate-deck.mjs` 실행 | 없음 |
| 한국어 폰트 | Pretendard / SUIT | 시스템 폰트 (미지정) |
| llms.txt | ✅ 있음 | ❌ 없음 |
| 다크모드 | ✅ 있음 | ❌ 없음 |

---

## 3. index.html에서 발견한 기술 요소

### 3-1. `llms.txt` 연동 (★★★ 즉시 적용 가능)

```html
<link rel="alternate" type="text/plain" title="llms.txt" href="/llms.txt" />
```

Andrej Karpathy가 제안한 패턴: 사이트/프로젝트에 `/llms.txt`를 두어 LLM이 컨텍스트를 빠르게 파악할 수 있게 함.

→ **우리 적용**: `sources/md/llms.txt` 또는 프로젝트 루트에 `llms.txt` 추가

### 3-2. 한국어 최적화 폰트 (★★★ 즉시 적용 가능)

```html
<!-- 한국어 최적 폰트 -->
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css" />
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/sunn-us/SUIT@2/fonts/variable/woff2/SUIT-Variable.css" />

<!-- 아이콘 -->
<link rel="stylesheet"
  href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css" />
```

현재 우리 Reveal.js HTML은 폰트 미지정 → 브라우저 기본 폰트 사용.

→ **우리 적용**: `html_renderer.py`의 Reveal.js 템플릿에 Pretendard 추가

### 3-3. 다크/라이트 모드 (★★ 중기 적용)

```javascript
// localStorage 기반 테마 토글
var theme = localStorage.getItem("fss-theme") || "light";
document.documentElement.classList.toggle("dark", theme === "dark");
```

→ **우리 적용**: Reveal.js 테마 선택 + 다크 테마 추가 (`data-theme-slug` 파라미터)

### 3-4. i18n (ko/en) 지원 (★ 장기)

```javascript
var locale = localStorage.getItem("fss-locale");
if (!locale) {
  locale = navigator.language.startsWith("ko") ? "ko" : "en";
}
```

### 3-5. Schema.org 구조화 데이터 (★ 장기)

```json
{ "@type": "SoftwareApplication", "name": "Future Slide Skill" }
```

→ 프로젝트를 공개 서비스로 전환할 때 SEO/LLM 인식을 위해 적용

### 3-6. 접근성 (a11y)

```html
<a href="#main" class="skip-link">Skip to content</a>
<!-- aria-label, aria-hidden 적극 사용 -->
```

---

## 4. 핵심 설계 철학에서 배울 점

### 4-1. "단일 프롬프트는 예측 가능한 방식으로 실패한다"

future-slide가 열거한 단일 LLM 호출의 실패 패턴:

| 실패 패턴 | Hello-Clova-Agent 현재 상태 |
|---------|--------------------------|
| 테마 추출 전에 슬라이드를 쓰기 시작 | 테마 하드코딩이므로 해당 없음 |
| 디자인 분석과 내용 전략을 혼합 | `slide_writer`가 둘 다 담당 → **해당** |
| 내러티브 흐름 없이 페이지 프롬프트 생성 | `DIRECT_SLIDE_SYSTEM`에 내러티브 규칙 있으나 약함 → **부분 해당** |
| 슬라이드 간 레이아웃 일관성 상실 | 4종 레이아웃만으로 단조로움 → **해당** |
| 내용보다 디자인 이미지에 과적합 | 우리는 텍스트 입력이라 해당 없음 |
| 프롬프트 작성 후 렌더링 안 함 | LLM → HTML 자동 렌더링 → 해당 없음 |

**결론**: 우리의 현재 3-node 단일 호출 방식은 속도상 이점이 있으나, 내러티브 품질과 레이아웃 다양성에서 한계.

### 4-2. `DESIGN.md` 패턴 — 디자인 시스템의 분리

future-slide의 핵심 통찰: **디자인 시스템을 LLM이 생성 가능한 텍스트 명세로 분리하면 재사용 가능**

```
# DESIGN.md 예시 구조
## Color system
primary: #1A237E, accent: #E91E63

## Layout families
S01: Title only (cover)
S02: Two-column (left text, right image)
S08: Full-bleed map/image
...

## Typography rules
H1: 48px bold, H2: 32px medium
Korean: Pretendard, English: Barlow
```

→ **우리 적용**: `html_renderer.py`에 하드코딩된 스타일을 `DESIGN.md` 또는 `theme.json`으로 외부화

---

## 5. 즉시 적용 가능한 개선 (Phase 2 후보)

### 5-1. ★★★ 한국어 폰트 (Pretendard) 적용

**현재 문제**: Reveal.js 슬라이드가 OS 기본 폰트 사용 → 기업 슬라이드 느낌 미흡  
**수정 대상**: `agent/nodes/html_renderer.py`의 HTML 템플릿  
**변경 내용**:

```html
<!-- Reveal.js <head>에 추가 -->
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin />
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css" />
<style>
  :root { --r-main-font: 'Pretendard Variable', 'Pretendard', sans-serif; }
  .reveal { font-family: var(--r-main-font); }
</style>
```

**효과**: 한국어 가독성 대폭 향상, 기업 프레젠테이션 품질

---

### 5-2. ★★★ 레이아웃 패밀리 확장 (4종 → 8종)

**현재 4종**: cover / section / content / summary  
**future-slide 참고 확장안**:

| ID | 이름 | 구조 | 용도 |
|----|------|------|------|
| L01 | cover | 중앙 집중 제목 | 표지 |
| L02 | section | 섹션 제목 + 부제 | 챕터 구분 |
| L03 | content | 불릿 리스트 | 일반 내용 |
| L04 | two-column | 좌: 텍스트, 우: 빈 영역 | 비교/대조 |
| L05 | highlight | 큰 숫자/통계 강조 | KPI, 수치 강조 |
| L06 | timeline | 수평 타임라인 | 일정, 과정 |
| L07 | quote | 큰 인용구 | 핵심 메시지 |
| L08 | summary | 체크리스트 + 결론 | 마무리 |

**프롬프트 변경**: `DIRECT_SLIDE_SYSTEM`에 레이아웃 힌트 추가

```
===SLIDE_3===
layout: two-column
## 비교 분석
왼쪽: 기존 방식
- 항목 1
오른쪽: 새로운 방식
- 항목 1
```

---

### 5-3. ★★★ `llms.txt` 추가

**목적**: 다음 LLM이 프로젝트를 5초 안에 파악  
**위치**: 프로젝트 루트 `llms.txt`  
**내용 구조**:

```
# Hello-Clova-Agent

프레젠테이션 자동 생성 에이전트 (HyperCLOVA X + LangGraph + Gradio)

## 현재 상태
- vLLM 0.19.1, BnB 4-bit, CUDA Graph 활성 (31.7 tok/s)
- 3-node 파이프라인: input_parser → slide_writer → html_renderer
- Gradio 3탭 UI: http://localhost:7860

## 핵심 파일
- agent/graph.py: LangGraph 파이프라인
- agent/nodes/slide_writer.py: 슬라이드 생성 (DIRECT_SLIDE_SYSTEM)
- ui/app.py: Gradio UI
- sources/md/handoff_memo.md: 상세 핸드오프 메모

## 금지 사항
- vLLM 버전 변경 금지 (0.19.1 고정)
- transformers 버전 다운그레이드 금지 (5.12.0 고정)
- --enforce-eager 재추가 금지 (CUDA Graph 활성 상태)
```

---

### 5-4. ★★ 내러티브 구조 강제 (프롬프트 개선)

**현재 문제**: `DIRECT_SLIDE_SYSTEM`이 슬라이드 수와 형식만 규정, 스토리 흐름 없음  
**future-slide 참고**: 설득력 있는 내러티브 흐름 명시

```python
DIRECT_SLIDE_SYSTEM = """...
내러티브 흐름 (반드시 준수):
- 슬라이드 1: 표지 (제목, 대상, 날짜)
- 슬라이드 2: 핵심 메시지 or 문제 정의 (한 문장)
- 슬라이드 3~(N-2): 본론 (근거, 분석, 데이터)
- 슬라이드 (N-1): 실행 방안 or 권고사항
- 슬라이드 N: 요약 및 결론
..."""
```

---

### 5-5. ★★ 슬라이드 계획 JSON 도입 (선택적 2-call 복귀)

**트레이드오프**:

| 방식 | 속도 | 품질 | 현재 선택 |
|------|------|------|----------|
| 1-call (현재) | ~90s | 보통 | ✅ |
| 2-call (plan+write) | ~3분 | 높음 | 옵션 |

**2-call 방식의 장점** (future-slide 철학 적용):
- 1차 호출: 목차 JSON 생성 (각 슬라이드의 역할, 레이아웃, 핵심 메시지)
- 2차 호출: 목차를 보며 상세 내용 작성 → 일관성 대폭 향상

**구현 제안**: Gradio에서 속도/품질 모드 선택 슬라이더 추가

```python
# Gradio에서 품질 모드 선택
mode = gr.Radio(["⚡ 빠른 생성 (1-call)", "✨ 고품질 생성 (2-call)"], value="⚡ 빠른 생성 (1-call)")
```

---

### 5-6. ★ 다크 테마 / 테마 선택

**현재**: Flutter Material 3 라이트 테마 고정  
**개선**: Reveal.js 내장 테마 선택 + 다크 테마 지원

```python
# html_renderer.py에 테마 파라미터 추가
THEMES = {
    "기본 (파란색)": "white",
    "다크": "black",
    "기업 (회색)": "simple",
    "한국어 최적": "serif",
}
```

---

## 6. 적용 불가 / 우리와 다른 부분

| future-slide 기능 | 이유 | 대안 |
|-----------------|------|------|
| GPT-4o Vision (참고 이미지 분석) | 멀티모달 LLM 없음 | 사용자가 테마 선택 UI로 대체 |
| DALL-E 3 이미지 생성 | 이미지 생성 LLM 없음 | 텍스트+HTML 슬라이드 유지 |
| `validate-deck.mjs` (Node.js) | 의존성 추가 | Python HTML 파서로 구현 가능 |
| Codex Skill Bundle (`$skill-name`) | Claude Code CLI 환경 | LangGraph 노드 패턴 유지 |
| 22가지 레이아웃 패밀리 (S01~S22) | 현재 LLM 출력 파싱 복잡도 증가 | 8종 확장으로 절충 |

---

## 7. 추가 분석을 위해 제공하면 좋은 자료

아래 파일들을 추가로 확인하면 더 구체적인 적용 방안을 도출할 수 있습니다:

### 7-1. 필수 (높은 가치)

1. **`skills/tightened-slide/assets/template.html`**  
   → S01~S22 레이아웃 패밀리의 실제 HTML CSS 구현  
   → 우리 Reveal.js 템플릿 개선에 직접 적용 가능

2. **`templates/DESIGN_TEMPLATE.md`**  
   → DESIGN.md 표준 형식  
   → 우리의 테마 시스템 외부화 설계에 활용

3. **`skills/tightened-slide/SKILL.md`**  
   → tightened-slide 프롬프트 원문  
   → 우리 `DIRECT_SLIDE_SYSTEM` 개선에 직접 참고

### 7-2. 선택 (중간 가치)

4. **`skills/gpt-image-slide-plan/SKILL.md`** (또는 `gpt-image-slide/SKILL.md`)  
   → 2-call 방식의 plan 프롬프트 원문

5. **실제 생성된 `slide_plan.json` 예시**  
   → 중간 아티팩트 구조 파악

6. **실제 생성된 `slide_prompts.json` 예시**  
   → 페이지별 지시 구조

### 7-3. 없어도 되는 것

- `site/` 디렉토리 (랜딩 페이지 코드, 슬라이드 생성과 무관)
- `public/diagram/` (다이어그램 이미지)

---

## 8. 우선순위별 적용 로드맵

### Phase 2-A (단기, 1일 이내)

1. **Pretendard 폰트** `html_renderer.py` 에 추가 (30분)
2. **`llms.txt`** 프로젝트 루트에 추가 (15분)
3. **내러티브 흐름 프롬프트** `DIRECT_SLIDE_SYSTEM` 개선 (1시간)

### Phase 2-B (중기, 1주 이내)

4. **레이아웃 패밀리 8종** HTML 템플릿 + 프롬프트 통합 (2일)
5. **테마 선택 UI** Gradio에 추가 (1일)
6. **속도/품질 모드 선택** Gradio + 선택적 2-call (1일)

### Phase 2-C (장기, 검토 필요)

7. **`DESIGN.md` 패턴** — 디자인 시스템 외부화
8. **슬라이드 검증** — Python HTML 파서로 구조 검증
9. **RAG 연동** — `sources/` 디렉토리 문서를 컨텍스트로 주입

---

*문서 유형: SWA-08 외부 프로젝트 분석 및 적용 제안 | 작성일: 2026-06-14*
