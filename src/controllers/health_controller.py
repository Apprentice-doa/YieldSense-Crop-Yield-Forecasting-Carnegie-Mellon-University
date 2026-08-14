"""Health and API-bootstrap controller definitions."""

from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Expose a lightweight API health signal for platform readiness."""

    return {"status": "healthy"}
