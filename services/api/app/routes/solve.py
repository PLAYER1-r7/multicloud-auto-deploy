from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    CloudProvider,
    SolveRequest,
    SolveResponse,
)
from app.services.azure_math_solver import AzureMathSolver
from app.services.base_math_solver import BaseMathSolver
from app.services.gcp_math_solver import GcpMathSolver

router = APIRouter(prefix="/v1", tags=["solve"])

_DISABLED_RESPONSE = {
    "status_code": 503,
    "detail": "solve endpoints are currently disabled (SOLVE_ENABLED=false)",
}


def _check_enabled() -> None:
    """SOLVE_ENABLED=false のとき 503 を返す。"""
    if not settings.solve_enabled:
        raise HTTPException(**_DISABLED_RESPONSE)


def _get_solver() -> BaseMathSolver:
    """クラウドプロバイダーに応じたソルバーを返す。Azure と GCP のみサポート。"""
    if settings.cloud_provider == CloudProvider.AZURE:
        return AzureMathSolver()
    if settings.cloud_provider == CloudProvider.GCP:
        return GcpMathSolver()
    raise HTTPException(
        status_code=501,
        detail="/v1/solve is available on Azure and GCP only. AWS implementation has been removed.",
    )


@router.post("/solve", response_model=SolveResponse)
def solve_math(request: SolveRequest) -> SolveResponse:
    _check_enabled()
    solver = _get_solver()
    return solver.solve(request)


# ------------------------------------------------------------------ #
# OCR デバッグログ取得                                                  #
# ------------------------------------------------------------------ #

_OCR_DEBUG_PATH = "/tmp/ocr_debug.jsonl"
_OCR_BLOB_CONTAINER = "ocr-debug"
_OCR_BLOB_NAME = "ocr_debug.jsonl"


def _read_ocr_lines_from_blob() -> list[str]:
    """Blob Storage から JSONL 行リストを返す。失敗時は空リスト。"""
    account = settings.azure_storage_account_name
    key = settings.azure_storage_account_key
    if not account or not key:
        return []
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.core.exceptions import ResourceNotFoundError

        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=key,
        )
        blob = service.get_blob_client(
            container=_OCR_BLOB_CONTAINER, blob=_OCR_BLOB_NAME
        )
        content = blob.download_blob().readall().decode("utf-8")
        return [l for l in content.splitlines() if l.strip()]
    except Exception:
        return []


@router.get("/ocr-debug")
def get_ocr_debug(limit: int = 20) -> JSONResponse:
    """OCR デバッグログ (Blob Storage: ocr-debug/ocr_debug.jsonl) の末尾 N 件を返す。

    limit: 返す最大行数（デフォルト 20）
    """
    import json as _json
    import os

    # Blob Storage から読む（全インスタンス共通）
    lines = _read_ocr_lines_from_blob()

    # フォールバック: /tmp ファイル（コンテナを跨いど山輪ではブランク）
    source = "blob"
    if not lines:
        if os.path.exists(_OCR_DEBUG_PATH):
            try:
                with open(_OCR_DEBUG_PATH, encoding="utf-8") as fh:
                    lines = [l for l in fh.read().splitlines() if l.strip()]
                source = "tmp_file"
            except Exception:
                pass

    if not lines:
        return JSONResponse(
            {"entries": [], "total": 0, "source": source,
             "message": "まだログがありません。/v1/solve を実行すると追記されます。"}
        )

    tail = lines[-limit:]
    entries = []
    for line in tail:
        try:
            entries.append(_json.loads(line))
        except Exception:
            entries.append({"raw": line})

    return JSONResponse({"entries": entries, "total": len(lines), "source": source})


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

    # Blob Storage 書き込みテスト
    try:
        from azure.storage.blob import BlobServiceClient

        account = settings.azure_storage_account_name
        key = settings.azure_storage_account_key
        if account and key:
            service = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=key,
            )
            container = service.get_container_client(_OCR_BLOB_CONTAINER)
            try:
                container.create_container()
            except Exception:
                pass
            blob = container.get_blob_client(_OCR_BLOB_NAME)
            try:
                blob.create_append_blob()
            except Exception:
                pass
            blob.append_block(b"[diag]\n")
            results["blob_write"] = f"ok ({account}/{_OCR_BLOB_CONTAINER}/{_OCR_BLOB_NAME})"
        else:
            results["blob_write"] = "skip: AZURE_STORAGE_ACCOUNT_NAME/KEY 未設定"
    except Exception as e:
        results["blob_write"] = f"error: {e}"

    # /tmp ファイル一覧
    try:
        results["tmp_listdir"] = os.listdir("/tmp")
    except Exception as e:
        results["tmp_listdir"] = f"error: {e}"

    return JSONResponse(results)
