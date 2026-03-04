"""OCR・数学解答エンドポイント (T12)

大学入試問題の画像から AI による解答を生成します。
"""

import base64
import json
import logging
import time
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["solve"])


class SolveInput(BaseModel):
    """入力画像情報"""

    imageUrl: str | None = Field(None, description="問題画像の公開URL")
    imageBase64: str | None = Field(None, description="base64エンコード済み画像")
    source: str = Field("paste", description="入力元ヒント (url|paste|upload)")


class SolveExam(BaseModel):
    """試験情報"""

    university: str = Field("tokyo", description="大学コード")
    year: int | None = Field(None, description="年度")
    subject: str = Field("math", description="科目コード")
    questionNo: str | None = Field(None, description="問題番号")


class SolveOptions(BaseModel):
    """解答オプション"""

    mode: str = Field("fast", description="OCR戦略 (fast|accurate)")
    needSteps: bool = Field(True, description="段階的解法を含める")
    needLatex: bool = Field(True, description="LaTeXを含める")
    maxTokens: int = Field(2000, description="LLM最大トークン数")
    debugOcr: bool = Field(False, description="OCR候補を含める")


class SolveRequest(BaseModel):
    """POST /v1/solve リクエスト"""

    input: SolveInput
    exam: SolveExam
    options: SolveOptions = Field(default_factory=SolveOptions)


class SolveAnswer(BaseModel):
    """解答情報"""

    final: str = Field(description="最終答")
    steps: list[str] = Field(default_factory=list, description="段階的解法")
    latex: str | None = Field(None, description="LaTeX形式")


class SolveMeta(BaseModel):
    """メタデータ"""

    ocrEngine: str = Field(description="使用したOCRエンジン")
    processingTimeMs: int = Field(description="処理時間 (ms)")
    ocrDebugTexts: list[str] | None = Field(None, description="デバッグ用OCR候補")


class SolveResponse(BaseModel):
    """POST /v1/solve レスポンス"""

    problemText: str = Field(description="抽出された問題テキスト")
    answer: SolveAnswer = Field(description="解答情報")
    meta: SolveMeta = Field(description="メタデータ")


def _ensure_solve_available() -> None:
    if not getattr(settings, "solve_enabled", False):
        raise HTTPException(
            status_code=503,
            detail="solve endpoints are currently disabled (SOLVE_ENABLED=false)",
        )


def _ensure_input_present(request: SolveRequest) -> None:
    if not request.input.imageUrl and not request.input.imageBase64:
        raise HTTPException(
            status_code=400,
            detail="Either imageUrl or imageBase64 must be provided",
        )


def _require_azure_solver_config() -> None:
    missing = []
    if not settings.azure_document_intelligence_endpoint:
        missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    if not settings.azure_document_intelligence_key:
        missing.append("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    if not settings.azure_openai_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not settings.azure_openai_key:
        missing.append("AZURE_OPENAI_KEY")

    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"solve endpoint is not configured: missing {', '.join(missing)}",
        )


def _normalize_base64(data: str) -> str:
    if "," in data and data.strip().lower().startswith("data:"):
        return data.split(",", 1)[1]
    return data


def _poll_document_intelligence(operation_url: str, key: str) -> dict[str, Any]:
    headers = {"Ocp-Apim-Subscription-Key": key}
    timeout_seconds = 45
    start = time.time()

    while True:
        response = requests.get(operation_url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        status = str(payload.get("status", "")).lower()

        if status == "succeeded":
            return payload
        if status in {"failed", "error"}:
            raise HTTPException(status_code=502, detail="OCR analysis failed")

        if time.time() - start > timeout_seconds:
            raise HTTPException(status_code=504, detail="OCR analysis timed out")

        time.sleep(1.0)


def _run_azure_ocr(request: SolveRequest) -> str:
    endpoint = settings.azure_document_intelligence_endpoint.rstrip("/")
    url = (
        f"{endpoint}/documentintelligence/documentModels/prebuilt-read:analyze"
        "?api-version=2024-02-29-preview"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_document_intelligence_key,
        "Content-Type": "application/json",
    }

    if request.input.imageUrl:
        body = {"urlSource": request.input.imageUrl}
    else:
        try:
            normalized = _normalize_base64(request.input.imageBase64 or "")
            base64.b64decode(normalized, validate=True)
            body = {"base64Source": normalized}
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail="imageBase64 is invalid"
            ) from exc

    analyze_response = requests.post(url, headers=headers, json=body, timeout=30)
    if analyze_response.status_code not in (200, 202):
        logger.error("Azure OCR analyze failed: %s", analyze_response.text[:500])
        raise HTTPException(status_code=502, detail="Failed to start OCR analysis")

    if analyze_response.status_code == 200:
        result_payload = analyze_response.json()
    else:
        operation_url = analyze_response.headers.get("operation-location")
        if not operation_url:
            raise HTTPException(
                status_code=502, detail="OCR operation-location missing"
            )
        result_payload = _poll_document_intelligence(
            operation_url, settings.azure_document_intelligence_key
        )

    content = (
        result_payload.get("analyzeResult", {}).get("content")
        or result_payload.get("content")
        or ""
    )
    if not content.strip():
        raise HTTPException(status_code=422, detail="OCR result is empty")

    return content


