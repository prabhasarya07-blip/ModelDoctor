from __future__ import annotations

import argparse
import re
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_md_to_pdf(md_path: Path, pdf_path: Path) -> None:
    md = md_path.read_text(encoding="utf-8", errors="replace").splitlines()

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        spaceAfter=8,
    )
    code = ParagraphStyle(
        name="Code",
        fontName="Courier",
        fontSize=8.8,
        leading=11,
        spaceAfter=8,
    )
    bullet = ParagraphStyle(
        name="Bullet",
        parent=body,
        leftIndent=14,
        bulletIndent=6,
        spaceAfter=2,
    )

    story = []
    in_code = False
    code_lines: list[str] = []

    for raw in md + [""]:
        line = raw.rstrip("\n")

        if line.strip().startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), style=code))
                story.append(Spacer(1, 0.12 * inch))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            story.append(Spacer(1, 0.08 * inch))
            continue

        if line.startswith("# "):
            story.append(Paragraph(_escape(line[2:].strip()), h1))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_escape(line[3:].strip()), h2))
            continue

        m = re.match(r"^-\s+(.*)$", line)
        if m:
            story.append(Paragraph(_escape(m.group(1)), bullet, bulletText="•"))
            continue

        m = re.match(r"^\d+\.\s+(.*)$", line)
        if m:
            story.append(Paragraph(_escape(m.group(1)), body))
            continue

        story.append(Paragraph(_escape(line), body))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title=md_path.stem,
    )
    doc.build(story)


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Render a Markdown file to a simple PDF.")
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(root / "docs" / "ModelDoctor_Runbook.md"),
        help="Input Markdown path (default: docs/ModelDoctor_Runbook.md)",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default=str(root / "docs" / "ModelDoctor_Runbook.pdf"),
        help="Output PDF path (default: docs/ModelDoctor_Runbook.pdf)",
    )
    args = parser.parse_args()

    md_path = Path(args.in_path)
    pdf_path = Path(args.out_path)

    render_md_to_pdf(md_path, pdf_path)
    print(f"Wrote: {pdf_path}")


if __name__ == "__main__":
    main()
