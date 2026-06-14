# SWA-10: imagegen 슬라이드 프롬프트 분석 — 우리 시스템 적용 가능 요소

> 원본: GPT-4o imagegen 기반 슬라이드 생성 프롬프트 (6슬라이드, 이미지 출력)  
> 작성일: 2026-06-14  
> 목적: 이미지 생성 전용 규칙 중 텍스트/HTML 덱에 이식 가능한 요소 선별

---

## 1. 원본 프롬프트 성격 분류

| 규칙 카테고리 | 이미지 생성 전용 | **우리에 적용 가능** |
|-------------|---------------|-------------------|
| 비율, 이미지 생성 명령(`imagegen`) | ❌ | — |
| 사진 처리, 3D 다이어그램, 일러스트 | ❌ | — |
| **언어 규칙 (한국어 주도 + 영어 강조)** | — | **✅ 프롬프트** |
| **영문 캐치프레이즈 (## 제목 위)** | — | **✅ 프롬프트 + HTML** |
| **슬라이드당 메시지 1개, 불릿 ≤3개** | — | **✅ 프롬프트** |
| **Cover / Intro / Body / Outro 구조** | — | **✅ 프롬프트 + 레이아웃** |
| **금지 패턴 (카드 나열, 번호뱃지 흐름도)** | — | **✅ 프롬프트** |
| 여백 7~8% safe margin, 30% 빈 공간 | 이미지용 | **✅ CSS 근사 적용** |
| 우상단 의도적 여백 | 이미지용 | 참고만 |

**이식 가능 비율: 약 60%** — 비주얼 디자인 철학이 텍스트/HTML 덱에도 유효함

---

## 2. 접목할 요소 상세

### 2-1. 언어 규칙: 한국어 주도 + 영어 선택적 강조 ★★★

**원본 규칙:**
> 본문은 한국어. 섹션 레이블, 짧은 캐치프레이즈, 지표, 제품/기술 용어, 핵심 비즈니스 키워드는 영어 사용.
> 결과는 한국어 주도이되 영어가 자연스럽게 강조되는 느낌.

**우리 현재 상태:** DIRECT_SLIDE_SYSTEM에 언어 규칙 없음 → LLM이 일관성 없이 혼용

**적용 방안:** DIRECT_SLIDE_SYSTEM에 추가
```
언어 규칙:
- 본문은 한국어 중심으로 작성한다
- 섹션 레이블, 수치/지표, 제품·기술 고유명사, 핵심 비즈니스 용어는 영어 그대로 사용
- 예: "AI 파이프라인 구축 전략" (O) vs "에이아이 파이프라인 구축 전략" (X)
```

---

### 2-2. 영문 캐치프레이즈 타이포그래피 ★★★

**원본 규칙:**
> 각 슬라이드 주 제목 바로 위에 1~2단어 영문 캐치프레이즈 배치.
> 예: `STEP 01 / INSPECT`, `PRIORITY 01 / INFRASTRUCTURE`, `NEW FEATURE / RELEASE`
> `COVER`, `INTRO`, `BODY`, `OUTRO` 같은 장르 명칭 금지.

**효과:** 텍스트만으로 레이어 감, 계층 감, 편집 디자인 느낌을 만드는 핵심 기법

**우리 적용:**
```
[LLM 출력 형식]
PIPELINE DESIGN / OVERVIEW
## AI 파이프라인 구조

[HTML 렌더링 결과]
<div class="catchphrase">PIPELINE DESIGN / OVERVIEW</div>
<h2>AI 파이프라인 구조</h2>
```

CSS:
```css
.reveal .catchphrase {
  font-family: "JetBrains Mono", monospace;
  font-size: 0.42em;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.60;
  margin-bottom: 0.25em;
  display: block;
}
/* 다크 배경 슬라이드에서 밝게 */
.reveal section[data-background-color^="#0"] .catchphrase,
.reveal section[data-background-color^="#1"] .catchphrase {
  opacity: 0.75;
}
```

---

### 2-3. 정보 밀도 규칙 ★★★

**원본 규칙:**
> - 슬라이드당 메시지 1개
> - 불릿 리스트 최대 3개 항목, 각 항목 1줄 이내
> - 다수 포인트보다 빠른 시각 이해 우선

**우리 현재 상태:** `"불릿 포인트 3~5개"` → 3~5 허용 → 종종 5개로 빽빽해짐

**적용 방안:** DIRECT_SLIDE_SYSTEM 수정
- `3~5개` → `최대 3개`
- `"슬라이드당 메시지 1개"` 명시 추가

---

### 2-4. 슬라이드 유형 구조 ★★★

**원본 구조:**
```
1. Cover    — 좌: 타이포/제목, 우: 키 비주얼
2. Intro    — 상: 제목+소개문, 하: 목차/로드맵 (아이콘+레이블 수평/수직 배열)
3~5. Body   — 상: 제목+소개문, 하: 다이어그램/차트/비주얼 집중
6. Outro    — 좌: 요약 메시지, 우: Next Action 리스트
```

**우리 현재 상태:**
- `cover / section / content / summary` 4종
- `intro` 없음 → 슬라이드 2가 content 타입으로 처리됨

**적용 방안:**
- `intro` 타입 추가 (슬라이드 2, 4장 이상 덱에서 활성)
- 내러티브 구조 프롬프트에 명시: Cover → Intro → Body × N → Outro

---

### 2-5. 금지 패턴 ★★

**원본 규칙:**
> - 카드 나열 금지: 3~4개 흰색 둥근 카드 + 아이콘 + 제목 + 설명 행 반복 레이아웃
> - 단계 흐름도 금지: 번호 뱃지 + 아이콘 + 레이블 + 화살표 AI 템플릿

**우리 LLM이 자주 만드는 패턴:**
- 12장짜리 덱에서 반복적인 불릿 리스트 패턴
- 단계를 `1. 수집 → 2. 처리 → 3. 출력` 텍스트로만 표현

**적용 방안:**
- 금지 패턴 프롬프트 추가
- 흐름도가 필요한 슬라이드에는 `:::mermaid` 사용 유도

---

### 2-6. Safe Margin / 여백 철학 ★★ (CSS 근사 적용)

**원본 규칙:**
> - 사방 여백 = 단축 변의 7~8%
> - 캔버스의 30% 이상은 빈 공간 유지

**우리 현재 상태:** Reveal.js 기본 패딩 적용 중

**적용 방안:** CSS에 여백 강화
```css
.reveal section {
  padding: 5vh 6vw !important;  /* 기존보다 넉넉한 safe margin */
}
/* 빈 공간 확보: 불릿을 3개로 제한하면 자연히 달성 */
```

---

## 3. 적용 불가 / 우리와 다른 부분

| 원본 규칙 | 이유 | 대안 |
|---------|------|------|
| 좌우 분할 레이아웃 (Cover: 좌 텍스트/우 비주얼) | 이미지 생성 전용 | future-slide S03 Split 레이아웃 장기 목표 |
| `imagegen` 순차 생성 | 이미지 생성 모델 없음 | Mermaid.js로 다이어그램 대체 |
| 사진/인물 처리 규칙 | 이미지 없음 | 향후 사전 생성 에셋 연동 시 참고 |
| 우상단 의도적 여백 | HTML 레이아웃으로 정밀 제어 어려움 | future-slide Custom Engine 장기 목표 |

---

## 4. 구현 우선순위

### Phase 2-A (즉시, 코드 변경)
1. **영문 캐치프레이즈** `md_to_html`에 감지 + CSS 추가
2. **언어 규칙** DIRECT_SLIDE_SYSTEM에 추가
3. **불릿 3개 제한** DIRECT_SLIDE_SYSTEM 수정
4. **intro 타입** SLIDE_COLORS + `_infer_slide_type` 추가
5. **금지 패턴** DIRECT_SLIDE_SYSTEM에 추가
6. **내러티브 구조** Cover→Intro→Body→Outro 명시

### Phase 2-B (중기)
7. **Safe margin CSS** Reveal.js 패딩 강화
8. **Outro 레이아웃** 우측에 Next Action 리스트 구조

---

## 5. 적용 후 예상 슬라이드 마크다운 형태

```
===SLIDE_1===
## LangGraph 기반 문서 자동화 시스템
부제목: 메모 한 장으로 완성하는 프레젠테이션
대상: 개발팀 내부 세미나 / 2026-06-14

===SLIDE_2===
AGENDA / OVERVIEW
## 오늘 발표 구성
- **Phase 1:** 현재 시스템 아키텍처
- **Phase 2:** 속도 최적화 결과
- **Phase 3:** 다음 단계 로드맵

===SLIDE_3===
PIPELINE DESIGN / CORE
## 3-Node 파이프라인 구조
:::mermaid
flowchart LR
  A[input_parser] --> B[slide_writer\nHyperCLOVA X] --> C[html_renderer]
:::

===SLIDE_4===
PERFORMANCE / RESULTS
## 속도 최적화 성과
- **CUDA Graph 활성화:** 21 → 32 tok/s (+50%)
- **1-call 통합:** 처리 시간 50% 단축
- **현재 목표:** 12슬라이드 기준 2~3분

===SLIDE_6===
NEXT STEPS / ACTION
## 다음 단계
- **레이아웃 확장:** 8종 패밀리 구현
- **RAG 연동:** sources/ 문서 컨텍스트 주입
- **이미지 에셋:** 사전 생성 보조 비주얼 연동
```

---

*문서 유형: SWA-10 외부 프롬프트 분석 + 접목 계획 | 작성일: 2026-06-14*
