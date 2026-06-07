import logging
from datetime import date as date_type

from fastapi import APIRouter, Form, UploadFile, File, Query

from app.schemas.order import (
    AnalyzeResponse,
    AvailabilityResponse,
    ExtractedFields,
    PageCounts,
    PricingBreakdown,
    SlotPreview,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("/availability", response_model=AvailabilityResponse)
def get_availability(date: str = Query(default=None, description="YYYY-MM-DD")):
    # Validate date format; default to today
    target_date = date or date_type.today().isoformat()
    try:
        date_type.fromisoformat(target_date)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")

    # Stub — real capacity tracked against Google Sheets in Sprint 05
    return AvailabilityResponse(
        date=target_date,
        remaining_capacity=40,
        fast_track_remaining=10,
        cutoff_applied=False,
        next_available_date=None,
    )


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
    logger.info(
        "analyze_order stub | student=%s | id=%s | hardbound=%d | cd=%d | delivery=%s | fast_track=%s | file=%s",
        full_name,
        student_id,
        num_hardbound,
        num_cd,
        delivery_option,
        fast_track,
        thesis_pdf.filename,
    )

    # Sprint 02 replaces this block with real PyMuPDF extraction + Claude Haiku fallback
    return AnalyzeResponse(
        analysis_id="anl_stub_001",
        extracted=ExtractedFields(
            full_name=full_name,
            thesis_title="[Extracted in Sprint 02]",
            student_id=student_id,
            course_code="CV",
            degree="B.Eng (Hons) Civil Engineering",
            year="JAN 2026",
            project_type="FYP",
            extraction_method="stub",
            confidence="low",
        ),
        pages=PageCounts(
            total_pages=128,
            bw_pages=121,
            color_pages=7,
        ),
        pricing=PricingBreakdown(
            cover_price=round(36.00 * num_hardbound, 2),
            bw_print_price=round(121 * 0.10, 2),
            color_print_price=round(7 * 0.30, 2),
            cd_price=round(4.00 * num_cd, 2),
            delivery_price=5.00,
            fast_track_price=10.00 if fast_track else 0.00,
            grand_total=round(
                36.00 * num_hardbound
                + 121 * 0.10
                + 7 * 0.30
                + 4.00 * num_cd
                + 5.00
                + (10.00 if fast_track else 0.00),
                2,
            ),
        ),
        slot_preview=SlotPreview(
            allocated_date=date_type.today().isoformat(),
            remaining_capacity=40,
            cutoff_applied=False,
        ),
    )
