import os
import pytest
from app.services.pdf_analysis_service import classify_pages

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", ".planning", "client-sample"
)

INFO_PAGE_PDF = os.path.join(FIXTURES_DIR, "Info-Page-Sample.pdf")
JAFNI_PDF = os.path.join(
    FIXTURES_DIR,
    "Final Year Project - Dissertation_Jafni Syazani bin Mohd Nazrin (21000201) - updated - JAFNI. SYZN.pdf",
)


@pytest.mark.parametrize("pdf_path", [INFO_PAGE_PDF, JAFNI_PDF])
def test_classify_pages_counts_add_up(pdf_path):
    if not os.path.exists(pdf_path):
        pytest.skip(f"fixture not found: {pdf_path}")
    result = classify_pages(pdf_path)
    assert result.total_pages > 0
    assert result.bw_pages + result.color_pages == result.total_pages
    assert result.bw_pages >= 0
    assert result.color_pages >= 0


@pytest.mark.parametrize("pdf_path", [INFO_PAGE_PDF, JAFNI_PDF])
def test_color_page_numbers_consistent(pdf_path):
    if not os.path.exists(pdf_path):
        pytest.skip(f"fixture not found: {pdf_path}")
    result = classify_pages(pdf_path)
    nums = result.color_page_numbers
    # count matches list length
    assert len(nums) == result.color_pages
    # all page numbers are within valid range, sorted ascending, no duplicates
    assert nums == sorted(nums)
    assert len(nums) == len(set(nums))
    for n in nums:
        assert 1 <= n <= result.total_pages
