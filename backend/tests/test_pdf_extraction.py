import os
import re
import pytest
from app.services.pdf_extraction_service import extract_info, extract_info_llm
from app.core.config import settings

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", ".planning", "client-sample"
)

INFO_PAGE_PDF = os.path.join(FIXTURES_DIR, "Info-Page-Sample.pdf")
JAFNI_PDF = os.path.join(
    FIXTURES_DIR,
    "Final Year Project - Dissertation_Jafni Syazani bin Mohd Nazrin (21000201) - updated - JAFNI. SYZN.pdf",
)
AMIRAH_PDF = os.path.join(
    FIXTURES_DIR,
    "20001349_Amirah Soffiya_Dissertation Softbound Final Draft (3) (1).pdf",
)

ID_RE = re.compile(r"^\d{7,9}$")


@pytest.mark.parametrize("pdf_path", [INFO_PAGE_PDF, JAFNI_PDF, AMIRAH_PDF])
def test_extract_info_returns_non_empty_fields(pdf_path):
    if not os.path.exists(pdf_path):
        pytest.skip(f"fixture not found: {pdf_path}")
    fields, page_texts = extract_info(pdf_path)
    assert len(page_texts) > 0
    # confidence and method are always set
    assert fields.extraction_method in ("heuristic",)
    assert fields.confidence in ("high", "low")
    assert fields.project_type in ("FYP", "POSTGRAD")


def test_extract_jafni_student_id():
    if not os.path.exists(JAFNI_PDF):
        pytest.skip(f"fixture not found: {JAFNI_PDF}")
    fields, _ = extract_info(JAFNI_PDF)
    assert fields.student_id == "21000201" or ID_RE.match(fields.student_id), (
        f"Expected 7-9 digit student ID, got: {fields.student_id!r}"
    )


def test_extract_jafni_course_is_fyp():
    if not os.path.exists(JAFNI_PDF):
        pytest.skip(f"fixture not found: {JAFNI_PDF}")
    fields, _ = extract_info(JAFNI_PDF)
    assert fields.project_type == "FYP"


def test_extract_jafni_title_is_thesis_title():
    """Title must not be the student name — it must contain the actual thesis subject."""
    if not os.path.exists(JAFNI_PDF):
        pytest.skip(f"fixture not found: {JAFNI_PDF}")
    fields, _ = extract_info(JAFNI_PDF)
    assert "SAVONIUS HYDROKINETIC TURBINE" in fields.thesis_title.upper(), (
        f"Title appears to be wrong (possibly picked up student name): {fields.thesis_title!r}"
    )


def test_extract_jafni_course_is_civil():
    """Course must map to CV (Civil Engineering), not OTHER."""
    if not os.path.exists(JAFNI_PDF):
        pytest.skip(f"fixture not found: {JAFNI_PDF}")
    fields, _ = extract_info(JAFNI_PDF)
    assert fields.course_code == "CV", (
        f"Expected CV, got: {fields.course_code!r}"
    )


def test_extract_info_page_course_is_civil():
    """Info-Page-Sample.pdf also contains (Civil Engineering) and must map to CV."""
    if not os.path.exists(INFO_PAGE_PDF):
        pytest.skip(f"fixture not found: {INFO_PAGE_PDF}")
    fields, _ = extract_info(INFO_PAGE_PDF)
    assert fields.course_code == "CV", (
        f"Expected CV, got: {fields.course_code!r}"
    )


def test_llm_fallback_skipped_without_key(monkeypatch):
    """When no API key, LLM fallback returns the fallback_fields unchanged."""
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    if not os.path.exists(INFO_PAGE_PDF):
        pytest.skip(f"fixture not found: {INFO_PAGE_PDF}")
    fields, page_texts = extract_info(INFO_PAGE_PDF)
    result = extract_info_llm(page_texts, fields)
    # Should return fallback unchanged
    assert result == fields


@pytest.mark.skipif(
    not settings.anthropic_api_key,
    reason="ANTHROPIC_API_KEY not set — skipping live LLM test",
)
def test_llm_fallback_live():
    if not os.path.exists(INFO_PAGE_PDF):
        pytest.skip(f"fixture not found: {INFO_PAGE_PDF}")
    fields, page_texts = extract_info(INFO_PAGE_PDF)
    result = extract_info_llm(page_texts, fields)
    assert result.extraction_method == "llm"
    assert result.confidence == "high"
    assert len(result.thesis_title) > 10