def _parse_llm_json(text: str) -> tuple[str, list[str], str | None]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text.strip(), [], None

    final_answer = str(payload.get("final") or payload.get("answer") or "").strip()
    steps_raw = payload.get("steps") or []
    if isinstance(steps_raw, list):
        steps = [str(step).strip() for step in steps_raw if str(step).strip()]
    else:
        steps = []

    latex_value = payload.get("latex")
    latex = str(latex_value).strip() if latex_value is not None else None

    if not final_answer:
        final_answer = text.strip()

    return final_answer, steps, latex


def _run_azure_openai(
    problem_text: str, options: SolveOptions
) -> tuple[str, list[str], str | None]:
    endpoint = settings.azure_openai_endpoint.rstrip("/")
    deployment = settings.azure_openai_deployment
    api_version = settings.azure_openai_api_version
    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    headers = {
        "api-key": settings.azure_openai_key,
        "Content-Type": "application/json",
    }

    system_prompt = (
        "あなたは大学入試数学の解答アシスタントです。"
        "必ずJSONのみで返し、キーは final, steps, latex を使ってください。"
        "steps は文字列配列、latex は文字列または null とします。"
    )
    user_prompt = (
        "以下の問題を解いてください。"
        "needSteps/needLatex を考慮し、不要な項目は空で返してください。\n\n"
        f"Problem:\n{problem_text}\n\n"
        f"needSteps={options.needSteps}, needLatex={options.needLatex}"
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": int(options.maxTokens),
        "response_format": {"type": "json_object"},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code >= 400:
        logger.error("Azure OpenAI failed: %s", response.text[:500])
        raise HTTPException(status_code=502, detail="Failed to generate answer")

    result = response.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not str(content).strip():
        raise HTTPException(status_code=502, detail="LLM returned empty response")

    final_answer, steps, latex = _parse_llm_json(str(content))

    if not options.needSteps:
        steps = []
    if not options.needLatex:
        latex = None

    return final_answer, steps, latex


def _solve_with_azure(request: SolveRequest) -> SolveResponse:
    started = time.time()

    problem_text = _run_azure_ocr(request)
    final_answer, steps, latex = _run_azure_openai(problem_text, request.options)

    elapsed_ms = int((time.time() - started) * 1000)

    return SolveResponse(
        problemText=problem_text,
        answer=SolveAnswer(
            final=final_answer,
            steps=steps,
            latex=latex,
        ),
        meta=SolveMeta(
            ocrEngine="azure-di-prebuilt-read",
            processingTimeMs=elapsed_ms,
            ocrDebugTexts=[problem_text] if request.options.debugOcr else None,
        ),
    )


@router.post(
    "/solve",
    response_model=SolveResponse,
    summary="数学問題を解く",
    description="大学入試問題の画像から AI が解答を生成します。",
)
async def solve(request: SolveRequest) -> SolveResponse:
    """
    POST /v1/solve — 画像から数学問題を解く

    **機能**:
    - 問題画像（URL または base64）から OCR で問題テキストを抽出
    - LLM で段階的な解法を生成
    - LaTeX 形式の数式を含める

    **コスト制御**:
    - `SOLVE_ENABLED=false` (デフォルト) でこのエンドポイントは無効

    **エラー**:
    - 503: `SOLVE_ENABLED=false` の場合
    - 400: リクエスト形式が不正な場合
    """

    _ensure_solve_available()
    _ensure_input_present(request)
    _require_azure_solver_config()

    logger.info(
        f"Solve request: university={request.exam.university}, "
        f"year={request.exam.year}, question={request.exam.questionNo}"
    )
    return _solve_with_azure(request)


@router.post(
    "/solve/stream",
    summary="数学問題を解く (ストリーミング)",
    description="大学入試問題の画像から AI が段階的に解答を生成します (JSON Lines)。",
)
def solve_stream(request: SolveRequest):
    """
    POST /v1/solve/stream — 画像から数学問題を解く (ストリーミング)

    Server-Sent Events (SSE) を使用してリアルタイムで解答を配信。

    **エラー**:
    - 503: `SOLVE_ENABLED=false` の場合
    """

    _ensure_solve_available()
    _ensure_input_present(request)
    _require_azure_solver_config()

    logger.info("Solve stream request")

    solved = _solve_with_azure(request)

    result_payload = {
        "problemText": solved.problemText,
        "answer": {
            "final": solved.answer.final,
            "steps": solved.answer.steps,
            "latex": solved.answer.latex,
        },
        "meta": {
            "ocrEngine": solved.meta.ocrEngine,
            "processingTimeMs": solved.meta.processingTimeMs,
            "ocrDebugTexts": solved.meta.ocrDebugTexts,
        },
    }

    preview_text = solved.problemText.replace("\n", " ")[:120]

    events = [
        {"type": "ocr", "payload": {"status": "processing", "progress": 0}},
        {"type": "ocr", "payload": {"status": "done", "text": preview_text}},
        {"type": "llm", "payload": {"status": "generating"}},
        *[{"type": "step", "payload": {"text": step}} for step in solved.answer.steps],
        {"type": "result", "payload": result_payload},
    ]

    sse_body = "".join(
        f"data: {json.dumps(event, ensure_ascii=False)}\n\n" for event in events
    )

    return Response(
        content=sse_body,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
