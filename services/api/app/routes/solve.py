from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

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


# ------------------------------------------------------------------ #
# OCR デバッグログ取得                                                  #
# ------------------------------------------------------------------ #

_OCR_DEBUG_PATH = "/tmp/ocr_debug.jsonl"


@router.get("/ocr-debug")
def get_ocr_debug(limit: int = 20) -> JSONResponse:
    """OCR デバッグログ（/tmp/ocr_debug.jsonl）の末尾 N 件を返す。

    limit: 返す最大行数（デフォルト 20）
    """
    import json as _json
    import os

    if not os.path.exists(_OCR_DEBUG_PATH):
        return JSONResponse(
            {"entries": [], "total": 0, "message": "ログファイルが存在しません"}
        )

    try:
        with open(_OCR_DEBUG_PATH, encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"ログ読み取りエラー: {exc}")

    tail = lines[-limit:]
    entries = []
    for line in tail:
        try:
            entries.append(_json.loads(line))
        except Exception:
            entries.append({"raw": line})

    return JSONResponse({"entries": entries, "total": len(lines)})


@router.get("/ocr-debug/diag")
def get_ocr_debug_diag() -> JSONResponse:
    """/tmp への書き込み・stdout の動作を診断する。"""
    import os

    results: dict = {}

    # stdout テスト
    try:
        print("[OCR-DIAG] stdout test from /v1/ocr-debug/diag", flush=True)
        results["stdout"] = "ok"
    except Exception as e:
        results["stdout"] = f"error: {e}"

    # /tmp 書き込みテスト
    test_path = "/tmp/_diag_test.txt"
    try:
        with open(test_path, "w") as fh:
            fh.write("diag\n")
        results["tmp_write"] = "ok"
    except Exception as e:
        results["tmp_write"] = f"error: {e}"

    # ocr_debug.jsonl 状態
    try:
        exists = os.path.exists(_OCR_DEBUG_PATH)
        size = os.path.getsize(_OCR_DEBUG_PATH) if exists else -1
        results["ocr_debug_jsonl"] = {"exists": exists, "size_bytes": size}
    except Exception as e:
        results["ocr_debug_jsonl"] = f"error: {e}"

    # /tmp ファイル一覧
    try:
        results["tmp_listdir"] = os.listdir("/tmp")
    except Exception as e:
        results["tmp_listdir"] = f"error: {e}"

    return JSONResponse(results)
