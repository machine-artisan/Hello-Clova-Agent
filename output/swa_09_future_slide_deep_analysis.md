# SWA-09: future-slide 심층 분석 + Mermaid.js 통합 계획

> 분석 파일: template.html / DESIGN_TEMPLATE.md / SKILL.md  
> 작성일: 2026-06-14  
> 핵심 발견: future-slide는 Reveal.js를 쓰지 않는다 → 완전 자체 엔진

---

## 1. 가장 중요한 발견: Custom Deck Engine

template.html을 열면 첫 번째로 눈에 띄는 것 — **Reveal.js가 없다**.

```html
<!-- future-slide template.html의 의존성 전부 -->
<link href="https://fonts.googleapis.com/css2?family=Inter...&family=Noto+Sans+KR..."> 
<!-- 그게 끝. Reveal.js CDN 없음. -->
```

네비게이션, 슬라이드 전환, 인덱스 오버레이 — 모두 42줄짜리 순수 JS로 직접 구현:

```javascript
document.addEventListener('keydown', event => {
  if(event.key === 'ArrowRight') show(current + 1);
  if(event.key === 'ArrowLeft')  show(current - 1);
  if(event.key === 'Escape')     openIndex();
  if(event.key === 'b')          setLowPower(toggle);
});
// + 마우스휠, 터치 스와이프
```

**왜 이게 중요한가:**  
Reveal.js = 약 200KB CDN 의존 + 고정 레이아웃 규칙 + 제한된 커스터마이징  
Custom engine = 완전 제어 + 오프라인 작동 + 레이아웃 무한 확장

---

## 2. template.html 디자인 시스템 분석

### 2-1. CSS 변수 기반 토큰 시스템

```css
:root {
  /* 컬러 */
  --paper: #fafaf8;         /* 배경 (순백이 아닌 약간 따뜻한 흰색) */
  --ink:   #0a0a0a;         /* 텍스트 (순검이 아닌 부드러운 검정) */
  --accent: #002FA7;        /* International Klein Blue — 포인트 1색만 허용 */
  --grey-1: #f0f0ee;        /* 카드 배경 */
  --grey-2: #d4d4d2;        /* 테두리 */
  --grey-3: #737373;        /* 보조 텍스트 */

  /* 폰트 */
  --font-en: "Inter", "Helvetica Neue", system-ui;
  --font-ko: "SUIT", "Pretendard", "Noto Sans KR";
  --mono:    "JetBrains Mono";
  
  /* 스페이싱 (8pt grid) */
  --sp-3:8px; --sp-4:12px; --sp-5:16px; --sp-6:24px;
  --sp-7:32px; --sp-8:40px; --sp-9:48px; --sp-10:64px;
}

/* 한국어 모드 전환 — html 속성 하나로 */
html[data-language="ko"] { --sans: var(--font-ko); }
```

**핵심 원칙 (SKILL.md에서 추출):**
- **포인트 컬러 1개만** (`--accent`)
- **그라디언트, 그림자, 둥근 모서리, 유리 효과, 네온, 3D 금지**
- 큰 제목: `font-weight: 200` (초경량) + `min(Xvw, Yvh)` 반응형 크기
- 본문: `font-weight: 300` (경량)

### 2-2. 슬라이드 모드 시스템

```html
<!-- 3가지 배경 모드 -->
<section class="slide">         <!-- 기본: paper 배경, ink 텍스트 -->
<section class="slide dark">    <!-- 다크: ink 배경, white 텍스트 -->
<section class="slide accent">  <!-- 강조: Klein Blue 배경, white 텍스트 -->

<!-- 분할 레이아웃 -->
<section class="slide split">   <!-- 좌우 2분할 (각각 다른 배경 가능) -->
```

### 2-3. S01~S22 레이아웃 패밀리 (SKILL.md)

