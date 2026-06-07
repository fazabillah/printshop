import re
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF

from app.core.config import settings
from app.core.course_codes import map_course_to_code, derive_project_type
from app.schemas.order import ExtractedFields

logger = logging.getLogger(__name__)

_MONTH_RE = re.compile(
    r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{4}\b",
    re.IGNORECASE,
)
_ID_RE = re.compile(r"\b\d{7,9}\b")
_PAREN_RE = re.compile(r"\(([^)]+)\)")
# Degree honorifics to skip when searching for the course name in parentheses
_IGNORED_PAREN_TOKENS = {"hons", "honours", "honors"}
# Header lines on UTP info pages that are not part of the thesis title
_HEADER_NOISE_RE = re.compile(
    r"universit|faculty|department|school of|college of|petronas|institute",
    re.IGNORECASE,
)


@dataclass
class _HeuristicResult:
    title: Optional[str] = None
    name: Optional[str] = None
    student_id: Optional[str] = None
    degree: Optional[str] = None
    course: Optional[str] = None
    year: Optional[str] = None
    page_texts: list[str] = field(default_factory=list)


def _extract_heuristic(pdf_path: str) -> _HeuristicResult:
    doc = fitz.open(pdf_path)
    result = _HeuristicResult()
    all_lines: list[str] = []
    largest_font = 0.0
    largest_text = ""
    # Lines from the page that contains the bare "by" line (the UTP info page)
    info_page_lines: list[str] | None = None

    for page_idx in range(min(5, len(doc))):
        page = doc[page_idx]
        raw_text = page.get_text("text")
        result.page_texts.append(raw_text)
        page_lines = [ln.strip() for ln in raw_text.splitlines()]
        all_lines.extend(page_lines)

        if info_page_lines is None:
            for ln in page_lines:
                if ln.lower() == "by":
                    info_page_lines = page_lines
                    break

        # Fallback title: block with the largest font on first pages
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = span.get("size", 0)
                    if size > largest_font and len(text) > 10:
                        largest_font = size
                        largest_text = text

    doc.close()

    # Title: prefer lines above "by" on the info page (standard UTP layout puts
    # the title directly above the "by / Author" block). Fall back to largest-font
    # span for PDFs that don't follow this layout.
    if info_page_lines is not None:
        by_idx = next(
            (i for i, ln in enumerate(info_page_lines) if ln.lower() == "by"), None
        )
        if by_idx is not None:
            title_parts = [
                ln for ln in info_page_lines[:by_idx]
                if ln and not _HEADER_NOISE_RE.search(ln)
            ]
            if title_parts:
                result.title = " ".join(title_parts).strip() or None

    if not result.title:
        result.title = largest_text.strip() or None

    # Name: line after a bare "by" line (case-insensitive)
    for i, line in enumerate(all_lines):
        if line.lower() == "by":
            for j in range(i + 1, min(i + 4, len(all_lines))):
                candidate = all_lines[j].strip()
                if candidate:
                    result.name = candidate
                    break
            break

    # Student ID: prefer match near name; fall back to first match anywhere
    name_line_idx = None
    if result.name:
        for i, line in enumerate(all_lines):
            if result.name in line:
                name_line_idx = i
                break

    for i, line in enumerate(all_lines):
        m = _ID_RE.search(line)
        if m:
            if name_line_idx is None or abs(i - name_line_idx) <= 5:
                result.student_id = m.group()
                break

    if result.student_id is None:
        # wider scan
        for line in all_lines:
            m = _ID_RE.search(line)
            if m:
                result.student_id = m.group()
                break

    # Degree: first line with Bachelor / Master / Doctor
    degree_line_idx = None
    for i, line in enumerate(all_lines):
        lower = line.lower()
        if "bachelor" in lower or "master" in lower or "doctor" in lower:
            result.degree = line.strip()
            degree_line_idx = i
            break

    # Course: first parenthesised token near the degree line that is not a
    # degree honorific like "(Hons)". The UTP format writes "(Civil Engineering)"
    # on the line after "Bachelor of Engineering (Hons)".
    if degree_line_idx is not None:
        search_range = all_lines[degree_line_idx: degree_line_idx + 4]
        combined = " ".join(search_range)
        for m in _PAREN_RE.finditer(combined):
            token = m.group(1).strip()
            if token.lower() not in _IGNORED_PAREN_TOKENS:
                result.course = token
                break

    # Year
    for line in all_lines:
        m = _MONTH_RE.search(line)
        if m:
            result.year = m.group().upper()
            break

    return result


def _is_low_confidence(r: _HeuristicResult) -> bool:
    if not r.title or len(r.title) < 20:
        return True
    if not r.name:
        return True
    if not r.student_id or not _ID_RE.fullmatch(r.student_id):
        return True
    if not r.degree:
        return True
    if not r.year:
        return True
    return False


def _build_extracted_fields(r: _HeuristicResult, method: str, confidence: str) -> ExtractedFields:
    course_name = r.course or ""
    course_code = map_course_to_code(course_name)
    project_type = derive_project_type(r.degree or "")
    return ExtractedFields(
        full_name=r.name or "",
        thesis_title=r.title or "",
        student_id=r.student_id or "",
        course_code=course_code,
        degree=r.degree or "",
        year=r.year or "",
        project_type=project_type,
        extraction_method=method,
        confidence=confidence,
    )


def extract_info(pdf_path: str) -> tuple[ExtractedFields, list[str]]:
    """Run heuristic extraction. Returns (fields, page_texts)."""
    r = _extract_heuristic(pdf_path)
    confidence = "low" if _is_low_confidence(r) else "high"
    fields = _build_extracted_fields(r, "heuristic", confidence)
    logger.info(
        "extract_info heuristic | title_len=%d | name=%s | id=%s | course=%s | confidence=%s",
        len(fields.thesis_title),
        bool(fields.full_name),
        bool(fields.student_id),
        fields.course_code,
        confidence,
    )
    return fields, r.page_texts


def extract_info_llm(page_texts: list[str], fallback_fields: ExtractedFields) -> ExtractedFields:
    """Claude Haiku fallback. Returns fallback_fields unchanged if key is absent or call fails."""
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping LLM fallback")
        return fallback_fields

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        combined_text = "\n\n".join(page_texts[:5])

        system_prompt = (
            "You are a thesis metadata extractor. "
            "Given the text from the first pages of a university thesis, "
            "return ONLY a JSON object with these exact keys: "
            "full_name, thesis_title, student_id, degree, course, year. "
            "course should be the plain English name (e.g. 'Civil Engineering'). "
            "year format: 'MON YYYY' (e.g. 'JAN 2026'). "
            "If a field is not found, use an empty string."
        )

        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract metadata from the following thesis pages. "
                        "Respond with only the JSON object, no markdown, no explanation.\n\n"
                        + combined_text
                    ),
                }
            ],
        )

        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[^\n]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)

        r = _HeuristicResult(
            title=data.get("thesis_title") or None,
            name=data.get("full_name") or None,
            student_id=data.get("student_id") or None,
            degree=data.get("degree") or None,
            course=data.get("course") or None,
            year=data.get("year") or None,
        )
        fields = _build_extracted_fields(r, "llm", "high")
        logger.info("extract_info_llm: success | course_code=%s", fields.course_code)
        return fields

    except Exception as exc:
        logger.error("extract_info_llm failed: %s — using heuristic fallback", exc)
        return fallback_fields
