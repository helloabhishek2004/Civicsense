from fastapi import APIRouter

from app.api.v1.routes import health, reports

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(reports.router)

__all__ = ["api_v1_router"]
