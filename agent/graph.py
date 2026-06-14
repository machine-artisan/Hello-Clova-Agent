"""
LangGraph 파이프라인 조립

파이프라인 구조 (3-node, LLM 1-call):
  사용자 입력
      │
  [Node 1] input_parser  ← LLM 없음 (빠름)
      │
  [Node 2] slide_writer  ← LLM 1회 호출 (기획+내용 통합)
      │
  [Node 3] html_renderer ← LLM 없음 (템플릿 렌더링)
      │
  Reveal.js HTML 출력

변경 이력:
  - outline_generator(Node 2) 제거 → slide_writer가 1-call로 흡수
  - LLM 호출 2회 → 1회로 감소 (~50% 속도 향상)
"""
from langgraph.graph import StateGraph, END
from agent.state import DeckState
from agent.nodes.input_parser import parse_input
from agent.nodes.slide_writer import write_slides
from agent.nodes.html_renderer import render_html


def build_graph():
    """LangGraph StateGraph를 조립하고 컴파일하여 반환합니다."""
    workflow = StateGraph(DeckState)

    workflow.add_node("input_parser", parse_input)
    workflow.add_node("slide_writer", write_slides)
    workflow.add_node("html_renderer", render_html)

    workflow.set_entry_point("input_parser")
    workflow.add_edge("input_parser", "slide_writer")
    workflow.add_edge("slide_writer", "html_renderer")
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
        "outline": {},
        "slides_md": [],
        "html_output": "",
        "status": "시작",
        "error": None,
    }
    return graph.invoke(initial_state)
