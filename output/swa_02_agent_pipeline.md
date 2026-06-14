# SWA-02: 에이전트 파이프라인 설계 (Agent Pipeline Design)

> LangGraph `StateGraph`를 사용한 ML 에이전트 파이프라인 설계 가이드.  
> 노드 구조, 상태 스키마, 에러 핸들링, 스트리밍 패턴을 다룹니다.

---

## 1. StateGraph 기본 구조

```python
# agent/graph.py 패턴
from langgraph.graph import StateGraph, END
from agent.state import MyState

def build_graph():
    workflow = StateGraph(MyState)

    # 노드 등록
    workflow.add_node("parser",    parse_input)
    workflow.add_node("processor", call_llm)
    workflow.add_node("renderer",  render_output)

    # 진입점 + 엣지
    workflow.set_entry_point("parser")
    workflow.add_edge("parser",    "processor")
    workflow.add_edge("processor", "renderer")
    workflow.add_edge("renderer",  END)

    return workflow.compile()

graph = build_graph()  # 모듈 레벨 싱글톤
```

---

## 2. 상태 스키마 설계 원칙

```python
# agent/state.py 패턴
from typing import TypedDict, Optional

class MyState(TypedDict):
    # === 입력 (항상 채워짐) ===
    user_prompt: str

    # === 노드별 출력 (순서대로 채워짐) ===
    parsed_request: dict    # parser 출력
    llm_raw: str            # processor 출력 (LLM 원문)
    result_items: list      # processor 출력 (파싱 후)
    html_output: str        # renderer 출력

    # === 메타 (항상 존재) ===
    status: str             # UI 진행 표시용
    error: Optional[str]    # None이면 정상, 문자열이면 오류
```

**설계 원칙:**
- 모든 필드를 `TypedDict`에 선언 (LangGraph가 타입 체크)
- 노드가 사용하지 않는 필드도 `{**state}` 스프레드로 전달
- `error` 필드 패턴: 이전 노드에서 오류 발생 시 이후 노드는 즉시 통과
- `status` 필드: UI 진행 표시에 활용 (`stream_mode="updates"`)

---

## 3. 노드 함수 패턴

### 3-1. LLM 없는 노드 (빠른 파싱/변환)

```python
# agent/nodes/input_parser.py 패턴
import re
from agent.state import MyState

def parse_input(state: MyState) -> MyState:
    # 오류 전파 패턴
    if state.get("error"):
        return state

    prompt = state["user_prompt"].strip()
    if not prompt:
        return {**state, "error": "입력이 비어 있습니다.", "status": "오류"}

    # 슬라이드 수 추출 예시
    num = 10
    m = re.search(r"(\d+)\s*(?:페이지|장|slides?)", prompt, re.IGNORECASE)
    if m:
        num = min(max(int(m.group(1)), 3), 20)

    return {
        **state,
        "parsed_request": {"original_prompt": prompt, "num": num},
        "status": "✅ 파싱 완료",
        "error": None,
    }
```

### 3-2. LLM 호출 노드 (핵심 처리)

```python
# agent/nodes/processor.py 패턴
import re
from agent.llm import chat
from agent.prompts import MY_SYSTEM_PROMPT
from agent.state import MyState

def call_llm(state: MyState) -> MyState:
    if state.get("error"):
        return state

    req = state["parsed_request"]

    user_msg = f"요청:\n{req['original_prompt']}"
    raw = chat(
        [
            {"role": "system", "content": MY_SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=2048,   # 입력 토큰 + 출력 토큰 ≤ max_model_len (4096)
    )

    # Think 모델 반복 출력 중복 제거 예시
    blocks = re.findall(r"===ITEM_(\d+)===(.*?)(?====ITEM_\d+===|$)", raw, re.DOTALL)
    seen: set[str] = set()
    items = []
    for num_str, content in blocks:
        if num_str not in seen:
            seen.add(num_str)
            c = content.strip()
            if c:
                items.append(c)

    if not items:
        return {**state, "error": f"파싱 실패:\n{raw}", "status": "오류"}

    return {
        **state,
        "llm_raw": raw,
        "result_items": items,
        "status": f"✅ 처리 완료 ({len(items)}건)",
    }
```

### 3-3. 출력 노드 (포맷/저장)

```python
# agent/nodes/renderer.py 패턴
import time
from pathlib import Path
from agent.state import MyState

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"

def render_output(state: MyState) -> MyState:
    if state.get("error"):
        return state

    items = state["result_items"]
    html = build_html(items)   # 순수 함수: 템플릿 렌더링

    # 파일 저장
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"result_{int(time.time())}.html"
    out_path.write_text(html, encoding="utf-8")

    return {
        **state,
        "html_output": html,
        "status": "✅ 완료",
    }
```

---

## 4. 조건부 분기 패턴

단순 선형 파이프라인 외에 조건 분기가 필요한 경우:

```python
def route_by_type(state: MyState) -> str:
    """분기 함수: 다음 노드 이름을 문자열로 반환"""
    if state.get("error"):
        return "error_handler"
    if state["parsed_request"]["type"] == "summary":
        return "summarizer"
    return "generator"

workflow.add_conditional_edges(
    "parser",
    route_by_type,
    {
        "summarizer":    "summarizer",
        "generator":     "generator",
        "error_handler": "error_handler",
    }
)
```

---

## 5. 스트리밍 패턴 (Gradio 진행 표시용)

```python
# graph.stream() 활용 — 노드 완료 시마다 이벤트 수신
for state_update in graph.stream(initial_state, stream_mode="updates"):
    node_name = list(state_update.keys())[0]
    node_state = state_update[node_name]
    print(f"[{node_name}] {node_state.get('status', '')}")
```

Gradio와 연동 시 `threading.Thread`로 분리 (SWA-04 참고):

```python
shared = {"done": False, "node": None, "result": None}

def _worker(prompt, shared):
    for update in graph.stream(initial_state, stream_mode="updates"):
        shared["node"] = list(update.keys())[0]
    shared["done"] = True
    shared["result"] = final_state

thread = threading.Thread(target=_worker, args=(prompt, shared))
thread.start()
```

---

## 6. 에러 전파 규칙

```python
# 표준 에러 전파 패턴 — 모든 노드가 따라야 함
def any_node(state: MyState) -> MyState:
    if state.get("error"):      # ← 이전 노드 오류 확인
        return state            # ← 오류 상태 그대로 통과

    try:
        # ... 실제 처리 ...
        return {**state, "result": result, "status": "✅ 완료"}
    except Exception as e:
        return {**state, "error": str(e), "status": "오류"}
```

마지막 노드에서 오류를 UI로 전달:
```python
if result.get("error"):
    return f"<p style='color:red'>오류: {result['error']}</p>", None, "❌ 오류"
```

---

## 7. 그래프 확장 시 체크리스트

새 노드를 추가할 때:
- [ ] `agent/state.py`에 새 필드 추가 (TypedDict)
- [ ] `agent/nodes/new_node.py` 생성 (`(state) -> state` 시그니처)
- [ ] `agent/graph.py`에 `add_node` + `add_edge`
- [ ] `ui/app.py`의 `NODE_LABELS`, `NODE_PROGRESS` 딕셔너리 업데이트
- [ ] 오류 전파 패턴 (`if state.get("error"): return state`) 포함

---

*문서 유형: SWA-02 에이전트 파이프라인 설계 | 작성일: 2026-06-14*
