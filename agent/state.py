"""
LangGraph 상태 정의 (DeckState)

[개념] 상태(State)란?
LangGraph에서 에이전트 파이프라인을 흐르는 데이터 구조입니다.
각 노드는 이 상태를 받아 처리하고, 업데이트된 상태를 다음 노드로 전달합니다.
"""
from typing import TypedDict, Optional


class DeckState(TypedDict):
    # === 입력 ===
    user_prompt: str        # 사용자 한국어 원문 입력

    # === Node 1 출력 (input_parser) ===
    num_slides: int         # 생성할 슬라이드 수 (기본 10, 최대 20)
    parsed_request: dict    # 파싱된 요청 정보

    # === Node 2 출력 (outline_generator) ===
    outline: dict           # 슬라이드 목차 JSON

    # === Node 3 출력 (slide_writer) ===
    slides_md: list         # 슬라이드별 마크다운 내용 리스트

    # === Node 4 출력 (html_renderer) ===
    html_output: str        # 최종 Reveal.js HTML

    # === 메타 ===
    status: str             # 현재 처리 단계 (UI 진행 표시용)
    error: Optional[str]    # 오류 메시지
