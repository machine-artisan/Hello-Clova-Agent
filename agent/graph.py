"""
LangGraph 파이프라인 조립

파이프라인 구조 (4-node, LLM 2-call):
  사용자 입력
      │
  [Node 1] input_parser   ← LLM 없음 (빠름)
      │
  [Node 2] think_drafter  ← LLM 1회: 형식 제약 없는 자유 구상 (temperature=0.7)
      │                      Think 모델이 "무엇을 말할 것인가"에만 집중
      │
  [Node 3] format_writer  ← LLM 1회: 초안 → ===SLIDE_N=== 변환 (temperature=0.1)
      │                      포맷 규칙만 기계적으로 적용, 내용 창작 없음
      │
  [Node 4] html_renderer  ← LLM 없음 (Reveal.js HTML 템플릿 렌더링)
      │
  Reveal.js HTML 출력

변경 이력:
  v1: outline_generator(Node 2) + slide_writer(Node 3) — LLM 2-call
  v2: slide_writer 통합 — LLM 1-call (속도 개선)
  v3: think_drafter + format_writer 분리 — LLM 2-call (품질 개선)
      Think 모델 특성상 내용 구상과 포맷 변환을 분리해야 포맷 준수율 향상
"""
from langgraph.graph import StateGraph, END
from agent.state import DeckState
from agent.nodes.input_parser import parse_input
from agent.nodes.think_drafter import draft_content
from agent.nodes.format_writer import format_slides
from agent.nodes.html_renderer import render_html


def build_graph():
    """LangGraph StateGraph를 조립하고 컴파일하여 반환합니다."""
    workflow = StateGraph(DeckState)

    workflow.add_node("input_parser",  parse_input)
    workflow.add_node("think_drafter", draft_content)
    workflow.add_node("format_writer", format_slides)
    workflow.add_node("html_renderer", render_html)

    workflow.set_entry_point("input_parser")
    workflow.add_edge("input_parser",  "think_drafter")
    workflow.add_edge("think_drafter", "format_writer")
    workflow.add_edge("format_writer", "html_renderer")
    workflow.add_edge("html_renderer", END)

    return workflow.compile()


# 싱글톤 그래프 인스턴스
graph = build_graph()


def run(user_prompt: str) -> DeckState:
    """CLI/테스트용 직접 실행 함수"""
    initial_state: DeckState = {
        "user_prompt": user_prompt,
        "num_slides": 10,
        "parsed_request": {},
        "draft_content": "",
        "outline": {},
        "slides_md": [],
        "html_output": "",
        "status": "시작",
        "error": None,
    }
    return graph.invoke(initial_state)
