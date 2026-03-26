from fastapi import APIRouter, status

from src.api.deps import HealthServiceDep
from src.core import settings

router = APIRouter()


@router.get("/", tags=["System"])
async def public_root() -> dict[str, str]:
    """Perform a basic system health check.

    Returns the current operational status, application name,
    and active deployment environment. Used by load balancers
    and monitoring tools to verify the API is alive.
    """
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "env": settings.ENVIRONMENT,
    }


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness_probe() -> dict[str, str]:
    """Execute a lightweight liveness check for the container orchestrator.

    Provides a fast, dependency-free endpoint to verify that the application's
    event loop is running and not deadlocked.

    Returns:
        dict[str, str]: A status dictionary indicating the process is alive.
    """
    return {"status": "ok"}


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_probe(health_service: HealthServiceDep) -> dict[str, str]:
    """Execute a comprehensive readiness check of critical infrastructure.

    Verifies active connections to essential dependencies. If this check fails,
    the instance is intentionally taken out of the service load balancer rotation.

    Args:
        health_service: Injected health service dependency.

    Returns:
        dict[str, str]: A status dictionary indicating the service is ready.
    """
    await health_service.check_readiness()
    return {"status": "ready"}
