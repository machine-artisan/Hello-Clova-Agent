"""
Node 2 (통합): slide_writer — 슬라이드 기획 + 내용 작성 (1-call)

[역할] LLM 1번 호출로 목차 기획과 슬라이드 내용 작성을 동시에 수행합니다.
       기존 outline_generator(Node 2)를 흡수하여 LLM 호출을 2→1로 줄입니다.
"""
import re
from agent.state import DeckState
from agent.llm import chat
from agent.prompts import DIRECT_SLIDE_SYSTEM


def write_slides(state: DeckState) -> DeckState:
    if state.get("error"):
        return state

    req = state["parsed_request"]
    num = req["num_slides"]

    user_msg = (
        f"아래 요청을 바탕으로 {num}장 분량의 슬라이드를 작성해 주세요.\n\n"
        f"요청:\n{req['original_prompt']}"
    )

    raw = chat(
        [
            {"role": "system", "content": DIRECT_SLIDE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=2048,
    )

    # ===SLIDE_N=== 구분자로 분리 — Think 모델 반복 출력 대응: 번호 첫 등장만 사용
    blocks = re.findall(r"===SLIDE_(\d+)===(.*?)(?====SLIDE_\d+===|$)", raw, re.DOTALL)
    seen: set[str] = set()
    slides_md = []
    for num_str, content in blocks:
        if num_str not in seen:
            seen.add(num_str)
            c = content.strip()
            if c:
                slides_md.append(c)

    if not slides_md:
        slides_md = [s.strip() for s in raw.split("---") if s.strip()]

    if not slides_md:
        return {**state, "error": f"슬라이드 내용 파싱 실패:\n{raw}", "status": "오류"}

    # html_renderer가 색상 타입을 위치 기반으로 처리하도록 outline은 비워둠
    return {
        **state,
        "outline": {},
        "slides_md": slides_md,
        "status": f"✅ 내용 작성 완료 ({len(slides_md)}장) → HTML 렌더링 중...",
    }
