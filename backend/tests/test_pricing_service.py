import pytest
from app.services.pricing_service import calculate_pricing


def test_fyp_cv_utp_delivery_no_fasttrack():
    # PRD §13.4 sample: 128 pages, 121 BW + 7 color, UTP delivery, no fast track
    pricing = calculate_pricing(
        project_type="FYP",
        course_code="CV",
        num_hardbound=1,
        num_cd=0,
        bw_pages=121,
        color_pages=7,
        delivery_option="UTP_DELIVERY",
        fast_track=False,
    )
    assert pricing.cover_price == 36.00
    assert pricing.bw_print_price == pytest.approx(12.10, abs=0.005)
    assert pricing.color_print_price == pytest.approx(2.10, abs=0.005)
    assert pricing.cd_price == 0.00
    assert pricing.delivery_price == 5.00
    assert pricing.fast_track_price == 0.00
    assert pricing.grand_total == pytest.approx(55.20, abs=0.005)


def test_postgrad_self_pickup_fast_track():
    pricing = calculate_pricing(
        project_type="POSTGRAD",
        course_code="OTHER",
        num_hardbound=2,
        num_cd=1,
        bw_pages=50,
        color_pages=10,
        delivery_option="SELF_PICKUP",
        fast_track=True,
    )
    # cover: 38 * 2 = 76
    # bw: 50 * 0.10 = 5
    # color: 10 * 0.30 = 3
    # cd: 4 * 1 = 4
    # delivery: 0
    # fast track: 10
    # total: 76 + 5 + 3 + 4 + 0 + 10 = 98
    assert pricing.cover_price == 76.00
    assert pricing.grand_total == pytest.approx(98.00, abs=0.005)


def test_fyp_other_falls_back_to_36():
    pricing = calculate_pricing(
        project_type="FYP",
        course_code="OTHER",
        num_hardbound=1,
        num_cd=0,
        bw_pages=0,
        color_pages=0,
        delivery_option="SELF_PICKUP",
        fast_track=False,
    )
    assert pricing.cover_price == 36.00
