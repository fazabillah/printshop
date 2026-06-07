from app.schemas.order import PricingBreakdown
from app.schemas.pricing import PRICING


def calculate_pricing(
    project_type: str,
    course_code: str,
    num_hardbound: int,
    num_cd: int,
    bw_pages: int,
    color_pages: int,
    delivery_option: str,
    fast_track: bool,
) -> PricingBreakdown:
    if project_type == "POSTGRAD":
        cover_unit = PRICING["POSTGRAD"]["DEFAULT"]
    else:
        cover_unit = PRICING["FYP"].get(course_code, 36.00)

    cover_price = round(cover_unit * num_hardbound, 2)
    bw_print_price = round(bw_pages * PRICING["BW_PER_PAGE"], 2)
    color_print_price = round(color_pages * PRICING["COLOR_PER_PAGE"], 2)
    cd_price = round(PRICING["CD_PRICE"] * num_cd, 2)
    delivery_price = PRICING["DELIVERY"].get(delivery_option, 0.00)
    fast_track_price = PRICING["FAST_TRACK_ADDON"] if fast_track else 0.00
    grand_total = round(
        cover_price + bw_print_price + color_print_price + cd_price + delivery_price + fast_track_price,
        2,
    )

    return PricingBreakdown(
        cover_price=cover_price,
        bw_print_price=bw_print_price,
        color_print_price=color_print_price,
        cd_price=cd_price,
        delivery_price=delivery_price,
        fast_track_price=fast_track_price,
        grand_total=grand_total,
    )
