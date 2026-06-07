import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", ".planning", "client-sample"
)

INFO_PAGE_PDF = os.path.join(FIXTURES_DIR, "Info-Page-Sample.pdf")

client = TestClient(app)


def _form_data():
    return {
        "full_name": "Test Student",
        "email": "test@example.com",
        "phone": "+60123456789",
        "student_id": "21000000",
        "num_hardbound": "1",
        "num_cd": "0",
        "delivery_option": "SELF_PICKUP",
        "fast_track": "false",
    }


@pytest.fixture
def pdf_file():
    if not os.path.exists(INFO_PAGE_PDF):
        pytest.skip(f"fixture not found: {INFO_PAGE_PDF}")
    with open(INFO_PAGE_PDF, "rb") as f:
        yield f


def test_analyze_returns_200_and_correct_shape(pdf_file):
    response = client.post(
        "/api/v1/orders/analyze",
        data=_form_data(),
        files={"thesis_pdf": ("info-page.pdf", pdf_file, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()

    assert "analysis_id" in body
    assert body["analysis_id"].startswith("anl_")

    extracted = body["extracted"]
    assert "full_name" in extracted
    assert "thesis_title" in extracted
    assert "student_id" in extracted
    assert "course_code" in extracted
    assert "degree" in extracted
    assert "year" in extracted
    assert "project_type" in extracted
    assert extracted["extraction_method"] in ("heuristic", "llm")
    assert extracted["confidence"] in ("high", "low")

    pages = body["pages"]
    assert pages["total_pages"] > 0
    assert pages["bw_pages"] + pages["color_pages"] == pages["total_pages"]

    pricing = body["pricing"]
    assert pricing["grand_total"] >= 0

    slot = body["slot_preview"]
    assert "allocated_date" in slot
    assert "remaining_capacity" in slot


def test_get_analysis_by_id(pdf_file):
    post_resp = client.post(
        "/api/v1/orders/analyze",
        data=_form_data(),
        files={"thesis_pdf": ("info-page.pdf", pdf_file, "application/pdf")},
    )
    assert post_resp.status_code == 200
    analysis_id = post_resp.json()["analysis_id"]

    get_resp = client.get(f"/api/v1/orders/{analysis_id}/analysis")
    assert get_resp.status_code == 200
    assert get_resp.json()["analysis_id"] == analysis_id


def test_get_analysis_unknown_id_returns_404():
    resp = client.get("/api/v1/orders/anl_00000000_999/analysis")
    assert resp.status_code == 404


def test_analyze_rejects_non_pdf():
    response = client.post(
        "/api/v1/orders/analyze",
        data=_form_data(),
        files={"thesis_pdf": ("file.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 422


def test_analyze_rejects_oversized_pdf():
    big_content = b"%PDF-" + b"x" * (31 * 1024 * 1024)
    response = client.post(
        "/api/v1/orders/analyze",
        data=_form_data(),
        files={"thesis_pdf": ("big.pdf", big_content, "application/pdf")},
    )
    assert response.status_code == 422