| ID | 이름 | 특징 | 한국어 메모 덱 활용 |
|----|------|------|------------------|
| S01 | Index Cover | ASCII 애니 배경, 표지 | 덱 시작 슬라이드 |
| S02 | Vertical Timeline + KPI | 세로 타임라인 | 프로젝트 이력 |
| S03 | Split Statement | 좌: 큰 주장 / 우: 근거 | 핵심 메시지 강조 |
| S04 | Six Cells | 6개 카드 그리드 | 기능 목록 |
| S05 | Three Layers | 3단 구조 | 계층 분석 |
| S06 | KPI Tower | 막대 높이 비교 | 수치 비교 |
| S07 | Horizontal Bar | 가로 막대 차트 | 순위, 점유율 |
| S08 | Duo Compare | 좌/우 비교 | Before/After |
| S09 | Dot Matrix Statement | 도트 패턴 + 큰 텍스트 | 임팩트 한 문장 |
| S10 | Split Closing | 좌: 결론 / 우: 액션아이템 | 마무리 슬라이드 |
| S11 | Horizontal Timeline | 가로 타임라인 | 로드맵, 일정 |
| S12 | Manifesto + Ink Banner | 선언문 + 하단 다크 배너 | 비전 선언 |
| S13 | Three Forces | 3개 주요 동인 | 분석 결과 |
| S14 | Loop Form | 순환 다이어그램 | 프로세스 |
| S15 | Matrix + Hero Stat | 그리드 + 큰 숫자 | 데이터 요약 |
| S16 | Multi-card Brief | 3×2 카드 | 요약 정리 |
| S17 | System Diagram | 시스템 구조 | 아키텍처 |
| S18 | Why Now | 3컬럼 근거 + 큰 숫자 | 시장 타이밍 |
| S19 | Four Cards | 4개 카드 | 4분면 정리 |
| S20 | Stacked KPI Ledger | 원장 형식 KPI | 재무/성과 지표 |
| S21 | Tech Spec Sheet | 사양 + 스펙 바 | 기술 스펙 |
| S22 | Image Hero | 전체 이미지 | 비주얼 임팩트 |

### 2-4. ASCII 배경 애니메이션 (주목할 기능)

```javascript
// Canvas API로 '01/|+-' 문자를 격자로 그림 (0.18 투명도)
// sin() 함수로 시간에 따라 문자가 천천히 변함
// 저전력 모드(B키)에서 off
const chars = '01/|+-';
const n = Math.floor(Math.abs(Math.sin(x*.004 + y*.006 + time*.001)) * chars.length);
ctx.fillText(chars[n], x, y);
```

**우리 데크에 적용 가능**: accent 슬라이드(표지)에 한정해서 적용하면 효과적.

---

## 3. DESIGN_TEMPLATE.md 활용 방안

10섹션 디자인 명세 포맷:

```
1. Design Intent (의도/인상)
2. Color System (색상 시스템)
3. Typography System (타이포그래피)
4. Layout Families (레이아웃 유형)
5. Grid & Spacing (격자/여백)
6. Components (컴포넌트)
7. Data Visualization (데이터 시각화)
8. Imagery (이미지 처리)
9. Slide-System Rules (슬라이드 규칙)
10. Anti-Patterns (금지 패턴)
```

→ **우리 적용**: `html_renderer.py`의 하드코딩 스타일을 `theme.json`으로 외부화  
→ LLM에게 "이 테마로 렌더링해줘"가 가능해짐

---

## 4. SKILL.md에서 배울 7가지

1. **Planning table 먼저**: `page → layout → reason → image slot` 표 작성 후 코딩
2. **Preflight**: 사용할 CSS 클래스가 템플릿에 실제로 존재하는지 확인 후 진행
3. **레이아웃 다양성 강제**: 7~8페이지 덱 → 최소 6가지 다른 레이아웃 사용
4. **언어 모드 명시**: `html lang="ko" data-language="ko"` — CSS 자동 전환
5. **SVG는 기하학만**: 레이블은 반드시 HTML로 (접근성 + 편집 편의)
6. **검증 단계 필수**: 납품 전 validate-deck 실행
7. **이미지 먼저 선택, 프롬프트 나중**: 레이아웃 슬롯 확정 후 이미지 생성

---

## 5. Mermaid.js 통합 가능성 분석

### 5-1. 우리 상황에서의 기술적 검토

```
[현재 흐름]
html_renderer.py → deck HTML 생성
ui/app.py → <iframe srcdoc="..."> 으로 Gradio에 표시
```

**srcdoc iframe에서 Mermaid 동작 여부:**

| 조건 | 결과 |
|------|------|
| `<iframe srcdoc="...">` (sandbox 없음) | ✅ 스크립트 실행됨 |
| `<iframe srcdoc="..." sandbox>` | ❌ 스크립트 차단 |
| CDN 스크립트 in srcdoc | ✅ 인터넷 있으면 로드됨 |
| Mermaid `securityLevel: 'loose'` | ✅ srcdoc 내 정상 동작 |
| Mermaid `securityLevel: 'sandbox'` | ⚠️ 이중 iframe 문제 발생 |

