# SWA-05: Gradio UI 패턴 (Gradio UI Patterns)

> LangGraph 에이전트 결과를 비개발자도 쓸 수 있는 웹 UI로 제공하는 패턴.  
> 블로킹 LLM 호출 중 실시간 진행 표시, 다중 탭, 파일 다운로드를 다룹니다.

---

## 1. 핵심 과제: LLM 호출은 블로킹이다

LangGraph 파이프라인의 LLM 호출은 90~150초 소요. 이 동안 Gradio가 멈추면 사용자는 아무 피드백도 받지 못함.

**해결 패턴: threading + generator yield**

```python
import threading, time
import gradio as gr

# ─── 공유 상태 ───────────────────────────────────────────────────────
def _run_graph_in_thread(prompt: str, shared: dict):
    from agent.graph import graph

    initial_state = {
        "user_prompt": prompt,
        "num_slides": 10,
        "parsed_request": {}, "outline": {}, "slides_md": [],
        "html_output": "", "status": "시작", "error": None,
    }

    for state_update in graph.stream(initial_state, stream_mode="updates"):
        node_name = list(state_update.keys())[0]
        shared["node"]     = node_name
        shared["status"]   = state_update[node_name].get("status", "")

    shared["done"]   = True
    shared["result"] = state_update[node_name]  # 최종 상태


# ─── Gradio generator 함수 ────────────────────────────────────────────
def generate(prompt: str):
    shared = {"done": False, "node": None, "status": "", "result": None}

    thread = threading.Thread(target=_run_graph_in_thread, args=(prompt, shared))
    thread.start()

    start = time.time()
    while not shared["done"]:
        elapsed = int(time.time() - start)
        node    = shared.get("node", "")
        status  = shared.get("status", "처리 중...")
        yield (
            f"<p>⏱️ {elapsed}초 경과 | [{node}] {status}</p>",  # 상태 HTML
            None,                                                   # 파일 (아직 없음)
            f"[{node}] {status}",                                   # 텍스트 상태
        )
        time.sleep(2)

    result = shared["result"]
    if result.get("error"):
        yield f"<p style='color:red'>❌ {result['error']}</p>", None, "오류"
    else:
        html = result["html_output"]
        # ... 파일 저장 후 반환
        yield f"<iframe srcdoc='{html}' style='width:100%;height:600px;'>", out_path, "✅ 완료"
```

---

## 2. Gradio Blocks 다중 탭 구조

```python
import gradio as gr

with gr.Blocks(title="에이전트 UI") as demo:
    gr.Markdown("# AI 에이전트")

    with gr.Tabs():

        # ─── 탭 1: 메인 기능 ─────────────────────────────────────────
        with gr.Tab("🚀 생성"):
            with gr.Row():
                with gr.Column(scale=1):
                    prompt_input = gr.Textbox(label="입력", lines=5)
                    run_btn = gr.Button("실행", variant="primary")
                    status_box = gr.Textbox(label="상태", interactive=False)
                with gr.Column(scale=2):
                    preview = gr.HTML(label="미리보기")
                    download = gr.File(label="다운로드", interactive=False)

            run_btn.click(
                fn=generate,
                inputs=[prompt_input],
                outputs=[preview, download, status_box],
            )

        # ─── 탭 2: 이력 보기 ──────────────────────────────────────────
        with gr.Tab("📂 이전 결과"):
            with gr.Row():
                with gr.Column(scale=1):
                    file_list = gr.Dropdown(
                        label="저장된 파일 (최신순)",
                        choices=list_output_files(),
                        interactive=True,
                    )
                    refresh_btn = gr.Button("🔄 새로 고침")
                    hist_download = gr.File(label="다운로드", interactive=False)
                with gr.Column(scale=2):
                    hist_preview = gr.HTML(label="미리보기")

            file_list.change(fn=load_file, inputs=[file_list], outputs=[hist_preview, hist_download])
            refresh_btn.click(fn=refresh_list, outputs=[file_list, hist_preview, hist_download])

        # ─── 탭 3: 설정 (선택) ────────────────────────────────────────
        with gr.Tab("⚙️ 설정"):
            model_info = gr.Textbox(
                label="현재 모델",
                value=os.getenv("LLM_MODEL", "(설정 안됨)"),
                interactive=False,
            )

if __name__ == "__main__":
    share = os.getenv("GRADIO_SHARE", "false").lower() == "true"
    demo.launch(server_name="0.0.0.0", share=share)
```

