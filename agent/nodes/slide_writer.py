"""
Node 3: slide_writer — 슬라이드별 내용 작성

[역할] LLM을 호출하여 목차를 바탕으로 각 슬라이드의 마크다운 내용을 생성합니다.
       이 노드가 '작성자 에이전트' 역할입니다.
"""
import json
import re
from agent.state import DeckState
from agent.llm import chat
from agent.prompts import SLIDE_SYSTEM


def write_slides(state: DeckState) -> DeckState:
    if state.get("error"):
        return state

    outline = state["outline"]
    slides_info = json.dumps(outline.get("slides", []), ensure_ascii=False, indent=2)

    user_msg = (
        f"발표 제목: {outline.get('title', '')}\n\n"
        f"슬라이드 목차:\n{slides_info}\n\n"
        "위 목차의 모든 슬라이드 내용을 순서대로 작성해 주세요."
    )

    raw = chat(
        [
            {"role": "system", "content": SLIDE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=6144,
    )

    # ===SLIDE_N=== 구분자로 분리
    parts = re.split(r"===SLIDE_\d+===", raw)
    slides_md = [p.strip() for p in parts if p.strip()]

    if not slides_md:
        # 폴백: --- 구분자 시도
        slides_md = [s.strip() for s in raw.split("---") if s.strip()]

    if not slides_md:
        return {**state, "error": f"슬라이드 내용 파싱 실패:\n{raw}", "status": "오류"}

    return {
        **state,
        "slides_md": slides_md,
        "status": f"✅ 내용 작성 완료 ({len(slides_md)}장) → HTML 렌더링 중...",
    }
