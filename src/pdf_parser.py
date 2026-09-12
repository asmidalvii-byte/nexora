"""PDF text extraction. Never lets one malformed file crash the batch."""
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pymupdf as fitz  # PyMuPDF


@dataclass
class ParsedPDF:
    source_name: str
    text: str
    num_pages: int
    ok: bool
    error: str = ""


def extract_text_from_pdf(source: Union[str, Path, bytes], source_name: str = "") -> ParsedPDF:
    """Extract text from a PDF given a path or raw bytes.

    Always returns a ParsedPDF — failures are captured in .ok/.error rather
    than raised, so a batch of resumes can't be taken down by one bad file.
    """
    name = source_name or (str(source) if isinstance(source, (str, Path)) else "uploaded.pdf")
    try:
        if isinstance(source, (str, Path)):
            doc = fitz.open(str(source))
        else:
            doc = fitz.open(stream=source, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - genuinely want to catch anything fitz raises
        return ParsedPDF(source_name=name, text="", num_pages=0, ok=False,
                          error=f"Could not open PDF: {exc}")

    try:
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text("text"))
        num_pages = doc.page_count
    except Exception as exc:  # noqa: BLE001
        return ParsedPDF(source_name=name, text="", num_pages=0, ok=False,
                          error=f"Could not read pages: {exc}")
    finally:
        doc.close()

    full_text = "\n".join(pages_text)

    if not full_text.strip():
        return ParsedPDF(source_name=name, text="", num_pages=num_pages, ok=False,
                          error="No extractable text found (scanned/image-only PDF?)")

    return ParsedPDF(source_name=name, text=full_text, num_pages=num_pages, ok=True)
