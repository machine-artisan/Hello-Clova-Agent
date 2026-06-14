"""
Node 2: outline_generator — 슬라이드 목차 생성

[역할] LLM을 호출하여 슬라이드 목차(JSON)를 생성합니다.
       이 노드가 '기획자 에이전트' 역할입니다.
"""
import json
import re
from agent.state import DeckState
from agent.llm import chat
from agent.prompts import OUTLINE_SYSTEM


def generate_outline(state: DeckState) -> DeckState:
    if state.get("error"):
        return state

    req = state["parsed_request"]
    user_msg = (
        f"다음 내용으로 {req['num_slides']}장 분량의 발표 슬라이드 목차를 작성해 주세요.\n\n"
        f"요청:\n{req['original_prompt']}\n\n"
        "JSON 형식으로만 출력하세요."
    )

    raw = chat(
        [
            {"role": "system", "content": OUTLINE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
    )

    # 첫 번째 완전한 JSON 객체만 추출 (Think 모델이 JSON을 반복 출력할 수 있음)
    start = raw.find("{")
    if start == -1:
        return {**state, "error": f"목차 JSON 파싱 실패:\n{raw}", "status": "오류"}

    try:
        outline, _ = json.JSONDecoder().raw_decode(raw, start)
    except json.JSONDecodeError as e:
        return {**state, "error": f"목차 JSON 파싱 오류: {e}\n원문:\n{raw}", "status": "오류"}

    total = len(outline.get("slides", []))
    return {
        **state,
        "outline": outline,
        "status": f"✅ 목차 생성 완료 ({total}장) → 내용 작성 중...",
    }
