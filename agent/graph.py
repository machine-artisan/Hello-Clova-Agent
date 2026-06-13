"""
LangGraph 파이프라인 조립

[개념] 애플리케이션 서버(App Server)란?
이 파일이 바로 애플리케이션 서버의 핵심입니다.
각 노드(에이전트)를 연결하여 요청을 처리하는 비즈니스 로직을 정의합니다.

파이프라인 구조:
  사용자 입력
      │
  [Node 1] input_parser      ← LLM 없음 (빠름)
      │
  [Node 2] outline_generator ← LLM 호출 (목차 생성)
      │
  [Node 3] slide_writer      ← LLM 호출 (내용 작성)
      │
  [Node 4] html_renderer     ← LLM 없음 (템플릿 렌더링)
      │
  Reveal.js HTML 출력
"""
from langgraph.graph import StateGraph, END
from agent.state import DeckState
from agent.nodes.input_parser import parse_input
from agent.nodes.outline_generator import generate_outline
from agent.nodes.slide_writer import write_slides
from agent.nodes.html_renderer import render_html


def build_graph():
    """LangGraph StateGraph를 조립하고 컴파일하여 반환합니다."""
    workflow = StateGraph(DeckState)

    # 노드 등록
    workflow.add_node("input_parser", parse_input)
    workflow.add_node("outline_generator", generate_outline)
    workflow.add_node("slide_writer", write_slides)
    workflow.add_node("html_renderer", render_html)

    # 엣지 연결 (선형 파이프라인)
    workflow.set_entry_point("input_parser")
    workflow.add_edge("input_parser", "outline_generator")
    workflow.add_edge("outline_generator", "slide_writer")
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
