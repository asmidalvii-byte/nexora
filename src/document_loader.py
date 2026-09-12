"""Dispatches a resume/JD/supporting-document upload to the right parser
by file extension — PDF, DOCX, or an image (PNG/JPG, via local OCR)
today. Callers only need `.ok` / `.text` / `.error`, so every parser's
result type works interchangeably."""
from pathlib import Path
from typing import Union

from src.docx_parser import extract_text_from_docx
from src.ocr_parser import extract_text_from_image, ocr_scanned_pdf
from src.pdf_parser import ParsedPDF, extract_text_from_pdf

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".png", ".jpg", ".jpeg")
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def load_document(source: Union[str, Path, bytes], source_name: str):
    ext = Path(source_name).suffix.lower()

    if ext == ".pdf":
        result = extract_text_from_pdf(source, source_name=source_name)
        if result.ok:
            return result
        # No extractable text layer often means a scanned PDF — try OCR
        # before giving up, rather than failing a document that's
        # perfectly readable to a human.
        ocr_result = ocr_scanned_pdf(source)
        if ocr_result.ok:
            return ParsedPDF(source_name=source_name, text=ocr_result.text, num_pages=result.num_pages, ok=True)
        return result  # keep the original, more specific PDF error

    if ext == ".docx":
        return extract_text_from_docx(source, source_name=source_name)

    if ext in _IMAGE_EXTENSIONS:
        ocr_result = extract_text_from_image(source)
        return ParsedPDF(source_name=source_name, text=ocr_result.text, num_pages=1, ok=ocr_result.ok, error=ocr_result.error)

    raise ValueError(f"Unsupported file type '{ext}' for {source_name} — expected one of {SUPPORTED_EXTENSIONS}")
