"""The health endpoint Cloud Run and the deploy check probe."""

from fastapi import APIRouter
from pydantic import BaseModel

from core.config import Settings


class HealthStatus(BaseModel):
    """What `/healthz` answers: which service is running, and which build of it."""

    service: str
    version: str


def create_health_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["ops"])

    @router.get("/healthz")
    async def healthz() -> HealthStatus:
        return HealthStatus(service=settings.service_name, version=settings.app_version)

    return router
