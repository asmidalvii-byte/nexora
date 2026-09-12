"""One-off utility: converts the plain-text sample JD/resumes into real PDFs
so demo mode and the end-to-end tests exercise the actual PDF-parsing path,
not a shortcut. Run with: python -m scripts.build_sample_pdfs
"""
import sys
from pathlib import Path

import pymupdf as fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import SAMPLE_DATA_DIR  # noqa: E402


def text_to_pdf(text: str, out_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, page.rect.width - 50, page.rect.height - 50)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv", align=0)
    doc.save(str(out_path))
    doc.close()


def main():
    jd_txt = SAMPLE_DATA_DIR / "sample_jd.txt"
    jd_pdf = SAMPLE_DATA_DIR / "sample_jd.pdf"
    text_to_pdf(jd_txt.read_text(encoding="utf-8"), jd_pdf)
    print(f"Wrote {jd_pdf}")

    resumes_dir = SAMPLE_DATA_DIR / "sample_resumes"
    for txt_path in sorted(resumes_dir.glob("*.txt")):
        pdf_path = txt_path.with_suffix(".pdf")
        text_to_pdf(txt_path.read_text(encoding="utf-8"), pdf_path)
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
