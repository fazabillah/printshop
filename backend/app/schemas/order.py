from typing import Optional
from pydantic import BaseModel


class AvailabilityResponse(BaseModel):
    date: str
    remaining_capacity: int
    fast_track_remaining: int
    cutoff_applied: bool
    next_available_date: Optional[str] = None


class ExtractedFields(BaseModel):
    full_name: str
    thesis_title: str
    student_id: str
    course_code: str
    degree: str
    year: str
    project_type: str       # "FYP" or "POSTGRAD"
    extraction_method: str  # "heuristic" or "llm"
    confidence: str         # "high", "medium", "low"


class PageCounts(BaseModel):
    total_pages: int
    bw_pages: int
    color_pages: int
    color_page_numbers: list[int] = []


class PricingBreakdown(BaseModel):
    cover_price: float
    bw_print_price: float
    color_print_price: float
    cd_price: float
    delivery_price: float
    fast_track_price: float
    grand_total: float


class SlotPreview(BaseModel):
    allocated_date: str
    remaining_capacity: int
    cutoff_applied: bool


class PreviewUrls(BaseModel):
    hardbound_cover: str
    cd_case: str
    hardbound_cover_docx: str
    cd_case_docx: str


class AnalyzeResponse(BaseModel):
    analysis_id: str
    extracted: ExtractedFields
    pages: PageCounts
    pricing: PricingBreakdown
    slot_preview: SlotPreview
    preview_urls: Optional[PreviewUrls] = None
    preview_failed: bool = False
    shipping_address: Optional[str] = None


class VerificationRequest(BaseModel):
    full_name: str
    thesis_title: str
    student_id: str
    course_code: str
    degree: Optional[str] = None
    year: str


class VerificationResponse(BaseModel):
    analysis_id: str
    extracted: ExtractedFields
    preview_urls: PreviewUrls
    preview_failed: bool
    render_version: int
    locked: bool


class ConfirmResponse(BaseModel):
    analysis_id: str
    status: str
    locked: bool
    verification_slip_url: Optional[str] = None
    confirmed_at: Optional[str] = None  # ISO 8601
