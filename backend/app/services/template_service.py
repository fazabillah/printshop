import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from app.core.config import settings
from app.core.course_codes import course_label

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


class TemplateConversionError(Exception):
    pass


# ─── Public API ───────────────────────────────────────────────────────────────

def fill_hardbound(fields: dict, out_dir: Path) -> Path:
    """Fill hardbound cover template and convert to PDF. Returns the PDF path."""
    docx_path = fill_hardbound_docx(fields, out_dir)
    return _convert_to_pdf(docx_path, out_dir)


def fill_cd_case(fields: dict, out_dir: Path) -> Path:
    """Fill CD case template and convert to PDF. Returns the PDF path."""
    docx_path = fill_cd_case_docx(fields, out_dir)
    return _convert_to_pdf(docx_path, out_dir)


def fill_hardbound_docx(fields: dict, out_dir: Path) -> Path:
    """Fill hardbound cover template and return the filled DOCX path."""
    mapping = _build_mapping(fields)
    return _render("hardbound.docx", mapping, out_dir)


def fill_cd_case_docx(fields: dict, out_dir: Path) -> Path:
    """Fill CD case template and return the filled DOCX path."""
    mapping = _build_mapping(fields)
    return _render("cd_case.docx", mapping, out_dir)


# ─── Internals ────────────────────────────────────────────────────────────────

def _build_mapping(fields: dict) -> dict:
    return {
        "{{TITLE}}":      fields.get("thesis_title", "").upper(),
        "{{FULL_NAME}}":  fields.get("full_name", "").upper(),
        "{{STUDENT_ID}}": fields.get("student_id", ""),
        "{{COURSE}}":     course_label(fields.get("course_code", "OTHER")).upper(),
        "{{MONTH_YEAR}}": fields.get("year", "").upper(),
    }


def _render(template_name: str, mapping: dict, out_dir: Path) -> Path:
    """Copy template, replace all placeholder tokens, return output DOCX path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    src = _TEMPLATES_DIR / template_name
    dst = out_dir / template_name
    shutil.copy2(src, dst)

    doc = Document(dst)

    # Replace in body paragraphs
    for p in doc.paragraphs:
        _replace_in_paragraph(p._p, mapping)

    # Replace in text boxes (w:txbxContent contains w:p elements)
    txbx_tag = qn("w:txbxContent")
    p_tag = qn("w:p")
    for txbx in doc.element.body.iter(txbx_tag):
        for p_el in txbx.iter(p_tag):
            _replace_in_paragraph(p_el, mapping)

    doc.save(dst)
    return dst


def _replace_in_paragraph(p_el, mapping: dict) -> None:
    """
    Join all run text in a paragraph, apply placeholder substitutions,
    write result into the first run, clear the rest.

    This handles the common case where autosave splits a placeholder across
    multiple runs: e.g. "{{TIT" in run 0, "LE}}" in run 1.
    """
    r_tag = qn("w:r")
    t_tag = qn("w:t")

    runs = p_el.findall(r_tag)
    if not runs:
        return

    full_text = "".join(
        t.text or "" for r in runs for t in r.findall(t_tag)
    )

    replaced = full_text
    for placeholder, value in mapping.items():
        replaced = replaced.replace(placeholder, value)

    if replaced == full_text:
        return  # nothing changed in this paragraph

    # Write the result to the last run (which typically holds correct formatting)
    target_r = runs[-1]
    t_els = target_r.findall(t_tag)
    if t_els:
        t_els[0].text = replaced
        # Preserve xml:space="preserve" so leading/trailing spaces survive
        if replaced != replaced.strip():
            t_els[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for extra in t_els[1:]:
            target_r.remove(extra)
    else:
        t_el = _make_t(replaced)
        target_r.append(t_el)

    # Clear text from all other runs (leave them for their rPr / formatting)
    for r in runs[:-1]:
        for t in r.findall(t_tag):
            t.text = ""


def _make_t(text: str):
    from lxml import etree
    t_el = etree.Element(qn("w:t"))
    t_el.text = text
    if text != text.strip():
        t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return t_el


def _convert_to_pdf(docx_path: Path, out_dir: Path) -> Path:
    """Run LibreOffice headless conversion. Raises TemplateConversionError on failure."""
    cmd = [
        settings.libreoffice_bin,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(out_dir),
        str(docx_path),
    ]
    logger.info("soffice convert: %s", docx_path.name)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except FileNotFoundError:
        raise TemplateConversionError(
            f"LibreOffice not found at {settings.libreoffice_bin}. "
            "Install LibreOffice or set LIBREOFFICE_BIN."
        )
    except subprocess.TimeoutExpired:
        raise TemplateConversionError("LibreOffice conversion timed out after 60 s")

    if result.returncode != 0:
        raise TemplateConversionError(
            f"LibreOffice exited {result.returncode}: {result.stderr.strip()}"
        )

    pdf_path = out_dir / docx_path.with_suffix(".pdf").name
    if not pdf_path.exists():
        raise TemplateConversionError(
            f"LibreOffice reported success but PDF not found at {pdf_path}"
        )
    return pdf_path
