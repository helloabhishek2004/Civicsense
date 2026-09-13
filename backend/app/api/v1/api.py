from fastapi import APIRouter

from app.api.v1.routes import ai, departments, health, issues, matches, reports

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(departments.router)
api_v1_router.include_router(ai.router)
api_v1_router.include_router(matches.router)
api_v1_router.include_router(issues.router)

__all__ = ["api_v1_router"]
