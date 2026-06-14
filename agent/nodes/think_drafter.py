"""
Node 2: think_drafter — 형식 제약 없는 자유 스토리라인 구상

[역할] Think 모델이 "무엇을 말할 것인가"에만 집중하도록 형식 제약을 제거합니다.
       풍부한 한국어 내용을 draft_content에 저장하고,
       format_writer(Node 3)가 엄격한 포맷으로 변환합니다.

[설계 의도]
  1-call 방식: Think 모델에게 내용 + 포맷을 동시에 요구 → 포맷 준수 실패
  2-call 방식: Think가 내용에만 집중 → format_writer가 포맷 변환
"""
import re
from agent.state import DeckState
from agent.llm import chat
from agent.prompts import THINK_DRAFT_SYSTEM

# 4096 토큰 제한 고려: draft가 너무 길면 format_writer context가 넘침
# 한국어 기준 1토큰 ≈ 1.5~2자, 800토큰 ≈ 1200~1600자
_DRAFT_MAX_CHARS = 1400


def draft_content(state: DeckState) -> DeckState:
    if state.get("error"):
        return state

    req = state["parsed_request"]
    num = req["num_slides"]

    user_msg = (
        f"다음 요청으로 {num}장 발표 슬라이드 스토리라인을 구상해주세요.\n\n"
        f"요청:\n{req['original_prompt']}\n\n"
        f"총 {num}장 구성으로, 각 슬라이드별 핵심 메시지와 내용을 풍부하게 작성해주세요."
    )

    raw = chat(
        [
            {"role": "system", "content": THINK_DRAFT_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=1000,  # 초안은 간결하게 — format_writer context 여유 확보
    )

    # Think 모델 후처리 누출 제거
    raw = re.sub(r"\nassistant\b.*$", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()

    # format_writer context overflow 방지
    draft = raw[:_DRAFT_MAX_CHARS] if len(raw) > _DRAFT_MAX_CHARS else raw

    return {
        **state,
        "draft_content": draft,
        "status": "✅ 스토리라인 구상 완료 → 포맷 변환 중...",
    }
