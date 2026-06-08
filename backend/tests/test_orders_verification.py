"""
Tests for Sprint 3 verification endpoints:
  PUT  /api/v1/orders/{id}/verification
  POST /api/v1/orders/{id}/confirm
  GET  /api/v1/orders/{id}/cover-preview.pdf
  GET  /api/v1/orders/{id}/cd-preview.pdf
  GET  /api/v1/orders/{id}/cover.docx
  GET  /api/v1/orders/{id}/cd.docx
  GET  /api/v1/orders/{id}/verification-slip.pdf
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import analysis_cache
from app.services.analysis_cache import AnalysisRecord
from app.schemas.order import (
    AnalyzeResponse, ExtractedFields, PageCounts, PricingBreakdown, SlotPreview
)

client = TestClient(app)

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", ".planning", "client-sample"
)
INFO_PAGE_PDF = os.path.join(FIXTURES_DIR, "Info-Page-Sample.pdf")


def _extracted():
    return ExtractedFields(
        full_name="Jafni Syazani bin Mohd Nazrin",
        thesis_title="Experimental Investigation of Depth Effects on CO2 Corrosion",
        student_id="21000201",
        course_code="CV",
        degree="B.Eng (Hons) Civil Engineering",
        year="JAN 2026",
        project_type="FYP",
        extraction_method="heuristic",
        confidence="high",
    )


def _make_record() -> tuple[str, AnalysisRecord]:
    """Seed the cache with a minimal record; return (analysis_id, record)."""
    analysis_id = analysis_cache.generate_analysis_id()
    response = AnalyzeResponse(
        analysis_id=analysis_id,
        extracted=_extracted(),
        pages=PageCounts(total_pages=128, bw_pages=121, color_pages=7, color_page_numbers=[1, 12]),
        pricing=PricingBreakdown(
            cover_price=36.0, bw_print_price=12.1, color_print_price=2.1,
            cd_price=0.0, delivery_price=0.0, fast_track_price=0.0, grand_total=50.2,
        ),
        slot_preview=SlotPreview(allocated_date="2026-06-07", remaining_capacity=40, cutoff_applied=False),
    )
    record = AnalysisRecord(response=response)
    analysis_cache.put(analysis_id, record)
    return analysis_id, record


# ─── PUT /verification ────────────────────────────────────────────────────────

def _mock_render():
    """Context manager that patches _render_previews to be a no-op."""
    return patch("app.routers.orders._render_previews")


def test_put_verification_updates_fields():
    aid, _ = _make_record()
    with _mock_render():
        resp = client.put(f"/api/v1/orders/{aid}/verification", json={
            "full_name": "New Name",
            "thesis_title": "New Title",
            "student_id": "99999999",
            "course_code": "ME",
            "year": "JUN 2026",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted"]["full_name"] == "New Name"
    assert body["extracted"]["course_code"] == "ME"
    assert body["render_version"] == 1
    assert body["locked"] is False


def test_put_verification_bumps_render_version_on_repeated_calls():
    aid, _ = _make_record()
    with _mock_render():
        client.put(f"/api/v1/orders/{aid}/verification", json={
            "full_name": "A", "thesis_title": "T", "student_id": "1",
            "course_code": "CV", "year": "JAN 2026",
        })
        resp = client.put(f"/api/v1/orders/{aid}/verification", json={
            "full_name": "B", "thesis_title": "T", "student_id": "1",
            "course_code": "CV", "year": "JAN 2026",
        })
    assert resp.json()["render_version"] == 2


def test_put_verification_on_unknown_id_returns_404():
    with _mock_render():
        resp = client.put("/api/v1/orders/anl_00000000_999/verification", json={
            "full_name": "X", "thesis_title": "X", "student_id": "1",
            "course_code": "CV", "year": "JAN 2026",
        })
    assert resp.status_code == 404


def test_put_verification_on_locked_record_returns_409():
    aid, _ = _make_record()
    analysis_cache.lock(aid)
    with _mock_render():
        resp = client.put(f"/api/v1/orders/{aid}/verification", json={
            "full_name": "X", "thesis_title": "X", "student_id": "1",
            "course_code": "CV", "year": "JAN 2026",
        })
    assert resp.status_code == 409


# ─── POST /confirm ────────────────────────────────────────────────────────────

def test_post_confirm_locks_record():
    aid, _ = _make_record()
    resp = client.post(f"/api/v1/orders/{aid}/confirm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "AWAITING_PAYMENT"
    assert body["locked"] is True

    record = analysis_cache.get_record(aid)
    assert record.locked is True
    assert record.status == "AWAITING_PAYMENT"


def test_post_confirm_twice_returns_409():
    aid, _ = _make_record()
    client.post(f"/api/v1/orders/{aid}/confirm")
    resp = client.post(f"/api/v1/orders/{aid}/confirm")
    assert resp.status_code == 409


def test_post_confirm_unknown_id_returns_404():
    resp = client.post("/api/v1/orders/anl_00000000_999/confirm")
    assert resp.status_code == 404


# ─── GET /cover-preview.pdf and /cd-preview.pdf ───────────────────────────────

def test_get_cover_preview_returns_pdf_bytes(tmp_path):
    aid, record = _make_record()
    fake_pdf = tmp_path / "cover.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake-cover")
    record.cover_pdf_path = fake_pdf

    resp = client.get(f"/api/v1/orders/{aid}/cover-preview.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-1.4 fake-cover"


def test_get_cd_preview_returns_pdf_bytes(tmp_path):
    aid, record = _make_record()
    fake_pdf = tmp_path / "cd.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake-cd")
    record.cd_pdf_path = fake_pdf

    resp = client.get(f"/api/v1/orders/{aid}/cd-preview.pdf")
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 fake-cd"


def test_get_cover_preview_404_when_no_pdf():
    aid, _ = _make_record()
    resp = client.get(f"/api/v1/orders/{aid}/cover-preview.pdf")
    assert resp.status_code == 404


# ─── GET DOCX fallbacks ───────────────────────────────────────────────────────

def test_get_cover_docx_returns_docx_bytes(tmp_path):
    aid, record = _make_record()
    fake_docx = tmp_path / "cover.docx"
    fake_docx.write_bytes(b"PK fake docx")
    record.cover_docx_path = fake_docx

    resp = client.get(f"/api/v1/orders/{aid}/cover.docx")
    assert resp.status_code == 200
    assert "wordprocessingml" in resp.headers["content-type"]


def test_get_cd_docx_returns_docx_bytes(tmp_path):
    aid, record = _make_record()
    fake_docx = tmp_path / "cd.docx"
    fake_docx.write_bytes(b"PK fake docx")
    record.cd_docx_path = fake_docx

    resp = client.get(f"/api/v1/orders/{aid}/cd.docx")
    assert resp.status_code == 200


# ─── GET /verification-slip.pdf ──────────────────────────────────────────────

def test_get_slip_404_before_confirm():
    aid, _ = _make_record()
    resp = client.get(f"/api/v1/orders/{aid}/verification-slip.pdf")
    assert resp.status_code == 404


def test_confirm_returns_slip_url_and_get_serves_pdf(tmp_path):
    aid, record = _make_record()
    fake_slip = tmp_path / "verification-slip.pdf"
    fake_slip.write_bytes(b"%PDF-1.4 fake-slip")

    with patch("app.routers.orders.verification_slip_service.generate", return_value=fake_slip):
        resp = client.post(f"/api/v1/orders/{aid}/confirm")

    assert resp.status_code == 200
    body = resp.json()
    assert body["verification_slip_url"] == f"/api/v1/orders/{aid}/verification-slip.pdf"
    assert body["confirmed_at"] is not None

    # Manually wire path since we patched the service
    record = analysis_cache.get_record(aid)
    record.verification_slip_path = fake_slip

    slip_resp = client.get(f"/api/v1/orders/{aid}/verification-slip.pdf")
    assert slip_resp.status_code == 200
    assert slip_resp.content == b"%PDF-1.4 fake-slip"


# ─── Analyze endpoint backward compatibility ──────────────────────────────────

def test_analyze_response_includes_preview_urls():
    if not os.path.exists(INFO_PAGE_PDF):
        pytest.skip("fixture not found")

    with open(INFO_PAGE_PDF, "rb") as f:
        with _mock_render() as mock:
            resp = client.post(
                "/api/v1/orders/analyze",
                data={
                    "full_name": "Test", "email": "t@t.com", "phone": "+60123456789",
                    "student_id": "21000000", "num_hardbound": "1", "num_cd": "0",
                    "delivery_option": "SELF_PICKUP", "fast_track": "false",
                },
                files={"thesis_pdf": ("info-page.pdf", f, "application/pdf")},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "preview_urls" in body
    assert "hardbound_cover" in body["preview_urls"]
    assert "cd_case" in body["preview_urls"]
