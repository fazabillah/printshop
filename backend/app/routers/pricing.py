from fastapi import APIRouter

from app.schemas.pricing import PRICING, PricingConfig

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])


@router.get("/config", response_model=PricingConfig)
def get_pricing_config():
    return PRICING
