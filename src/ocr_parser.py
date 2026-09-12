"""Local OCR for image-based supporting documents (PNG/JPG) and scanned
PDFs with no extractable text layer. Uses pytesseract (a wrapper around
the local Tesseract binary) — no cloud OCR API, no API key.

Tesseract itself is a separate system binary pytesseract shells out to.
When it isn't installed, every call here fails in a well-defined way that
callers turn into the honest "OCR unavailable" message the spec requires
— never a fabricated result, never a crash of the whole upload.
"""
from dataclasses import dataclass
from io import BytesIO
from typing import Union


@dataclass
class OCRResult:
    text: str
    ok: bool
    error: str = ""


def _tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 - binary missing, misconfigured, or pytesseract itself absent
        return False


def extract_text_from_image(source: Union[bytes, str]) -> OCRResult:
    if not _tesseract_available():
        return OCRResult(text="", ok=False, error="OCR unavailable: Tesseract is not installed on this machine.")

    try:
        import pytesseract
        from PIL import Image

        image = Image.open(BytesIO(source)) if isinstance(source, bytes) else Image.open(source)
        text = pytesseract.image_to_string(image)
    except Exception as exc:  # noqa: BLE001
        return OCRResult(text="", ok=False, error=f"OCR failed: {exc}")

    if not text.strip():
        return OCRResult(text="", ok=False, error="OCR ran but found no readable text in the image.")
    return OCRResult(text=text, ok=True)


def ocr_scanned_pdf(source: Union[bytes, str]) -> OCRResult:
    """Fallback for a PDF with no extractable text layer (a scanned
    document) — renders each page to an image and OCRs it."""
    if not _tesseract_available():
        return OCRResult(text="", ok=False, error="OCR unavailable: Tesseract is not installed on this machine.")

    try:
        import pymupdf as fitz
        import pytesseract
        from PIL import Image

        doc = fitz.open(stream=source, filetype="pdf") if isinstance(source, bytes) else fitz.open(source)
        page_texts = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            image = Image.open(BytesIO(pix.tobytes("png")))
            page_texts.append(pytesseract.image_to_string(image))
        doc.close()
        text = "\n".join(page_texts)
    except Exception as exc:  # noqa: BLE001
        return OCRResult(text="", ok=False, error=f"OCR failed on scanned PDF: {exc}")

    if not text.strip():
        return OCRResult(text="", ok=False, error="OCR ran but found no readable text in the scanned PDF.")
    return OCRResult(text=text, ok=True)
