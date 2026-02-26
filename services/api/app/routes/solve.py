from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import (
    CloudProvider,
    SolveJobCreateResponse,
    SolveJobStatusResponse,
    SolveRequest,
    SolveResponse,
)
from app.services.aws_math_solver import AwsMathSolver
from app.services.azure_math_solver import AzureMathSolver
from app.services.gcp_math_solver import GcpMathSolver
from app.services.solve_job_service import SolveJobService

router = APIRouter(prefix="/v1", tags=["solve"])

_DISABLED_RESPONSE = {
    "status_code": 503,
    "detail": "solve endpoints are currently disabled (SOLVE_ENABLED=false)",
}


def _check_enabled() -> None:
    """SOLVE_ENABLED=false のとき 503 を返す。"""
    if not settings.solve_enabled:
        raise HTTPException(**_DISABLED_RESPONSE)


def _get_solver() -> AwsMathSolver:
    """クラウドプロバイダーに応じたソルバーを返す。"""
    if settings.cloud_provider == CloudProvider.AZURE:
        return AzureMathSolver()
    if settings.cloud_provider == CloudProvider.GCP:
        return GcpMathSolver()
    return AwsMathSolver()


@router.post("/solve", response_model=SolveResponse)
def solve_math(request: SolveRequest) -> SolveResponse:
    _check_enabled()
    if settings.cloud_provider not in (
        CloudProvider.AWS,
        CloudProvider.AZURE,
        CloudProvider.GCP,
    ):
        raise HTTPException(
            status_code=501,
            detail="/v1/solve is implemented only for AWS, Azure, and GCP in this version",
        )

    solver = _get_solver()
    return solver.solve(request)


@router.post("/solve-jobs", response_model=SolveJobCreateResponse)
def create_solve_job(request: SolveRequest) -> SolveJobCreateResponse:
    _check_enabled()
    if settings.cloud_provider != CloudProvider.AWS:
        raise HTTPException(
            status_code=501,
            detail="/v1/solve-jobs is implemented only for AWS in this version",
        )

    try:
        service = SolveJobService()
        payload = service.create_job(request)
        return SolveJobCreateResponse.model_validate(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to create solve job: {exc}"
        )


@router.get("/solve-jobs/{job_id}", response_model=SolveJobStatusResponse)
def get_solve_job(job_id: str) -> SolveJobStatusResponse:
    _check_enabled()
    if settings.cloud_provider != CloudProvider.AWS:
        raise HTTPException(
            status_code=501,
            detail="/v1/solve-jobs is implemented only for AWS in this version",
        )

    try:
        service = SolveJobService()
        payload = service.get_job(job_id)
        return SolveJobStatusResponse.model_validate(payload)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="job not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to get solve job: {exc}")
