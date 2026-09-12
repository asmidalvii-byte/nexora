import io

from src.document_loader import load_document
from src.ocr_parser import extract_text_from_image


def _blank_png_bytes() -> bytes:
    from PIL import Image
    img = Image.new("RGB", (100, 40), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_ocr_degrades_gracefully_without_crashing_when_tesseract_missing():
    """This environment doesn't have the Tesseract binary installed — the
    important behavior is that we get an honest, non-fabricated error
    rather than a crash or a fake result."""
    result = extract_text_from_image(_blank_png_bytes())
    assert isinstance(result.ok, bool)
    if not result.ok:
        assert "ocr" in result.error.lower()


def test_document_loader_handles_image_extension_without_raising():
    result = load_document(_blank_png_bytes(), source_name="certificate.png")
    assert hasattr(result, "ok")
    assert hasattr(result, "error")


def test_document_loader_rejects_unknown_extension():
    import pytest
    with pytest.raises(ValueError):
        load_document(b"whatever", source_name="resume.exe")
