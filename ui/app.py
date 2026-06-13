"""
Gradio 웹 앱 — Local Deck Gen Agent UI

# ── 프로젝트 루트를 sys.path에 추가 ──────────────────────────────────────────
# 원인: `python ui/app.py` 실행 시 Python은 스크립트 위치(ui/)만 경로에 추가하며
#       프로젝트 루트를 자동으로 추가하지 않습니다.
#       이 코드가 없으면 `from agent.graph import graph`가 ModuleNotFoundError를 냅니다.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
# ─────────────────────────────────────────────────────────────────────────────

[개념] 웹서버(Web Server)란?
이 파일이 웹서버 역할을 합니다. Gradio가 HTTP 서버를 내장하여 브라우저의 요청을 받고,
에이전트 파이프라인(app server)에 작업을 위임한 뒤 결과를 HTML로 응답합니다.

                 브라우저
                    │  HTTP
          ┌─────────▼──────────┐
          │   Gradio 웹서버    │  ← 이 파일
          │  (app.py, :7860)   │
          └─────────┬──────────┘
                    │  Python 함수 호출
          ┌─────────▼──────────┐
          │  LangGraph 파이프  │  ← agent/graph.py
          │  (앱 서버 역할)    │
          └─────────┬──────────┘
                    │  HTTP (OpenAI API)
          ┌─────────▼──────────┐
          │   vLLM API 서버    │  ← localhost:8000
          │  (LLM 엔진)        │
          └────────────────────┘
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import gradio as gr
from agent.graph import graph
from agent.state import DeckState

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SAMPLE_PROMPT = """\
이 발표는 "Local Deck Gen Agent" 프로젝트를 소개하는 내용으로,
아래 주제를 포함한 12페이지 분량의 슬라이드를 생성해 주세요:

1. 프로젝트 개요 (Gamma, SkyAI 같은 발표 자동 생성 서비스를 로컬에서 구현)
2. 기술 스택 소개 (LangGraph, HyperCLOVA X, vLLM, Gradio, Reveal.js)
3. 시스템 아키텍처 (웹서버 → 앱서버 → API 서버 → LLM 계층 설명)
4. LangGraph 4-노드 에이전트 파이프라인 상세 설명
5. Phase 1 구현 결과 및 데모
6. Phase 2 계획 (RAG 연동, 동적 테마 자동 생성)
7. 기대 효과 및 결론

