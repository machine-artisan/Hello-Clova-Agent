"""
wiki_agent/wiki_loader.py — wiki 전체를 로드하여 덱 생성 컨텍스트로 반환

덱 생성 에이전트(agent/nodes/outline_generator.py)가 호출하여
사용자 도메인 지식을 시스템 프롬프트에 주입합니다.
"""

from pathlib import Path

WIKI_DIR = Path(__file__).parent.parent / "wiki"

WIKI_FILES = ["profile.md", "domain.md", "stack.md", "glossary.md"]


def load_wiki() -> str:
    """wiki 파일들을 하나의 문자열로 합쳐 반환. wiki가 비어 있으면 빈 문자열."""
    parts = []
    for name in WIKI_FILES:
        path = WIKI_DIR / name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").strip()
        # 템플릿 placeholder만 있는 파일은 건너뜀
        if "(populated by ingest)" in content and content.count("\n") < 10:
            continue
        if "(fill in)" in content and content.count("(fill in)") > 3:
            continue
        parts.append(f"## [{name}]\n\n{content}")

    return "\n\n---\n\n".join(parts)


def has_wiki() -> bool:
    """실질적인 wiki 내용이 있는지 확인"""
    return bool(load_wiki().strip())