우리 코드(`ui/app.py`)에 `sandbox` 속성이 없으므로 **Mermaid 동작 가능**.

**단, 현재 이스케이핑 방식에 문제 있음:**
```python
# 현재 (불완전)
safe_html = html.replace('"', "&quot;")  # & → &amp; 안 함

# 권장 (완전한 HTML 어트리뷰트 이스케이프)
import html as html_module
safe_html = html_module.escape(deck_html, quote=True)
```
Mermaid 다이어그램 텍스트에 `&`나 `<`가 포함되면 현재 방식에서 깨짐.

### 5-2. Mermaid.js 적용 최소 코드

```html
<!-- html_renderer.py의 <head>에 추가 -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({
    startOnLoad: true,
    theme: 'base',
    themeVariables: {
      primaryColor: '#002FA7',    /* --accent 와 일치 */
      primaryTextColor: '#ffffff',
      primaryBorderColor: '#002FA7',
      lineColor: '#525252',
      background: '#fafaf8',      /* --paper 와 일치 */
      fontFamily: '"Pretendard Variable", "Pretendard", "Noto Sans KR", sans-serif',
    },
    securityLevel: 'loose',
  });
</script>
```

슬라이드 내 사용:
```html
<div class="mermaid" style="width:100%;max-height:50vh">
flowchart LR
  A[입력] --> B[LLM 처리] --> C[HTML 출력]
</div>
```

### 5-3. 메모 덱에 유용한 Mermaid 다이어그램 유형

| 타입 | 문법 | 메모 덱 활용 예 |
|------|------|----------------|
| `flowchart` | `flowchart TD` | 의사결정 흐름, 프로세스 단계 |
| `mindmap` | `mindmap` | 아이디어 구조, 목차 시각화 |
| `gantt` | `gantt` | 일정, 로드맵 |
| `quadrantChart` | `quadrantChart` | 우선순위 매트릭스 |
| `timeline` | `timeline` | 이력, 마일스톤 |
| `sequenceDiagram` | `sequenceDiagram` | 시스템 간 상호작용 |

**예시 — 프로젝트 로드맵 슬라이드:**
```
:::mermaid
gantt
  title 개발 로드맵
  dateFormat YYYY-MM
  section Phase 1
  환경 구성    :done, 2026-05, 1M
  기본 기능    :done, 2026-06, 1M
  section Phase 2
  다이어그램   :active, 2026-07, 1M
  테마 시스템  :2026-08, 1M
:::
```

**예시 — 시스템 구조 슬라이드:**
```
:::mermaid
flowchart TD
  U[사용자 입력] --> G[Gradio UI]
  G --> P[LangGraph 파이프라인]
  P --> L[vLLM\nHyperCLOVA X]
  L --> P
  P --> H[Reveal.js HTML]
  H --> O[output/deck_*.html]
:::
```

### 5-4. LLM 프롬프트 통합 전략

`DIRECT_SLIDE_SYSTEM`에 다이어그램 옵션 추가:

```python
DIRECT_SLIDE_SYSTEM = """...기존 내용...

다이어그램 사용 (선택):
슬라이드 내에 흐름/구조를 시각화해야 할 때 아래 형식 사용:

:::mermaid
flowchart LR
  A[시작] --> B[처리] --> C[완료]
:::

지원 다이어그램: flowchart (흐름), mindmap (마인드맵), gantt (일정), timeline (이력)
텍스트만으로 충분한 경우에는 다이어그램 불필요"""
```

파서에서 처리:
```python
# slide_writer.py 또는 html_renderer.py
import re

def convert_mermaid_blocks(md: str) -> str:
    """:::mermaid ... ::: 블록을 <div class='mermaid'>로 변환"""
    return re.sub(
        r':::mermaid\n(.*?):::',
        lambda m: f'<div class="mermaid">\n{m.group(1)}</div>',
        md,
        flags=re.DOTALL
    )
```

---

## 6. Reveal.js vs Custom Engine 비교

future-slide 분석 후 우리의 선택지:

