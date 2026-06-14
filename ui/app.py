"""
Gradio 웹 앱 — Local Deck Gen Agent UI
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import time
import threading
import html as html_lib
import gradio as gr
from agent.graph import graph
from agent.state import DeckState

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── 노드별 사용자 메시지 ──────────────────────────────────────────────────────
NODE_LABELS = {
    "input_parser":  ("📋", "[1/3] 입력 분석 완료"),
    "slide_writer":  ("✍️", "[2/3] HCX가 슬라이드를 작성 중입니다 (최대 3분 소요)"),
    "html_renderer": ("🎨", "[3/3] HTML 렌더링 중"),
}
NODE_PROGRESS = {
    "input_parser":  0.05,
    "slide_writer":  0.10,
    "html_renderer": 0.92,
}

LOADING_HTML = (
    "<div style='height:600px;display:flex;flex-direction:column;align-items:center;"
    "justify-content:center;background:#f5f5f5;border-radius:8px;color:#555;gap:16px'>"
    "<div style='font-size:2em'>⏳</div>"
    "<div style='font-size:1em'>HCX 모델이 메모를 작성하고 있습니다...</div>"
    "<div style='font-size:0.8em;color:#888'>LLM 추론 단계는 최대 3분이 소요됩니다.</div>"
    "</div>"
)
IDLE_HTML = (
    "<div style='height:600px;display:flex;align-items:center;justify-content:center;"
    "background:#f5f5f5;border-radius:8px;color:#999'>생성 버튼을 눌러주세요</div>"
)

# ─── 샘플 데이터 ──────────────────────────────────────────────────────────────
SAMPLE_TOPICS = """\
1. 프로젝트 개요 (Gamma, SkyAI 같은 발표 자동 생성 서비스를 로컬에서 구현)
2. 기술 스택 소개 (LangGraph, HyperCLOVA X, vLLM, Gradio, Reveal.js)
3. 시스템 아키텍처 (웹서버 → 앱서버 → API 서버 → LLM 계층 설명)
4. LangGraph 4-노드 에이전트 파이프라인 상세 설명
5. Phase 1 구현 결과 및 데모
6. Phase 2 계획 (RAG 연동, 동적 테마 자동 생성)
7. 기대 효과 및 결론"""

SAMPLE_AUDIENCE = "기업 담당자 (기술 배경 비전문가)"
SAMPLE_STYLE = "Flutter 디자인 시스템, 파란 계열, 깔끔하고 전문적인 느낌"
SAMPLE_TITLE = "Local Deck Gen Agent"

FREEFORM_SAMPLE = """\
이 메모는 "Local Deck Gen Agent" 프로젝트를 소개하는 내용으로,
아래 주제를 포함한 12페이지 분량의 슬라이드를 생성해 주세요:

1. 프로젝트 개요 (Gamma, SkyAI 같은 발표 자동 생성 서비스를 로컬에서 구현)
2. 기술 스택 소개 (LangGraph, HyperCLOVA X, vLLM, Gradio, Reveal.js)
3. 시스템 아키텍처 (웹서버 → 앱서버 → API 서버 → LLM 계층 설명)
4. LangGraph 4-노드 에이전트 파이프라인 상세 설명
5. Phase 1 구현 결과 및 데모
6. Phase 2 계획 (RAG 연동, 동적 테마 자동 생성)
7. 기대 효과 및 결론

