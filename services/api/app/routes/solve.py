from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import CloudProvider, SolveRequest, SolveResponse
from app.services.aws_math_solver import AwsMathSolver

router = APIRouter(prefix="/v1", tags=["solve"])


@router.post("/solve", response_model=SolveResponse)
def solve_math(request: SolveRequest) -> SolveResponse:
    if settings.cloud_provider != CloudProvider.AWS:
        raise HTTPException(
            status_code=501,
            detail="/v1/solve is implemented only for AWS in this version",
        )

    solver = AwsMathSolver()
    return solver.solve(request)
