"""
Node 4: html_renderer — Reveal.js HTML 생성

[역할] LLM 호출 없이 순수 Python으로 마크다운 슬라이드를 Reveal.js HTML로 변환합니다.
       Flutter 디자인 시스템 컬러와 Roboto 폰트를 적용합니다.
"""
import re
from agent.state import DeckState

# 슬라이드 타입별 배경색 (Flutter Material Design 3)
SLIDE_COLORS = {
    "cover":   {"bg": "#1565C0", "text": "#FFFFFF", "accent": "#90CAF9"},
    "section": {"bg": "#006A6A", "text": "#FFFFFF", "accent": "#80CBC4"},
    "content": {"bg": "#FFFFFF", "text": "#212121", "accent": "#1565C0"},
    "summary": {"bg": "#0D47A1", "text": "#FFFFFF", "accent": "#BBDEFB"},
}
DEFAULT_COLORS = SLIDE_COLORS["content"]


def md_to_html(md_text: str) -> str:
    """간단한 마크다운 → HTML 변환 (외부 라이브러리 미사용)"""
    lines = md_text.strip().splitlines()
    html_parts = []
    in_ul = False

    for line in lines:
        line = line.rstrip()
        if not line:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            continue

        if line.startswith("## "):
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            title = line[3:].strip()
            html_parts.append(f'<h2>{title}</h2>')
        elif line.startswith("# "):
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            title = line[2:].strip()
            html_parts.append(f'<h1>{title}</h1>')
        elif line.startswith("### "):
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            title = line[4:].strip()
            html_parts.append(f'<h3>{title}</h3>')
        elif re.match(r"^[-*]\s+", line):
            if not in_ul:
                html_parts.append('<ul>')
                in_ul = True
            item = re.sub(r"^[-*]\s+", "", line)
            # 인라인 볼드
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            html_parts.append(f'<li>{item}</li>')
        else:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            html_parts.append(f'<p>{text}</p>')

    if in_ul:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def build_section(slide_md: str, slide_info: dict) -> str:
    slide_type = slide_info.get("type", "content")
    colors = SLIDE_COLORS.get(slide_type, DEFAULT_COLORS)
    content_html = md_to_html(slide_md)

    bg_attr = f'data-background-color="{colors["bg"]}"'
    text_color = colors["text"]
    accent = colors["accent"]

    style = (
        f'style="color:{text_color};" '
        f'data-accent="{accent}"'
    )

    return f'<section {bg_attr} {style}>\n{content_html}\n</section>'


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>

  <!-- Reveal.js CDN -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/white.css">

  <!-- Google Fonts: Roboto (Flutter 공식 폰트) -->
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Google+Sans:wght@400;500;700&display=swap">

  <style>
    /* ===== Flutter Design System Theme ===== */
    :root {{
      --md-primary:       #1565C0;
      --md-secondary:     #006A6A;
      --md-surface:       #FFFFFF;
      --md-background:    #F8F9FF;
      --md-on-primary:    #FFFFFF;
      --md-on-surface:    #212121;
      --md-outline:       #73777F;
    }}

    .reveal {{
      font-family: 'Roboto', 'Google Sans', sans-serif;
      font-size: 28px;
    }}

    /* 제목 */
    .reveal h1 {{
      font-family: 'Google Sans', 'Roboto', sans-serif;
      font-weight: 700;
      font-size: 1.8em;
      line-height: 1.2;
      margin-bottom: 0.4em;
      text-shadow: none;
    }}
    .reveal h2 {{
      font-family: 'Google Sans', 'Roboto', sans-serif;
      font-weight: 500;
      font-size: 1.3em;
      border-bottom: 3px solid currentColor;
      padding-bottom: 0.2em;
      margin-bottom: 0.6em;
      opacity: 0.9;
    }}
    .reveal h3 {{
      font-weight: 500;
      font-size: 1.1em;
      opacity: 0.85;
      margin-bottom: 0.4em;
    }}

    /* 불릿 포인트 */
    .reveal ul {{
      list-style: none;
      padding-left: 0;
      margin: 0.5em 0;
    }}
    .reveal ul li {{
      position: relative;
      padding-left: 1.4em;
      margin-bottom: 0.5em;
      font-size: 0.88em;
      line-height: 1.5;
    }}
    .reveal ul li::before {{
      content: "▸";
      position: absolute;
      left: 0;
      opacity: 0.7;
    }}

    /* 단락 */
    .reveal p {{
      font-size: 0.85em;
      line-height: 1.6;
      opacity: 0.9;
    }}

    /* 흰색 슬라이드: 파란 강조 */
    .reveal section[data-background-color="#FFFFFF"] h2 {{
      border-color: var(--md-primary);
      color: var(--md-primary);
    }}
    .reveal section[data-background-color="#FFFFFF"] ul li::before {{
      color: var(--md-primary);
    }}

    /* 카드 스타일 (흰 배경) */
    .reveal section[data-background-color="#FFFFFF"] .card {{
      background: var(--md-background);
      border-radius: 8px;
      padding: 0.8em 1.2em;
      box-shadow: 0 1px 4px rgba(0,0,0,0.12);
      margin: 0.4em 0;
    }}

    /* 진행률 바 */
    .reveal .progress {{
      color: #90CAF9;
    }}

    /* 슬라이드 번호 */
    .reveal .slide-number {{
      font-family: 'Roboto', sans-serif;
      font-size: 14px;
      opacity: 0.6;
    }}
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
{slides_html}
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
  <script>
    Reveal.initialize({{
      hash: true,
      slideNumber: 'c/t',
      progress: true,
      controls: true,
      transition: 'slide',
      transitionSpeed: 'fast',
      center: true,
      width: 1280,
      height: 720,
    }});
  </script>
</body>
</html>"""


def _infer_slide_type(i: int, total: int, md: str) -> str:
    """outline 없을 때 위치 + 내용으로 슬라이드 타입 추론"""
    if i == 0:
        return "cover"
    if i == total - 1:
        return "summary"
    # 불릿이 없고 짧으면 section 슬라이드
    if md and not re.search(r"^[-*]\s", md, re.MULTILINE) and len(md) < 200:
        return "section"
    return "content"


def _extract_title(slides_md: list) -> str:
    """outline 없을 때 첫 슬라이드 ## 제목에서 발표 제목 추출"""
    if not slides_md:
        return "발표 슬라이드"
    m = re.search(r"^##\s+(.+)$", slides_md[0], re.MULTILINE)
    return m.group(1).strip() if m else "발표 슬라이드"


def render_html(state: DeckState) -> DeckState:
    """Node 3: 마크다운 슬라이드 리스트 → Reveal.js HTML"""
    if state.get("error"):
        return state

    slides_md = state["slides_md"]
    outline = state["outline"]
    slide_infos = outline.get("slides", [])
    title = outline.get("title") or _extract_title(slides_md)

    n = len(slide_infos) if slide_infos else len(slides_md)
    sections = []
    for i in range(n):
        md = slides_md[i] if i < len(slides_md) else ""
        if i < len(slide_infos):
            info = slide_infos[i]
        else:
            info = {"type": _infer_slide_type(i, n, md)}
        sections.append(build_section(md, info))

    slides_html = "\n\n".join(f"      {s}" for s in sections)
    html = HTML_TEMPLATE.format(title=title, slides_html=slides_html)

    return {
        **state,
        "html_output": html,
        "status": "✅ HTML 렌더링 완료 — 덱 생성 성공!",
    }
