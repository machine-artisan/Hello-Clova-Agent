"""
wiki_agent/convert.py — 원본 문서 → Markdown 변환

지원 형식:
  PDF   : PyMuPDF (fitz) 로 페이지별 텍스트 추출
  ipynb : nbformat 로 코드/마크다운 셀 추출

사용:
  python wiki_agent/convert.py sources/raw/my_doc.pdf
  python wiki_agent/convert.py sources/raw/notebook.ipynb
"""

import sys
import re
from pathlib import Path


# ── 출력 경로 결정 ────────────────────────────────────────────────────────────

def _output_path(src: Path) -> Path:
    out_dir = Path(__file__).parent.parent / "sources" / "md"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / (src.stem + ".md")


# ── PDF 변환 ──────────────────────────────────────────────────────────────────

def convert_pdf(src: Path) -> Path:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("pip install pymupdf")

    doc = fitz.open(str(src))
    lines = [f"# {src.stem}\n\n*Source: {src.name}*\n"]

    for i, page in enumerate(doc, 1):
        text = page.get_text().strip()
        if text:
            lines.append(f"\n## Page {i}\n\n{text}\n")

    out = _output_path(src)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[convert] PDF  → {out}")
    return out


# ── Jupyter Notebook 변환 ─────────────────────────────────────────────────────

def convert_ipynb(src: Path) -> Path:
    try:
        import nbformat
    except ImportError:
        raise ImportError("pip install nbformat")

    nb = nbformat.read(str(src), as_version=4)
    lines = [f"# {src.stem}\n\n*Source: {src.name}*\n"]

    for cell in nb.cells:
        src_text = "".join(cell["source"]).strip()
        if not src_text:
            continue

        if cell["cell_type"] == "markdown":
            lines.append(f"\n{src_text}\n")

        elif cell["cell_type"] == "code":
            lines.append(f"\n```python\n{src_text}\n```\n")
            # 텍스트 출력만 포함 (이미지 등 제외)
            for output in cell.get("outputs", []):
                text = output.get("text") or output.get("data", {}).get("text/plain")
                if text:
                    out_str = "".join(text).strip()
                    if out_str:
                        lines.append(f"\n**Output:**\n```\n{out_str}\n```\n")

    out = _output_path(src)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[convert] ipynb → {out}")
    return out


# ── 진입점 ────────────────────────────────────────────────────────────────────

def convert(src_path: str) -> Path:
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(src)

    suffix = src.suffix.lower()
    if suffix == ".pdf":
        return convert_pdf(src)
    elif suffix == ".ipynb":
        return convert_ipynb(src)
    else:
        raise ValueError(f"Unsupported format: {suffix}  (supported: .pdf, .ipynb)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wiki_agent/convert.py <file>")
        sys.exit(1)
    result = convert(sys.argv[1])
    print(f"Done → {result}")