| 항목 | Reveal.js (현재) | Custom Engine (future-slide 방식) |
|------|-----------------|----------------------------------|
| 초기 구현 | 쉬움 (이미 작동) | 어려움 (재작성 필요) |
| CDN 의존 | Reveal.js ~200KB | 폰트만 (구글폰트 CDN) |
| 레이아웃 자유도 | 제한적 | 완전 자유 |
| 오프라인 작동 | ❌ (CDN 필요) | ✅ (스크립트 inline) |
| S01~S22 레이아웃 구현 | 어려움 | 직접 CSS로 구현 |
| 유지보수 | Reveal.js 버전 의존 | 직접 관리 |
| 마이그레이션 비용 | 0 | 높음 (html_renderer.py 전면 재작성) |

**권장 방향**: 
- **단기**: Reveal.js 유지 + Mermaid.js + Pretendard 폰트 추가
- **장기**: Custom engine으로 마이그레이션 (S01~S22 레이아웃 구현 시)

---

## 7. 즉시 구현 계획 (Phase 2-A)

### 변경 파일 1: `agent/nodes/html_renderer.py`

```python
# 변경 1: HTML <head>에 Pretendard + Mermaid 추가
HEAD_ADDITIONS = """
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    primaryColor: '#1565C0',
    primaryTextColor: '#ffffff',
    lineColor: '#525252',
    background: '#ffffff',
    fontFamily: '"Pretendard Variable","Pretendard","Noto Sans KR",sans-serif',
  },
  securityLevel: 'loose',
});
</script>
<style>
  .reveal { font-family: "Pretendard Variable","Pretendard","Noto Sans KR",sans-serif !important; }
  .mermaid svg { max-height: 45vh; width: 100%; }
</style>
"""

# 변경 2: :::mermaid 블록 변환 함수 추가
def _convert_mermaid(md: str) -> str:
    return re.sub(
        r':::mermaid\n(.*?):::',
        lambda m: f'<div class="mermaid">{m.group(1)}</div>',
        md, flags=re.DOTALL
    )
```

### 변경 파일 2: `ui/app.py`

```python
# 변경: srcdoc 이스케이핑 강화
import html as html_module

def _load_deck(filename: str):
    html = path.read_text(encoding="utf-8")
    safe_html = html_module.escape(html, quote=True)  # & < > " ' 모두 처리
    iframe = f'<iframe srcdoc="{safe_html}" style="..." allowfullscreen></iframe>'
```

### 변경 파일 3: `agent/prompts.py`

```python
# DIRECT_SLIDE_SYSTEM에 다이어그램 옵션 추가
# (텍스트 맨 끝에 붙임)
DIAGRAM_ADDON = """
흐름이나 구조를 시각화할 때 (선택사항):
:::mermaid
flowchart LR
  A[시작] --> B[처리] --> C[완료]
:::

지원 타입: flowchart / mindmap / gantt / timeline / sequenceDiagram
다이어그램은 내용이 명확히 도움되는 경우에만 사용"""
```

---

## 8. 추후 나중에 이미지 에셋 연동 방안

사용자 언급 "나중에 이미지 에셋을 미리 생성해서 보조설명으로 사용" →

**Phase 3 설계안:**

```
[사전 생성 단계]
키워드 추출 → 이미지 생성 API (DALL-E / Stable Diffusion) → images/deck_XYZ/
   ↑
   sources/raw/ 또는 사용자 업로드

[덱 생성 시]
slide_writer.py가 슬라이드 내용 작성 시 이미지 참조 태그 포함:
  [[image:인공지능_개념도]]
  
html_renderer.py가 images/ 폴더에서 해당 이미지 찾아 <img src="..."> 삽입
```

future-slide의 이미지 네이밍 규칙 참고:
```
images/{page}-{semantic-name}.{ext}
예: images/03-system-diagram.png
    images/07-kpi-comparison.jpg
```

S22 레이아웃(Image Hero) 구현 시 이 이미지들이 전체화면으로 활용됨.

---

## 9. 추가 분석이 필요한 자료 (현재 미확보)

| 파일 | 위치 | 가치 |
|------|------|------|
| `references/layout-lock.md` | `skills/tightened-slide/references/` | S01~S22 HTML 스켈레톤 |
| `references/layouts.md` | 동일 | 레이아웃별 마크업 예시 |
| `references/themes.md` | 동일 | IKB 외 다른 테마 정의 |
| `scripts/validate-deck.mjs` | `skills/tightened-slide/scripts/` | 덱 검증 로직 |
| 실제 생성된 덱 예시 | `examples/` 또는 README | 완성 결과물 확인 |

---

*문서 유형: SWA-09 심층 분석 + Mermaid.js 통합 계획 | 작성일: 2026-06-14*
