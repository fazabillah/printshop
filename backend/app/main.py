from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import orders, pricing

app = FastAPI(title="PrintShop Hardbound API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.app_env == "development" else ["https://printshop.internal"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders.router)
app.include_router(pricing.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
