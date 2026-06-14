"""
Gradio 웹 앱 — Local Deck Gen Agent UI

탭 구성:
  Tab 1 — 프롬프트 생성기 : 폼 → 전문 프롬프트 조립 (LLM 없음, 즉시 응답)
  Tab 2 — 덱 생성        : 프롬프트 → HCX 2-call 파이프라인 → Reveal.js HTML
  Tab 3 — 생성 이력       : output/ 디렉토리의 deck_*.html 목록 + 미리보기
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import threading
import html as html_lib

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

import gradio as gr
from agent.graph import graph
from agent.state import DeckState

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── 노드별 진행 메시지 ───────────────────────────────────────────────────────
NODE_LABELS = {
    "input_parser":  ("📋", "[1/4] 입력 분석 완료"),
    "think_drafter": ("🤔", "[2/4] HCX가 스토리라인을 구상 중 (최대 2분 소요)"),
    "format_writer": ("✍️",  "[3/4] 포맷 변환 중 (최대 1분 소요)"),
    "html_renderer": ("🎨", "[4/4] HTML 렌더링 중"),
}
NODE_PROGRESS = {
    "input_parser":  0.05,
    "think_drafter": 0.10,
    "format_writer": 0.72,
    "html_renderer": 0.94,
}

LOADING_HTML = (
    "<div style='height:600px;display:flex;flex-direction:column;align-items:center;"
    "justify-content:center;background:#f5f5f5;border-radius:8px;color:#555;gap:16px'>"
    "<div style='font-size:2em'>⏳</div>"
    "<div style='font-size:1em'>HCX 모델이 슬라이드를 작성하고 있습니다...</div>"
    "<div style='font-size:0.8em;color:#888'>LLM 추론 단계는 최대 3분이 소요됩니다.</div>"
    "</div>"
)
IDLE_HTML = (
    "<div style='height:600px;display:flex;align-items:center;justify-content:center;"
    "background:#f5f5f5;border-radius:8px;color:#999'>생성 버튼을 눌러주세요</div>"
)


# ─── Tab 1: 프롬프트 조립 ─────────────────────────────────────────────────────
PURPOSE_OPTIONS = [
    "기술 소개 / 데모",
    "비즈니스 제안",
    "프로젝트 발표",
    "교육 자료",
    "팀 내부 공유",
    "투자 유치 (IR)",
]
TONE_OPTIONS = [
    "전문적이고 명확한",
    "친근하고 이해하기 쉬운",
    "간결하고 임팩트 있는",
    "설득력 있는",
]


def build_prompt(title: str, num_pages: int, purpose: str,
                 audience: str, tone: str, topics: str, style: str) -> str:
    """폼 필드를 바탕으로 덱 생성에 최적화된 프롬프트를 조립합니다."""
    title = title.strip() or "발표"
    lines = [
        f'"{title}"을(를) 주제로 **{int(num_pages)}장** 분량의 프레젠테이션 슬라이드를 생성해 주세요.',
    ]
    if purpose:
        lines.append(f"발표 목적: {purpose}")
    if audience.strip():
        lines.append(f"대상 청중: {audience.strip()}")
    if tone:
        lines.append(f"톤 & 스타일: {tone}" + (f", {style.strip()}" if style.strip() else ""))
    elif style.strip():
        lines.append(f"스타일: {style.strip()}")

    if topics.strip():
        lines.append(f"\n포함할 주제 (순서대로):\n{topics.strip()}")

    return "\n".join(lines)


# ─── Tab 2: 덱 생성 파이프라인 ────────────────────────────────────────────────
def _run_graph_in_thread(prompt: str, shared: dict):
    initial_state: DeckState = {
        "user_prompt": prompt,
        "num_slides": 10,
        "parsed_request": {},
        "draft_content": "",
        "outline": {},
        "slides_md": [],
        "html_output": "",
        "status": "시작",
        "error": None,
    }
    try:
        final = None
        for state_update in graph.stream(initial_state, stream_mode="updates"):
            node_name = list(state_update.keys())[0]
            node_state = list(state_update.values())[0]
            icon, label = NODE_LABELS.get(node_name, ("⚙️", node_name))
            shared["node"] = node_name
            shared["node_label"] = f"{icon} {label}"
            shared["node_progress"] = NODE_PROGRESS.get(node_name, 0.5)
            final = node_state
        shared["result"] = final
    except Exception as e:
        shared["result"] = {"error": str(e)}
    finally:
        shared["done"] = True


def generate_deck(prompt: str, progress=gr.Progress()):
    if not prompt.strip():
        yield IDLE_HTML, None, "⚠️ 프롬프트를 입력해 주세요."
        return

    llm_model = os.getenv("LLM_MODEL")
    llm_base = os.getenv("LLM_API_BASE")
    if not llm_model or not llm_base:
        missing = ", ".join(
            k for k, v in {"LLM_MODEL": llm_model, "LLM_API_BASE": llm_base}.items() if not v
        )
        yield IDLE_HTML, None, f"❌ 환경변수 미설정: {missing}"
        return

    shared = {"done": False, "node": "", "node_label": "⏳ 시작 중...",
              "node_progress": 0.0, "result": None}
    thread = threading.Thread(target=_run_graph_in_thread, args=(prompt, shared), daemon=True)
    thread.start()

    elapsed = 0
    prev_node = ""
    node_elapsed = 0

    while not shared["done"]:
        time.sleep(2)
        elapsed += 2
        cur_node = shared["node"]
        if cur_node != prev_node:
            node_elapsed = 0
            prev_node = cur_node
        else:
            node_elapsed += 2

        pct = shared["node_progress"]
        if cur_node in ("think_drafter", "format_writer"):
            pct = min(pct + node_elapsed / 200, pct + 0.40)

        label = shared["node_label"]
        status = f"{label} | ⏱️ 총 {elapsed}초 경과 (현재 단계 {node_elapsed}초)"
        progress(min(pct, 0.95), desc=label)
        yield LOADING_HTML, None, status

    thread.join()
    final_state = shared["result"]

    if final_state is None:
        yield IDLE_HTML, None, "❌ 파이프라인 실행 실패"
        return
    if final_state.get("error"):
        err = final_state["error"]
        yield f"<p style='color:red'>❌ {err}</p>", None, f"❌ 오류: {err[:120]}"
        return

    html = final_state.get("html_output", "")
    if not html:
        yield IDLE_HTML, None, "❌ HTML 생성 실패"
        return

    timestamp = int(time.time())
    out_path = OUTPUT_DIR / f"deck_{timestamp}.html"
    out_path.write_text(html, encoding="utf-8")

    safe_html = html_lib.escape(html, quote=True)
    iframe_html = (
        f'<iframe srcdoc="{safe_html}" '
        f'style="width:100%;height:600px;border:none;border-radius:8px;" '
        f'allowfullscreen></iframe>'
    )
    progress(1.0, desc="✅ 완료!")
    yield iframe_html, str(out_path), f"✅ 완료 — 총 {elapsed}초 소요"


# ─── Tab 3: 생성 이력 ─────────────────────────────────────────────────────────
def list_deck_files() -> list[str]:
    return [f.name for f in sorted(OUTPUT_DIR.glob("deck_*.html"), reverse=True)]


def _load_deck(filename: str):
    if not filename:
        return IDLE_HTML, None
    path = OUTPUT_DIR / filename
    if not path.exists():
        return f"<p style='color:red'>파일 없음: {filename}</p>", None
    html = path.read_text(encoding="utf-8")
    safe_html = html_lib.escape(html, quote=True)
    iframe = (
        f'<iframe srcdoc="{safe_html}" '
        f'style="width:100%;height:600px;border:none;border-radius:8px;" '
        f'allowfullscreen></iframe>'
    )
    return iframe, str(path)


def refresh_deck_list():
    files = list_deck_files()
    if not files:
        return gr.update(choices=[], value=None), IDLE_HTML, None
    return gr.update(choices=files, value=files[0]), *_load_deck(files[0])


# ─── Gradio UI ────────────────────────────────────────────────────────────────
with gr.Blocks(title="🗒️ Memo Deck Gen Agent") as demo:

    gr.HTML("""
    <div style="text-align:center; padding:16px 0 8px">
      <h1 style="color:#1565C0; font-size:1.6em; margin-bottom:4px">🗒️ Memo Deck Gen Agent</h1>
      <p style="color:#555; font-size:0.9em">한국어 메모 → Reveal.js 슬라이드 자동 생성</p>
      <p style="font-size:0.8em; color:#888">LangGraph · HyperCLOVA X · vLLM · Flutter Design</p>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: 프롬프트 생성기 ─────────────────────────────────────────────
        with gr.Tab("📋 프롬프트 생성기"):
            gr.Markdown(
                "각 항목을 채우고 **프롬프트 생성** 버튼을 누르세요. "
                "완성된 프롬프트를 복사한 뒤 **덱 생성** 탭에 붙여넣으면 슬라이드가 만들어집니다."
            )
            with gr.Row():
                with gr.Column(scale=1):
                    p_title = gr.Textbox(
                        label="발표 제목",
                        placeholder="예: LangGraph 기반 AI 파이프라인 구축 전략",
                    )
                    p_pages = gr.Slider(
                        minimum=3, maximum=20, step=1, value=8,
                        label="슬라이드 수",
                    )
                    p_purpose = gr.Dropdown(
                        choices=PURPOSE_OPTIONS,
                        value=PURPOSE_OPTIONS[0],
                        label="발표 목적",
                    )
                    p_audience = gr.Textbox(
                        label="대상 청중",
                        placeholder="예: 개발팀 리드, 기술 배경 있음",
                    )
                    p_tone = gr.Dropdown(
                        choices=TONE_OPTIONS,
                        value=TONE_OPTIONS[0],
                        label="톤",
                    )
                    p_topics = gr.Textbox(
                        label="포함할 주제 목록",
                        placeholder=(
                            "예:\n"
                            "1. LangGraph 개요\n"
                            "2. 파이프라인 아키텍처\n"
                            "3. 구현 단계\n"
                            "4. 성능 최적화\n"
                            "5. 다음 단계"
                        ),
                        lines=7,
                    )
                    p_style = gr.Textbox(
                        label="추가 스타일 가이드 (선택)",
                        placeholder="예: 파란 계열, 다이어그램 포함 권장",
                    )
                    with gr.Row():
                        p_build_btn = gr.Button("⚡ 프롬프트 생성", variant="primary")
                        p_clear_btn = gr.Button("🗑️ 초기화", variant="secondary")

                with gr.Column(scale=1):
                    p_output = gr.Code(
                        label="📋 생성된 프롬프트 — 우측 상단 복사 버튼으로 복사하세요",
                        language=None,
                        interactive=False,
                        value="← 왼쪽 폼을 채우고 '프롬프트 생성' 버튼을 누르세요.",
                    )
                    gr.Markdown(
                        "> **사용 방법**  \n"
                        "> 1. 위 텍스트박스 우측 📋 아이콘으로 복사  \n"
                        "> 2. **덱 생성** 탭으로 이동  \n"
                        "> 3. 붙여넣기 후 🚀 슬라이드 생성"
                    )

            p_build_btn.click(
                fn=build_prompt,
                inputs=[p_title, p_pages, p_purpose, p_audience, p_tone, p_topics, p_style],
                outputs=[p_output],
            )
            p_clear_btn.click(
                fn=lambda: ("", 8, PURPOSE_OPTIONS[0], "", TONE_OPTIONS[0], "", "", ""),
                outputs=[p_title, p_pages, p_purpose, p_audience, p_tone, p_topics, p_style, p_output],
            )

        # ── Tab 2: 덱 생성 ────────────────────────────────────────────────────
        with gr.Tab("🚀 덱 생성"):
            gr.Markdown(
                "프롬프트를 붙여넣고 **슬라이드 생성** 버튼을 누르세요. "
                "자유 형식으로 직접 작성해도 됩니다. "
                "**`N장`** 또는 **`N페이지`** 키워드로 슬라이드 수를 지정하세요."
            )
            with gr.Row():
                with gr.Column(scale=1):
                    g_prompt = gr.Textbox(
                        label="📝 프롬프트 입력",
                        placeholder=(
                            "예: \"AI 파이프라인 구축 전략\"을(를) 주제로 8장 분량의 슬라이드를 생성해 주세요.\n"
                            "발표 목적: 기술 소개 / 데모\n"
                            "대상 청중: 개발팀 리드, 기술 배경 있음\n\n"
                            "포함할 주제:\n"
                            "1. LangGraph 개요\n"
                            "2. 파이프라인 아키텍처\n"
                            "..."
                        ),
                        lines=16,
                    )
                    with gr.Row():
                        g_gen_btn = gr.Button("🚀 슬라이드 생성", variant="primary")
                        g_clear_btn = gr.Button("🗑️ 초기화", variant="secondary")
                    g_status = gr.Textbox(
                        label="⚙️ 처리 상태",
                        interactive=False,
                        lines=2,
                        placeholder="생성 버튼을 누르면 진행 상태가 표시됩니다.",
                    )

                with gr.Column(scale=2):
                    g_preview = gr.HTML(label="🖥️ 미리보기", value=IDLE_HTML)
                    g_download = gr.File(label="⬇️ HTML 다운로드", interactive=False)

            g_gen_btn.click(
                fn=generate_deck,
                inputs=[g_prompt],
                outputs=[g_preview, g_download, g_status],
            )
            g_clear_btn.click(
                fn=lambda: ("", None, ""),
                outputs=[g_prompt, g_download, g_status],
            )

        # ── Tab 3: 생성 이력 ──────────────────────────────────────────────────
        with gr.Tab("📂 생성 이력"):
            gr.Markdown("저장된 덱 파일을 선택하면 미리보기가 표시됩니다.")
            with gr.Row():
                with gr.Column(scale=1):
                    h_list = gr.Dropdown(
                        label="저장된 덱 목록 (최신순)",
                        choices=list_deck_files(),
                        value=list_deck_files()[0] if list_deck_files() else None,
                        interactive=True,
                    )
                    h_refresh_btn = gr.Button("🔄 목록 새로 고침", variant="secondary")
                    h_download = gr.File(label="⬇️ HTML 다운로드", interactive=False)
                with gr.Column(scale=2):
                    h_preview = gr.HTML(label="🖥️ 미리보기", value=IDLE_HTML)

            _init_files = list_deck_files()
            if _init_files:
                _init_iframe, _init_path = _load_deck(_init_files[0])
                h_preview.value = _init_iframe
                h_download.value = _init_path

            h_list.change(fn=_load_deck, inputs=[h_list], outputs=[h_preview, h_download])
            h_refresh_btn.click(fn=refresh_deck_list, outputs=[h_list, h_preview, h_download])

    gr.Markdown(
        "---\n"
        "**Memo Deck Gen Agent** · Phase 1 MVP · "
        "LangGraph + HyperCLOVA X + vLLM + Reveal.js",
    )


if __name__ == "__main__":
    _share = os.environ.get("GRADIO_SHARE", "true").lower() not in ("false", "0", "no")
    demo.launch(
        share=_share,
        server_port=7860,
        show_error=True,
    )
