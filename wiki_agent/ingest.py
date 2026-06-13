"""
wiki_agent/ingest.py — Markdown → wiki/*.md 병합

sources/md/ 에 있는 MD 파일을 읽어 LLM으로 분석한 뒤
wiki/domain.md, wiki/stack.md, wiki/glossary.md 를 업데이트합니다.

사용:
  python wiki_agent/ingest.py sources/md/my_doc.md
  python wiki_agent/ingest.py          # sources/md/ 전체 처리
"""

import sys
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
WIKI_DIR = ROOT / "wiki"
MD_DIR = ROOT / "sources" / "md"
PROCESSED_DIR = ROOT / "sources" / "processed"

INGEST_SYSTEM = """\
You are a domain knowledge extraction agent.
Given a source document (Markdown), extract and structure knowledge into three sections.
Return valid JSON with keys: "domain", "stack", "glossary".

Rules:
- "domain": list of {heading, content} objects for core concepts, processes, insights
- "stack": list of {name, description} objects for tools, frameworks, infrastructure
- "glossary": list of {term, definition} objects
- Be concise. Distill, do not copy verbatim.
- English only.
- If nothing relevant found for a section, return an empty list.
"""


def _load_wiki(name: str) -> str:
    path = WIKI_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _append_wiki(name: str, new_content: str) -> None:
    path = WIKI_DIR / name
    current = path.read_text(encoding="utf-8")
    path.write_text(current.rstrip() + "\n\n" + new_content + "\n", encoding="utf-8")


def _llm_extract(md_text: str) -> dict:
    """LLM으로 MD 문서에서 wiki 항목 추출"""
    import json
    from agent.llm import chat

    response = chat(
        messages=[
            {"role": "system", "content": INGEST_SYSTEM},
            {"role": "user", "content": f"Extract knowledge from this document:\n\n{md_text[:8000]}"},
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    # JSON 파싱
    import re
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"domain": [], "stack": [], "glossary": []}


def ingest_file(md_path: Path) -> None:
    print(f"\n[ingest] Processing: {md_path.name}")
    md_text = md_path.read_text(encoding="utf-8")

    extracted = _llm_extract(md_text)

    # domain.md 업데이트
    if extracted.get("domain"):
        domain_lines = [f"<!-- ingested from {md_path.name} -->"]
        for item in extracted["domain"]:
            domain_lines.append(f"\n### {item['heading']}\n\n{item['content']}")
        _append_wiki("domain.md", "\n".join(domain_lines))
        print(f"  → domain.md  +{len(extracted['domain'])} sections")

    # stack.md 업데이트
    if extracted.get("stack"):
        stack_lines = [f"<!-- ingested from {md_path.name} -->"]
        for item in extracted["stack"]:
            stack_lines.append(f"\n- **{item['name']}**: {item['description']}")
        _append_wiki("stack.md", "\n".join(stack_lines))
        print(f"  → stack.md   +{len(extracted['stack'])} tools")

    # glossary.md 업데이트
    if extracted.get("glossary"):
        gloss_lines = [f"<!-- ingested from {md_path.name} -->"]
        for item in extracted["glossary"]:
            gloss_lines.append(f"\n- **{item['term']}**: {item['definition']}")
        _append_wiki("glossary.md", "\n".join(gloss_lines))
        print(f"  → glossary.md +{len(extracted['glossary'])} terms")

    # 처리 완료 → processed/ 로 이동
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / md_path.name
    shutil.move(str(md_path), str(dest))
    print(f"  → archived to sources/processed/{md_path.name}")


def ingest_all() -> None:
    md_files = [f for f in MD_DIR.glob("*.md") if f.name != ".gitkeep"]
    if not md_files:
        print("[ingest] sources/md/ 에 처리할 파일이 없습니다.")
        return
    for f in sorted(md_files):
        ingest_file(f)
    print(f"\n[ingest] 완료 — {len(md_files)}개 파일 처리")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        ingest_file(Path(sys.argv[1]))
    else:
        ingest_all()