대상 청중: 기업 담당자 (기술 배경 비전문가)
스타일: Flutter 디자인 시스템, 파란 계열, 깔끔하고 전문적인 느낌
"""


def generate_deck(prompt: str, progress=gr.Progress()):
    """Gradio 이벤트 핸들러 — 에이전트 파이프라인 실행 및 결과 반환"""
    if not prompt.strip():
        return (
            "<p style='color:red'>⚠️ 내용을 입력해 주세요.</p>",
            None,
            "입력 없음",
        )

    llm_model = os.getenv("LLM_MODEL")
    llm_base = os.getenv("LLM_API_BASE")
    if not llm_model or not llm_base:
        missing = ", ".join(
            k for k, v in {"LLM_MODEL": llm_model, "LLM_API_BASE": llm_base}.items() if not v
        )
        return (
            f"<p style='color:red'>❌ 환경변수 미설정: {missing}<br>"
            "셀 3/6과 셀 5/6을 실행한 뒤 다시 시도하세요.</p>",
            None,
            f"오류: {missing} 미설정",
        )

    progress(0, desc="Node 1: 입력 파싱 중...")

    initial_state: DeckState = {
        "user_prompt": prompt,
        "num_slides": 10,
        "parsed_request": {},
        "outline": {},
        "slides_md": [],
        "html_output": "",
        "status": "시작",
        "error": None,
    }

    # 스트리밍 방식: 각 노드 완료마다 progress 업데이트
    final_state = None
    try:
        for i, state_update in enumerate(
            graph.stream(initial_state, stream_mode="updates")
        ):
            node_name = list(state_update.keys())[0]
            node_state = list(state_update.values())[0]
            status_msg = node_state.get("status", "처리 중...")

            progress_pct = (i + 1) / 4
            progress(progress_pct, desc=status_msg)
            final_state = node_state
    except Exception as e:
        if "Connection" in type(e).__name__ or "connection" in str(e).lower():
            return (
                "<p style='color:red'>❌ LLM 서버(Ollama)에 연결할 수 없습니다.<br>"
                "셀 2/6을 실행하여 Ollama 서버를 시작한 뒤 다시 시도하세요.</p>",
                None,
                "오류: Ollama 미실행",
            )
        return f"<p style='color:red'>❌ {e}</p>", None, f"오류: {e}"

    if final_state is None:
        return "<p style='color:red'>파이프라인 실행 실패</p>", None, "오류"

    if final_state.get("error"):
        err = final_state["error"]
        return f"<p style='color:red'>❌ {err}</p>", None, f"오류: {err}"

    html = final_state.get("html_output", "")
    if not html:
        return "<p style='color:red'>HTML 생성 실패</p>", None, "오류"

    # 파일 저장
    timestamp = int(time.time())
    out_path = OUTPUT_DIR / f"deck_{timestamp}.html"
    out_path.write_text(html, encoding="utf-8")

    # iframe 미리보기 (srcdoc으로 임베딩)
    safe_html = html.replace('"', "&quot;")
    iframe_html = (
        f'<iframe srcdoc="{safe_html}" '
        f'style="width:100%;height:600px;border:none;border-radius:8px;" '
        f'allowfullscreen></iframe>'
    )

    return iframe_html, str(out_path), final_state.get("status", "완료")


# ─── Gradio UI 레이아웃 ────────────────────────────────────────────────────────
with gr.Blocks(
    title="🎨 Local Deck Gen Agent",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="teal",
        font=[gr.themes.GoogleFont("Roboto"), "sans-serif"],
    ),
    css="""
    .header { text-align: center; padding: 16px 0 8px; }
    .header h1 { color: #1565C0; font-size: 1.6em; margin-bottom: 4px; }
    .header p  { color: #555; font-size: 0.9em; }
    .generate-btn { background: #1565C0 !important; color: white !important; }
    """,
) as demo:

    # ─ 헤더
    gr.HTML("""
    <div class="header">
      <h1>🎨 Local Deck Gen Agent</h1>
      <p>한국어 프롬프트 → Reveal.js 발표 슬라이드 자동 생성</p>
      <p style="font-size:0.8em; color:#888">
        LangGraph · HyperCLOVA X · vLLM · Flutter Design
      </p>
    </div>
    """)

    # ─ 아키텍처 설명 (교육용)
    with gr.Accordion("📐 시스템 아키텍처 (클릭하여 열기)", open=False):
        gr.Markdown("""
**[웹서버]** Gradio (이 앱) → 브라우저의 HTTP 요청을 받아 응답
**[앱서버]** LangGraph 파이프라인 → 비즈니스 로직 (4-노드 에이전트)
**[API 서버]** vLLM → OpenAI 호환 REST API로 LLM 추론 제공
**[모델]** HyperCLOVA X SEED → 실제 텍스트 생성 담당

```
브라우저 → [Gradio :7860] → [LangGraph] → [vLLM :8000] → LLM
              웹서버             앱서버          API서버
```
        """)

    # ─ 입력 / 출력
    with gr.Row():
        with gr.Column(scale=1):
            prompt_box = gr.Textbox(
                label="📝 발표 내용 입력 (한국어 마크다운)",
                placeholder="발표 주제, 페이지 수, 대상 청중, 스타일 등을 자유롭게 입력하세요.",
                lines=14,
                value=SAMPLE_PROMPT,
            )
            with gr.Row():
                gen_btn = gr.Button("🚀 덱 생성", variant="primary", elem_classes="generate-btn")
                clear_btn = gr.Button("🗑️ 초기화", variant="secondary")

            status_box = gr.Textbox(label="⚙️ 처리 상태", interactive=False, lines=1)

        with gr.Column(scale=2):
            preview_html = gr.HTML(
                label="🖥️ 미리보기",
                value="<div style='height:600px;display:flex;align-items:center;justify-content:center;"
                      "background:#f5f5f5;border-radius:8px;color:#999'>생성 버튼을 눌러주세요</div>",
            )
            download_file = gr.File(label="⬇️ HTML 다운로드", interactive=False)

    # ─ 이벤트 연결
    gen_btn.click(
        fn=generate_deck,
        inputs=[prompt_box],
        outputs=[preview_html, download_file, status_box],
    )
    clear_btn.click(
        fn=lambda: ("", None, ""),
        outputs=[prompt_box, download_file, status_box],
    )

    # ─ 푸터
    gr.Markdown(
        "---\n"
        "**Local Deck Gen Agent** · Phase 1 MVP · "
        "LangGraph + HyperCLOVA X + vLLM + Reveal.js",
        elem_id="footer",
    )


if __name__ == "__main__":
    _share = os.environ.get("GRADIO_SHARE", "true").lower() not in ("false", "0", "no")
    demo.launch(
        share=_share,
        server_port=7860,
        show_error=True,
    )
