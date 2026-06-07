import logging
import fitz  # PyMuPDF

from app.schemas.order import PageCounts

logger = logging.getLogger(__name__)

# A pixel is considered non-grayscale if any two channels differ by more than this.
COLOR_DIFF_THRESHOLD = 10
# A page is COLOR if non-grayscale pixels exceed this fraction of total pixels.
# TODO: revisit with numpy if page-scan latency exceeds NF03 (15s) for large PDFs.
COLOR_PIXEL_RATIO = 0.005


def classify_pages(pdf_path: str) -> PageCounts:
    doc = fitz.open(pdf_path)
    total = len(doc)
    color_page_numbers: list[int] = []

    for page_idx, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        n = pix.n  # bytes per pixel (3 = RGB, 4 = RGBA)
        samples = pix.samples
        pixel_count = pix.width * pix.height
        non_gray = 0

        for i in range(0, len(samples), n):
            r = samples[i]
            g = samples[i + 1]
            b = samples[i + 2]
            if abs(r - g) > COLOR_DIFF_THRESHOLD or abs(g - b) > COLOR_DIFF_THRESHOLD or abs(r - b) > COLOR_DIFF_THRESHOLD:
                non_gray += 1

        if pixel_count > 0 and non_gray / pixel_count > COLOR_PIXEL_RATIO:
            color_page_numbers.append(page_idx + 1)  # 1-indexed for display

    doc.close()
    color_count = len(color_page_numbers)
    bw_count = total - color_count
    logger.info("classify_pages: total=%d bw=%d color=%d color_pages=%s file=%s",
                total, bw_count, color_count, color_page_numbers, pdf_path)
    return PageCounts(
        total_pages=total,
        bw_pages=bw_count,
        color_pages=color_count,
        color_page_numbers=color_page_numbers,
    )
