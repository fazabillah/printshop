import logging
import os
import tempfile
from datetime import date as date_type
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse

from app.schemas.order import (
    AnalyzeResponse,
    AvailabilityResponse,
    ConfirmResponse,
    PreviewUrls,
    SlotPreview,
    VerificationRequest,
    VerificationResponse,
)
from app.services import analysis_cache, pdf_extraction_service, pdf_analysis_service, pricing_service
from app.services.analysis_cache import AnalysisRecord
from app.services import template_service, verification_slip_service
from app.services.template_service import TemplateConversionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

MAX_PDF_BYTES = 30 * 1024 * 1024  # VAL-002
_PREVIEW_BASE_DIR = Path(tempfile.gettempdir()) / "printshop"


def _preview_dir(analysis_id: str, version: int) -> Path:
    return _PREVIEW_BASE_DIR / analysis_id / f"v{version}"


def _build_preview_urls(analysis_id: str, version: int) -> PreviewUrls:
    base = f"/api/v1/orders/{analysis_id}"
    return PreviewUrls(
        hardbound_cover=f"{base}/cover-preview.pdf?v={version}",
        cd_case=f"{base}/cd-preview.pdf?v={version}",
        hardbound_cover_docx=f"{base}/cover.docx",
        cd_case_docx=f"{base}/cd.docx",
    )


def _render_previews(record: AnalysisRecord, analysis_id: str) -> None:
    """Fill templates and convert to PDF; update record in-place."""
    version = record.render_version
    out_dir = _preview_dir(analysis_id, version)
    fields = record.response.extracted.model_dump()
    needs_cd = record.response.pricing.cd_price > 0

    # Fill DOCX first — always needed, even as PDF fallback download
    try:
        cover_docx = template_service.fill_hardbound_docx(fields, out_dir)
        record.cover_docx_path = cover_docx
        if needs_cd:
            cd_docx = template_service.fill_cd_case_docx(fields, out_dir)
            record.cd_docx_path = cd_docx
        else:
            record.cd_docx_path = None
    except Exception as exc:
        logger.warning("DOCX fill failed for %s: %s", analysis_id, exc)
        record.cover_pdf_path = None
        record.cd_pdf_path = None
        record.preview_failed = True
        return

    # Convert to PDF (best-effort; DOCX fallback remains available on failure)
    try:
        cover_pdf = template_service._convert_to_pdf(cover_docx, out_dir)
        record.cover_pdf_path = cover_pdf
        if needs_cd:
            cd_pdf = template_service._convert_to_pdf(cd_docx, out_dir)
            record.cd_pdf_path = cd_pdf
        else:
            record.cd_pdf_path = None
        record.preview_failed = False
    except TemplateConversionError as exc:
        logger.warning("PDF conversion failed for %s: %s", analysis_id, exc)
        record.cover_pdf_path = None
        record.cd_pdf_path = None
        record.preview_failed = True


def _cleanup_old_versions(analysis_id: str, current_version: int) -> None:
    base = _PREVIEW_BASE_DIR / analysis_id
    if not base.exists():
        return
    for child in base.iterdir():
        if child.is_dir() and child.name != f"v{current_version}":
            import shutil
            shutil.rmtree(child, ignore_errors=True)


@router.get("/availability", response_model=AvailabilityResponse)
def get_availability(date: str = Query(default=None, description="YYYY-MM-DD")):
    target_date = date or date_type.today().isoformat()
    try:
        date_type.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")

    # Stub — real capacity tracked against Google Sheets in Sprint 05
    return AvailabilityResponse(
        date=target_date,
        remaining_capacity=40,
        fast_track_remaining=10,
        cutoff_applied=False,
        next_available_date=None,
    )


