"""
Node 3: format_writer — draft_content → ===SLIDE_N=== 엄격한 포맷 변환

[역할] think_drafter가 자유 형식으로 구상한 초안을 받아
       낮은 temperature(0.1)로 포맷 규칙을 기계적으로 적용합니다.
       내용 창작은 하지 않고 오직 변환만 담당합니다.
"""
import re
from agent.state import DeckState
from agent.llm import chat
from agent.prompts import FORMAT_SYSTEM


def format_slides(state: DeckState) -> DeckState:
    if state.get("error"):
        return state

    req = state["parsed_request"]
    num = req["num_slides"]
    draft = state.get("draft_content", "")

    if not draft:
        return {**state, "error": "스토리라인 초안이 비어있습니다.", "status": "오류"}

    user_msg = (
        f"아래 초안을 **정확히 {num}장**으로 변환하세요.\n"
        f"초안 슬라이드 수와 달라도 반드시 {num}장만 출력하세요.\n\n"
        f"--- 초안 ---\n{draft}"
    )

    raw = chat(
        [
            {"role": "system", "content": FORMAT_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.1,   # 포맷 규칙 준수: 창의성 낮추고 결정론적으로
        max_tokens=1800,
    )

    # Think 모델 후처리 누출 제거 (raw 전체 + 각 슬라이드)
    raw = re.sub(r"\nassistant\b.*$", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()

    # ===SLIDE_N=== 파싱 — 중복 번호는 첫 번째만 사용
    blocks = re.findall(r"===SLIDE_(\d+)===(.*?)(?====SLIDE_\d+===|$)", raw, re.DOTALL)
    seen: set[str] = set()
    slides_md: list[str] = []
    for num_str, content in blocks:
        if num_str not in seen:
            seen.add(num_str)
            c = content
            # Think 모델 후처리 누출 제거
            c = re.sub(r"\nassistant\b.*$", "", c, flags=re.DOTALL | re.IGNORECASE)
            # FORMAT_SYSTEM 규칙 텍스트 누출 제거 (━━━ 구분자 이후)
            c = re.sub(r"\n\s*━+.*$", "", c, flags=re.DOTALL)
            # 후행 공백·빈줄 정리
            c = "\n".join(line.rstrip() for line in c.splitlines()).strip()
            if c:
                slides_md.append(c)

    # 폴백: 구분자 파싱 실패 시 --- 로 분리
    if not slides_md:
        slides_md = [s.strip() for s in raw.split("---") if s.strip()]

    if not slides_md:
        return {
            **state,
            "error": f"포맷 변환 실패 — 슬라이드를 파싱할 수 없습니다.\n원본:\n{raw[:500]}",
            "status": "오류",
        }

    # 슬라이드 1: ## 제목 다음 줄에 캐치프레이즈가 잘못 포함된 경우 제거
    if slides_md:
        lines = slides_md[0].splitlines()
        cleaned: list[str] = []
        for i, line in enumerate(lines):
            is_catchphrase_line = (
                i > 0
                and bool(re.match(r"^[A-Z][A-Z\s/]+[A-Z]$", line.strip()))
                and not line.startswith("#")
                and not line.startswith("-")
            )
            if not is_catchphrase_line:
                cleaned.append(line)
        slides_md[0] = "\n".join(cleaned).strip()

    # 요청 슬라이드 수 초과 시 잘라내기
    if len(slides_md) > num:
        slides_md = slides_md[:num]

    return {
        **state,
        "outline": {},  # html_renderer는 위치 기반 타입 추론 사용
        "slides_md": slides_md,
        "status": f"✅ 포맷 변환 완료 ({len(slides_md)}장) → HTML 렌더링 중...",
    }