대상 독자: 기업 담당자 (기술 배경 비전문가)
스타일: Flutter 디자인 시스템, 파란 계열, 깔끔하고 전문적인 느낌"""


def build_structured_prompt(title, num_pages, topics, audience, style):
    parts = [
        f'이 메모는 "{title.strip() or "메모"}"를 주제로 하며, '
        f'{int(num_pages)}페이지 분량의 슬라이드를 생성해 주세요.'
    ]
    if topics.strip():
        parts.append(f"\n다음 주제를 순서대로 포함해 주세요:\n{topics.strip()}")
    if audience.strip():
        parts.append(f"\n대상 독자: {audience.strip()}")
    if style.strip():
        parts.append(f"스타일: {style.strip()}")
    return "\n".join(parts)


def _run_graph_in_thread(prompt: str, shared: dict):
    """LangGraph를 별도 스레드에서 실행하고 결과를 shared dict에 저장"""
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
    """generator 방식: LLM 추론 중에도 2초마다 경과 시간을 갱신"""
    if not prompt.strip():
        yield IDLE_HTML, None, "⚠️ 내용을 입력해 주세요."
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
        # LLM 노드는 내부 경과에 따라 부드럽게 진행바 이동
        if cur_node in ("outline_generator", "slide_writer"):
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


def generate_from_structured(title, num_pages, topics, audience, style, progress=gr.Progress()):
    prompt = build_structured_prompt(title, num_pages, topics, audience, style)
    yield from generate_deck(prompt, progress)


# ─── 이전 덱 목록 ─────────────────────────────────────────────────────────────
def list_deck_files() -> list[str]:
    files = sorted(OUTPUT_DIR.glob("deck_*.html"), reverse=True)
    return [f.name for f in files]


def refresh_deck_list():
    files = list_deck_files()
    if not files:
        return gr.update(choices=[], value=None), IDLE_HTML, None
    return gr.update(choices=files, value=files[0]), *_load_deck(files[0])


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


def load_deck(filename: str):
    return _load_deck(filename)


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

        # ── 탭 1: 메모 내용 구성 ───────────────────────────────────────────────
        with gr.Tab("📋 메모 내용 구성 (권장)"):
            gr.Markdown(
                "각 항목을 채우면 HCX 모델이 일관된 슬라이드를 생성합니다. "
                "**주제 목록**을 구체적으로 적을수록 결과 품질이 높아집니다."
            )
            with gr.Row():
                with gr.Column(scale=1):
                    s_title = gr.Textbox(
                        label="메모집 제목",
                        placeholder="예: Local Deck Gen Agent 프로젝트 소개",
                        value=SAMPLE_TITLE,
                    )
                    s_pages = gr.Slider(
                        minimum=3, maximum=20, step=1, value=12,
                        label="페이지 수",
                    )
                    s_topics = gr.Textbox(
                        label="포함할 주제 목록",
                        placeholder=(
                            "예:\n"
                            "1. 프로젝트 개요\n"
                            "2. 기술 스택\n"
                            "3. 시스템 아키텍처\n"
                            "..."
                        ),
                        lines=8,
                        value=SAMPLE_TOPICS,
                    )
                    s_audience = gr.Textbox(
                        label="대상 독자",
                        placeholder="예: 기업 담당자 (기술 배경 비전문가)",
                        value=SAMPLE_AUDIENCE,
                    )
                    s_style = gr.Textbox(
                        label="스타일 / 톤",
                        placeholder="예: 파란 계열, 깔끔하고 전문적인 느낌",
                        value=SAMPLE_STYLE,
                    )
                    with gr.Row():
                        s_gen_btn = gr.Button("🚀 슬라이드 생성", variant="primary")
                        s_clear_btn = gr.Button("🗑️ 초기화", variant="secondary")
                    s_status = gr.Textbox(
                        label="⚙️ 처리 상태",
                        interactive=False,
                        lines=2,
                        placeholder="생성 버튼을 누르면 진행 상태가 표시됩니다.",
                    )

                with gr.Column(scale=2):
                    s_preview = gr.HTML(label="🖥️ 미리보기", value=IDLE_HTML)
                    s_download = gr.File(label="⬇️ HTML 다운로드", interactive=False)

            s_gen_btn.click(
                fn=generate_from_structured,
                inputs=[s_title, s_pages, s_topics, s_audience, s_style],
                outputs=[s_preview, s_download, s_status],
            )
            s_clear_btn.click(
                fn=lambda: ("", 12, "", "", "", None, ""),
                outputs=[s_title, s_pages, s_topics, s_audience, s_style, s_download, s_status],
            )

        # ── 탭 2: 직접 입력 ───────────────────────────────────────────────────
        with gr.Tab("✏️ 직접 입력 (고급)"):
            gr.Markdown(
                "자유 형식으로 프롬프트를 작성합니다. "
                "**`N페이지`** 또는 **`N장`** 키워드로 슬라이드 수를 지정하세요."
            )
            with gr.Row():
                with gr.Column(scale=1):
                    f_prompt = gr.Textbox(
                        label="📝 메모 내용 입력 (한국어)",
                        placeholder=(
                            "예시:\n"
                            "\"프로젝트명\" 소개, 10페이지 분량.\n\n"
                            "포함할 내용:\n"
                            "1. 배경 및 목적\n"
                            "2. 핵심 기술\n"
                            "3. 결론\n\n"
                            "대상: 임원진 / 스타일: 전문적이고 간결하게"
                        ),
                        lines=14,
                        value=FREEFORM_SAMPLE,
                    )
                    with gr.Row():
                        f_gen_btn = gr.Button("🚀 슬라이드 생성", variant="primary")
                        f_clear_btn = gr.Button("🗑️ 초기화", variant="secondary")
                    f_status = gr.Textbox(
                        label="⚙️ 처리 상태",
                        interactive=False,
                        lines=2,
                        placeholder="생성 버튼을 누르면 진행 상태가 표시됩니다.",
                    )

                with gr.Column(scale=2):
                    f_preview = gr.HTML(label="🖥️ 미리보기", value=IDLE_HTML)
                    f_download = gr.File(label="⬇️ HTML 다운로드", interactive=False)

            f_gen_btn.click(
                fn=generate_deck,
                inputs=[f_prompt],
                outputs=[f_preview, f_download, f_status],
            )
            f_clear_btn.click(
                fn=lambda: ("", None, ""),
                outputs=[f_prompt, f_download, f_status],
            )

        # ── 탭 3: 이전 덱 목록 ────────────────────────────────────────────────
        with gr.Tab("📂 이전 메모 덱"):
            gr.Markdown("저장된 덱 파일을 선택하면 바로 미리보기가 표시됩니다.")
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

            # 초기 로드: 첫 번째 파일 표시
            _init_files = list_deck_files()
            if _init_files:
                _init_iframe, _init_path = _load_deck(_init_files[0])
                h_preview.value = _init_iframe
                h_download.value = _init_path

            h_list.change(fn=load_deck, inputs=[h_list], outputs=[h_preview, h_download])
            h_refresh_btn.click(
                fn=refresh_deck_list,
                outputs=[h_list, h_preview, h_download],
            )

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
