"""
Node 1: input_parser — 사용자 입력 파싱

[역할] LLM 호출 없이 순수 Python으로 입력을 구조화합니다.
       슬라이드 수 힌트 추출 및 기본값 설정.
"""
import re
from agent.state import DeckState


def parse_input(state: DeckState) -> DeckState:
    prompt = state["user_prompt"].strip()
    if not prompt:
        return {**state, "error": "입력이 비어 있습니다.", "status": "오류"}

    # 슬라이드 수 힌트 추출: "10페이지", "15슬라이드", "12장" 등
    num_slides = 10  # 기본값
    match = re.search(r"(\d+)\s*(?:페이지|슬라이드|장|slides?)", prompt, re.IGNORECASE)
    if match:
        num_slides = min(max(int(match.group(1)), 3), 20)

    return {
        **state,
        "num_slides": num_slides,
        "parsed_request": {
            "original_prompt": prompt,
            "num_slides": num_slides,
        },
        "slides_md": [],
        "outline": {},
        "html_output": "",
        "error": None,
        "status": "✅ 입력 파싱 완료 → 목차 생성 중...",
    }
