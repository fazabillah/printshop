"""Tests for verification_slip_service."""
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

import pytest

from app.schemas.order import (
    AnalyzeResponse,
    ExtractedFields,
    PageCounts,
    PricingBreakdown,
    SlotPreview,
)
from app.services.analysis_cache import AnalysisRecord
from app.services import verification_slip_service


def _make_record(cover_pdf: Optional[Path] = None, cd_pdf: Optional[Path] = None) -> AnalysisRecord:
    extracted = ExtractedFields(
        full_name="JAFNI SYAZANI BIN MOHD NAZRIN",
        thesis_title="COMPARATIVE PETROGRAPHIC ANALYSIS",
        student_id="20000123",
        course_code="CV",
        degree="Bachelor of Engineering (Hons)",
        year="JAN 2026",
        project_type="FYP",
        extraction_method="heuristic",
        confidence="high",
    )
    pricing = PricingBreakdown(
        cover_price=36.0,
        bw_print_price=6.0,
        color_print_price=2.1,
        cd_price=4.0 if cd_pdf else 0.0,
        delivery_price=0.0,
        fast_track_price=0.0,
        grand_total=48.1 if cd_pdf else 44.1,
    )
    response = AnalyzeResponse(
        analysis_id="anl_test_001",
        extracted=extracted,
        pages=PageCounts(total_pages=67, bw_pages=60, color_pages=7),
        pricing=pricing,
        slot_preview=SlotPreview(
            allocated_date="2026-06-08",
            remaining_capacity=40,
            cutoff_applied=False,
        ),
    )
    record = AnalysisRecord(response=response)
    record.cover_pdf_path = cover_pdf
    record.cd_pdf_path = cd_pdf
    record.locked = True
    record.confirmed_at = datetime(2026, 6, 8, 10, 0, 0, tzinfo=timezone.utc)
    return record


def _make_minimal_pdf(path: Path) -> None:
    """Write a minimal valid PDF so fitz can open it."""
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Contents 4 0 R/Resources<<>>>>endobj\n"
        b"4 0 obj<</Length 0>>stream\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n0000000266 00000 n \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n317\n%%EOF\n"
    )


class TestGenerateWritesPdf:
    def test_output_is_valid_pdf(self, tmp_path):
        cover = tmp_path / "cover.pdf"
        cd = tmp_path / "cd.pdf"
        _make_minimal_pdf(cover)
        _make_minimal_pdf(cd)

        record = _make_record(cover_pdf=cover, cd_pdf=cd)
        result = verification_slip_service.generate(record, "anl_test_001", tmp_path)

        assert result.exists()
        assert result.read_bytes().startswith(b"%PDF")

    def test_output_filename(self, tmp_path):
        cover = tmp_path / "cover.pdf"
        _make_minimal_pdf(cover)
        record = _make_record(cover_pdf=cover)
        result = verification_slip_service.generate(record, "anl_test_001", tmp_path)
        assert result.name == "verification-slip.pdf"


class TestNoCdThumbnail:
    def test_skips_cd_when_none(self, tmp_path):
        cover = tmp_path / "cover.pdf"
        _make_minimal_pdf(cover)
        record = _make_record(cover_pdf=cover, cd_pdf=None)

        # Should not raise
        result = verification_slip_service.generate(record, "anl_test_001", tmp_path)
        assert result.exists()
        assert result.read_bytes().startswith(b"%PDF")


class TestMissingCoverPdf:
    def test_handles_missing_cover_gracefully(self, tmp_path):
        record = _make_record(cover_pdf=None, cd_pdf=None)

        # Should not raise — uses fallback text instead of thumbnail
        result = verification_slip_service.generate(record, "anl_test_001", tmp_path)
        assert result.exists()
        assert result.read_bytes().startswith(b"%PDF")