@router.get("/{analysis_id}/analysis", response_model=AnalyzeResponse)
def get_analysis(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    resp = record.response
    if record.cover_pdf_path or record.cover_docx_path:
        resp = resp.model_copy(update={
            "preview_urls": _build_preview_urls(analysis_id, record.render_version),
            "preview_failed": record.preview_failed,
        })
    return resp


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_order(
    thesis_pdf: UploadFile = File(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    student_id: str = Form(...),
    num_hardbound: int = Form(...),
    num_cd: int = Form(...),
    delivery_option: str = Form(...),
    fast_track: bool = Form(False),
    shipping_address: Optional[str] = Form(None),
):
    # VAL-003: shipping_address required for non-pickup deliveries
    _DELIVERY_NEEDS_ADDRESS = {"UTP_DELIVERY", "POSTAGE_SEMENANJUNG", "POSTAGE_SABAH_SARAWAK", "POSTAGE_INTERNATIONAL"}
    if delivery_option in _DELIVERY_NEEDS_ADDRESS and not (shipping_address or "").strip():
        raise HTTPException(status_code=400, detail="shipping_address is required for this delivery option (VAL-003)")

    # VAL-001: PDF only
    if thesis_pdf.content_type not in ("application/pdf", "application/octet-stream") and not (
        thesis_pdf.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted (VAL-001)")

    content = await thesis_pdf.read()

    # VAL-002: max 30 MB
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=422, detail="Thesis PDF must be under 30 MB (VAL-002)")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(
            "analyze_order | student=%s | id=%s | hardbound=%d | cd=%d | delivery=%s | fast_track=%s | file=%s | bytes=%d",
            full_name, student_id, num_hardbound, num_cd, delivery_option, fast_track,
            thesis_pdf.filename, len(content),
        )

        extracted, page_texts = pdf_extraction_service.extract_info(tmp_path)

        if extracted.confidence == "low":
            extracted = pdf_extraction_service.extract_info_llm(page_texts, extracted)

        if not extracted.student_id:
            extracted = extracted.model_copy(update={"student_id": student_id})
        if not extracted.full_name:
            extracted = extracted.model_copy(update={"full_name": full_name})

        pages = pdf_analysis_service.classify_pages(tmp_path)

        pricing = pricing_service.calculate_pricing(
            project_type=extracted.project_type,
            course_code=extracted.course_code,
            num_hardbound=num_hardbound,
            num_cd=num_cd,
            bw_pages=pages.bw_pages,
            color_pages=pages.color_pages,
            delivery_option=delivery_option,
            fast_track=fast_track,
        )

        slot_preview = SlotPreview(
            allocated_date=date_type.today().isoformat(),
            remaining_capacity=40,
            cutoff_applied=False,
        )

        analysis_id = analysis_cache.generate_analysis_id()
        response = AnalyzeResponse(
            analysis_id=analysis_id,
            extracted=extracted,
            pages=pages,
            pricing=pricing,
            slot_preview=slot_preview,
            shipping_address=shipping_address,
        )

        record = AnalysisRecord(response=response, shipping_address=shipping_address)
        analysis_cache.put(analysis_id, record)

        # Initial template render (best-effort; failure surfaced as preview_failed)
        _render_previews(record, analysis_id)
        if not record.preview_failed:
            response = response.model_copy(update={
                "preview_urls": _build_preview_urls(analysis_id, record.render_version),
                "preview_failed": False,
            })
        else:
            response = response.model_copy(update={
                "preview_urls": _build_preview_urls(analysis_id, record.render_version),
                "preview_failed": True,
            })
        record.response = response
        return response

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.put("/{analysis_id}/verification", response_model=VerificationResponse)
def update_verification(analysis_id: str, body: VerificationRequest):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.locked:
        raise HTTPException(status_code=409, detail="order already confirmed; fields are locked")

    edits = body.model_dump(exclude_none=True)
    if "degree" in edits and edits["degree"] is None:
        del edits["degree"]

    record = analysis_cache.update_extracted(analysis_id, edits)

    _cleanup_old_versions(analysis_id, record.render_version)
    _render_previews(record, analysis_id)

    return VerificationResponse(
        analysis_id=analysis_id,
        extracted=record.response.extracted,
        preview_urls=_build_preview_urls(analysis_id, record.render_version),
        preview_failed=record.preview_failed,
        render_version=record.render_version,
        locked=record.locked,
    )


@router.post("/{analysis_id}/confirm", response_model=ConfirmResponse)
def confirm_verification(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.locked:
        raise HTTPException(status_code=409, detail="order already confirmed")

    analysis_cache.lock(analysis_id)

    slip_url: Optional[str] = None
    confirmed_at_str: Optional[str] = None
    if record.confirmed_at:
        confirmed_at_str = record.confirmed_at.isoformat()

    try:
        slip_dir = _preview_dir(analysis_id, record.render_version)
        slip_path = verification_slip_service.generate(record, analysis_id, slip_dir)
        record.verification_slip_path = slip_path
        slip_url = f"/api/v1/orders/{analysis_id}/verification-slip.pdf"
    except Exception as exc:
        logger.warning("Verification slip generation failed for %s: %s", analysis_id, exc)

    return ConfirmResponse(
        analysis_id=analysis_id,
        status="AWAITING_PAYMENT",
        locked=True,
        verification_slip_url=slip_url,
        confirmed_at=confirmed_at_str,
    )


@router.get("/{analysis_id}/cover-preview.pdf")
def get_cover_preview(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.cover_pdf_path is None or not record.cover_pdf_path.exists():
        raise HTTPException(status_code=404, detail="cover preview not available")
    return FileResponse(
        path=str(record.cover_pdf_path),
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{analysis_id}/cd-preview.pdf")
def get_cd_preview(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.cd_pdf_path is None or not record.cd_pdf_path.exists():
        raise HTTPException(status_code=404, detail="CD preview not available")
    return FileResponse(
        path=str(record.cd_pdf_path),
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{analysis_id}/cover.docx")
def get_cover_docx(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.cover_docx_path is None or not record.cover_docx_path.exists():
        raise HTTPException(status_code=404, detail="cover DOCX not available")
    return FileResponse(
        path=str(record.cover_docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="hardbound_cover.docx",
    )


@router.get("/{analysis_id}/cd.docx")
def get_cd_docx(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.cd_docx_path is None or not record.cd_docx_path.exists():
        raise HTTPException(status_code=404, detail="CD DOCX not available")
    return FileResponse(
        path=str(record.cd_docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="cd_case.docx",
    )


@router.get("/{analysis_id}/verification-slip.pdf")
def get_verification_slip(analysis_id: str):
    record = analysis_cache.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    if record.verification_slip_path is None or not record.verification_slip_path.exists():
        raise HTTPException(status_code=404, detail="verification slip not available")
    return FileResponse(
        path=str(record.verification_slip_path),
        media_type="application/pdf",
        filename=f"verification-slip-{analysis_id}.pdf",
        headers={"Content-Disposition": f'attachment; filename="verification-slip-{analysis_id}.pdf"'},
    )
