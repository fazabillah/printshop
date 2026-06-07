import logging
import os
import tempfile
from datetime import date as date_type

from fastapi import APIRouter, Form, UploadFile, File, Query, HTTPException

from app.schemas.order import (
    AnalyzeResponse,
    AvailabilityResponse,
    SlotPreview,
)
from app.services import analysis_cache, pdf_extraction_service, pdf_analysis_service, pricing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

MAX_PDF_BYTES = 30 * 1024 * 1024  # VAL-002


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
    cached = analysis_cache.get(analysis_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="analysis expired or not found")
    return cached


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
):
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

        # Extract thesis metadata
        extracted, page_texts = pdf_extraction_service.extract_info(tmp_path)

        # LLM fallback if confidence is low
        if extracted.confidence == "low":
            extracted = pdf_extraction_service.extract_info_llm(page_texts, extracted)

        # Override student_id and full_name with form values only if extraction totally missed them
        # (form values are the user's own input and act as fallback per §13.4 request contract)
        if not extracted.student_id:
            extracted = extracted.model_copy(update={"student_id": student_id})
        if not extracted.full_name:
            extracted = extracted.model_copy(update={"full_name": full_name})

        # Page analysis (all pages)
        pages = pdf_analysis_service.classify_pages(tmp_path)

        # Pricing
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

        # Slot preview — real slot logic ships in Sprint 5
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
        )
        analysis_cache.put(analysis_id, response)
        return response

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