---

## 3. 진행 표시 패턴

### 3-1. 텍스트 상태 (단순)

```python
yield gr.update(value="[1/3] 입력 분석 중...")
```

### 3-2. gr.Progress (내장 진행바)

```python
def generate(prompt, progress=gr.Progress()):
    progress(0, desc="시작...")
    # ... 처리 ...
    progress(0.5, desc="LLM 호출 중...")
    # ... 처리 ...
    progress(1.0, desc="완료")
```

### 3-3. HTML 로딩 애니메이션 (커스텀)

```python
LOADING_HTML = """
<div style="display:flex;align-items:center;gap:12px;padding:20px;">
  <div style="
    width:40px; height:40px; border-radius:50%;
    border:4px solid #1565C0; border-top-color:transparent;
    animation: spin 1s linear infinite;
  "></div>
  <span style="font-size:1.1em;">AI가 생성 중입니다...</span>
</div>
<style>@keyframes spin { to { transform:rotate(360deg); } }</style>
"""

# 초기 상태
preview = gr.HTML(value=LOADING_HTML)
```

---

## 4. 파일 미리보기 패턴 (Reveal.js / HTML)

```python
def load_html_preview(filename: str) -> tuple[str, str | None]:
    path = OUTPUT_DIR / filename
    if not path.exists():
        return f"<p style='color:red'>파일 없음: {filename}</p>", None

    html = path.read_text(encoding="utf-8")
    safe = html.replace('"', "&quot;")   # srcdoc 속성용 이스케이프
    iframe = (
        f'<iframe srcdoc="{safe}" '
        f'style="width:100%;height:600px;border:none;border-radius:8px;" '
        f'allowfullscreen></iframe>'
    )
    return iframe, str(path)
```

> **Gradio 경고 무시**: `<script>` 태그 포함 HTML을 `gr.HTML`에 직접 넣으면 브라우저가 실행 차단.  
> 하지만 `<iframe srcdoc="...">` 내부는 독립 문서이므로 스크립트가 정상 실행됨. Reveal.js, Chart.js 등 OK.

---

## 5. Colab에서 Gradio 공유

```python
# Colab에서는 반드시 share=True (터널링 없으면 외부 접속 불가)
demo.launch(share=True)  # → https://xxxxx.gradio.live

# 로컬에서는 share=False + server_name="0.0.0.0"
demo.launch(server_name="0.0.0.0", share=False)  # → http://localhost:7860
```

환경변수로 제어:
```python
share = os.getenv("GRADIO_SHARE", "false").lower() == "true"
demo.launch(server_name="0.0.0.0", share=share)
```

---

## 6. 자주 쓰는 Gradio 컴포넌트 조합

| 목적 | 컴포넌트 |
|------|---------|
| 긴 텍스트 입력 | `gr.Textbox(lines=5)` |
| 구조화 입력 | 여러 `gr.Textbox` + `gr.Slider` + `gr.Dropdown` |
| 결과 HTML 표시 | `gr.HTML` (정적) 또는 `<iframe srcdoc>` (스크립트 포함) |
| 파일 다운로드 | `gr.File(interactive=False)`, 값으로 파일 경로 문자열 전달 |
| 진행 표시 | `gr.Textbox(interactive=False)` 또는 `gr.Progress()` |
| 파일 목록 선택 | `gr.Dropdown(choices=[...])` + `.change()` 이벤트 |
| 주 실행 버튼 | `gr.Button("실행", variant="primary")` |
| 보조 버튼 | `gr.Button("새로 고침", variant="secondary")` |

---

## 7. 환경변수 주입 (WSL2 / 비인터랙티브 셸)

WSL2에서 Claude Code CLI가 `.bashrc`를 소싱하지 않는 문제:

```json
// .claude/settings.local.json
{
  "env": {
    "HF_TOKEN": "hf_..."
  }
}
```

Gradio 실행 시 명시적 전달:
```bash
LLM_API_BASE="http://localhost:8000/v1" \
LLM_API_KEY="EMPTY" \
LLM_MODEL="your-model-id" \
GRADIO_SHARE="false" \
python3 ui/app.py
```

---

*문서 유형: SWA-05 Gradio UI 패턴 | 작성일: 2026-06-14*
