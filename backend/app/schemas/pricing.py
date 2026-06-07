from pydantic import BaseModel


class DeliveryPricing(BaseModel):
    SELF_PICKUP: float
    UTP_DELIVERY: float
    POSTAGE_SEMENANJUNG: float
    POSTAGE_SABAH_SARAWAK: float
    POSTAGE_INTERNATIONAL: float


class FYPPricing(BaseModel):
    CV: float
    CE: float
    ME: float
    EE: float
    ComE: float
    MAT: float
    PE: float
    AC: float


class PostgradPricing(BaseModel):
    DEFAULT: float


class PricingConfig(BaseModel):
    FYP: FYPPricing
    POSTGRAD: PostgradPricing
    BW_PER_PAGE: float
    COLOR_PER_PAGE: float
    CD_PRICE: float
    DELIVERY: DeliveryPricing
    FAST_TRACK_ADDON: float


PRICING: dict = {
    "FYP": {
        "CV": 36.00,
        "CE": 36.00,
        "ME": 36.00,
        "EE": 36.00,
        "ComE": 36.00,
        "MAT": 36.00,
        "PE": 36.00,
        "AC": 36.00,
    },
    "POSTGRAD": {
        "DEFAULT": 38.00,
    },
    "BW_PER_PAGE": 0.10,
    "COLOR_PER_PAGE": 0.30,
    "CD_PRICE": 4.00,
    "DELIVERY": {
        "SELF_PICKUP": 0.00,
        "UTP_DELIVERY": 5.00,
        "POSTAGE_SEMENANJUNG": 10.00,
        "POSTAGE_SABAH_SARAWAK": 35.00,
        "POSTAGE_INTERNATIONAL": 100.00,
    },
    "FAST_TRACK_ADDON": 10.00,
}
