"""Azure backend math problem solver.

OCR: Azure AI Document Intelligence (prebuilt-read + prebuilt-layout w/ FORMULAS)
LLM: Azure OpenAI (GPT-4o)

Inherits common logic (OCR scoring, prompt construction, etc.) from BaseMathSolver
and overrides only Azure-specific methods.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.models import SolveAnswer, SolveMeta, SolveRequest, SolveResponse
from app.services.base_math_solver import BaseMathSolver


@dataclass
class OcrResult:
    """Structured result from OCR pipeline, replacing the unwieldy 6-tuple."""

    text: str
    source: str
    score: float
    candidate_count: int
    top_candidates: list[dict] = field(default_factory=list)
    debug_texts: list[dict] = field(default_factory=list)


class AzureMathSolver(BaseMathSolver):
    """Azure DI + OpenAI を使った数学ソルバー。

    共通ロジック（スコアリング・プロンプト生成など）は BaseMathSolver から継承し、
    Azure 固有の OCR (Document Intelligence) と LLM (OpenAI) を実装する。
    """

    def __init__(self) -> None:
        self._sample_pdf_text_cache: dict[str, str] = {}
        self._di_client = self._build_di_client()
        self._openai_client = self._build_openai_client()

    # ------------------------------------------------------------------
    # クライアント初期化
    # ------------------------------------------------------------------

    def _build_di_client(self) -> Any:
        """Azure Document Intelligence クライアントを構築する。"""
        endpoint = settings.azure_document_intelligence_endpoint
        key = settings.azure_document_intelligence_key
        if not endpoint or not key:
            return None
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            return DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key),
            )
        except ImportError:
            return None

    def _build_openai_client(self) -> Any:
        """Azure OpenAI クライアントを構築する。"""
        endpoint = settings.azure_openai_endpoint
        key = settings.azure_openai_key
        if not endpoint or not key:
            return None
        try:
            from openai import AzureOpenAI

            return AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=key,
                api_version=settings.azure_openai_api_version,
            )
        except ImportError:
            return None

    # ------------------------------------------------------------------
    # solve() エントリポイント（AWS 版を Azure 用に再実装）
    # ------------------------------------------------------------------

    def solve(self, request: SolveRequest) -> SolveResponse:
        start = time.time()
        image_bytes = self._resolve_image(request)

        ocr = self._extract_text_with_azure_di(image_bytes, request)

        ocr_replacement_ratio, ocr_non_ascii_ratio = self._compute_ocr_quality_metrics(
            ocr.text
        )
        structured_problem = self._build_structured_problem(ocr.text, request)
        answer_payload = self._generate_with_openai(ocr.text, request, structured_problem)
        answer_payload["diagramGuide"] = self._resolve_diagram_guide(
            answer_payload, structured_problem
        )
        answer_payload["final"] = self._refine_final_text_for_geometry(
            str(answer_payload.get("final", "")), structured_problem
        )
        answer_payload["steps"] = self._refine_steps_for_geometry(
            answer_payload.get("steps", []),
            structured_problem,
            str(answer_payload.get("final", "")),
        )
        ocr_needs_review = self._should_flag_ocr_review(
            ocr.score, ocr_replacement_ratio, ocr.candidate_count
        )
        if ocr_needs_review:
            answer_payload = self._apply_ocr_review_warning(answer_payload)

        problem_type = str(structured_problem.get("problemType", "algebra"))
        answer_payload["confidence"] = self._calibrate_answer_confidence(
            raw_confidence=answer_payload.get("confidence", 0.5),
            ocr_score=ocr.score,
            replacement_ratio=ocr_replacement_ratio,
            ocr_source=ocr.source,
            problem_type=problem_type,
            ocr_needs_review=ocr_needs_review,
        )
        answer_payload = self._enforce_output_options(answer_payload, request)

        latency_ms = int((time.time() - start) * 1000)

        answer = SolveAnswer(
            final=answer_payload.get("final", ""),
            latex=answer_payload.get("latex"),
            steps=answer_payload.get("steps", []),
            diagramGuide=answer_payload.get("diagramGuide"),
            confidence=float(answer_payload.get("confidence", 0.5)),
        )

        return SolveResponse(
            requestId=f"req_{uuid.uuid4().hex[:16]}",
            status="completed",
            problemText=ocr.text,
            answer=answer,
            meta=SolveMeta(
                ocrProvider="azure_document_intelligence",
                ocrSource=ocr.source,
                ocrScore=ocr.score,
                ocrCandidates=ocr.candidate_count,
                ocrTopCandidates=ocr.top_candidates,
                ocrDebugTexts=ocr.debug_texts if request.options.debug_ocr else None,
                structuredProblem=structured_problem if request.options.debug_ocr else None,
                ocrReplacementRatio=ocr_replacement_ratio,
                ocrNonAsciiRatio=ocr_non_ascii_ratio,
                ocrNeedsReview=ocr_needs_review,
                model=f"azure_openai/{settings.azure_openai_deployment}",
                latencyMs=latency_ms,
                costUsd=0.0,
            ),
        )

    # ------------------------------------------------------------------
    # Azure Document Intelligence OCR
    # ------------------------------------------------------------------

    def _extract_text_with_azure_di(
        self,
        image_bytes: bytes,
        request: SolveRequest,
    ) -> OcrResult:
        """Run Azure DI OCR, score all candidates, return the best as OcrResult."""
        raw_candidates = self._call_azure_di(image_bytes)
        if not raw_candidates:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Azure Document Intelligence returned no OCR candidates. "
                    "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY."
                ),
            )

        scored: list[dict] = []
        for text, source in raw_candidates:
            cleaned = self._cleanup_ocr_text(text)
            if not cleaned:
                continue
            score = self._score_ocr_text(cleaned, source)
            scored.append({"text": cleaned, "source": source, "score": score})

        if not scored:
            raise HTTPException(
                status_code=422, detail="No readable text found in image"
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]

        self._dump_ocr_to_file(image_bytes, scored)

        return OcrResult(
            text=str(best["text"]),
            source=str(best["source"]),
            score=round(float(best["score"]), 4),
            candidate_count=len(scored),
            top_candidates=[
                {
                    "source": str(c["source"]),
                    "score": round(float(c["score"]), 4),
                    "textPreview": self._preview_text(str(c["text"])),
                }
                for c in scored[:3]
            ],
            debug_texts=[
                {
                    "source": str(c["source"]),
                    "score": round(float(c["score"]), 4),
                    "text": self._limit_debug_text(str(c["text"])),
                }
                for c in scored[:5]
            ],
        )

    # ------------------------------------------------------------------
    # OCR デバッグ出力
    # ------------------------------------------------------------------

    _OCR_DUMP_PATH = "/tmp/ocr_debug.jsonl"
    _OCR_BLOB_CONTAINER = "ocr-debug"
    _OCR_BLOB_NAME = "ocr_debug.jsonl"

    def _dump_ocr_to_file(self, image_bytes: bytes, scored: list[dict]) -> None:
        """OCR 結果を stdout・Blob Storage・/tmp ファイルに出力する（デバッグ用）。

        出力先:
          1. stdout          — Azure Functions ログで確認可能
          2. Blob Storage     — ocr-debug コンテナ / ocr_debug.jsonl (AppendBlob)
          3. /tmp (フォールバック) — ローカル実行時のみ有効
        形式: 1 行 = 1 リクエスト分の JSON オブジェクト (JSONL)
        """
        try:
            image_sha = hashlib.sha256(image_bytes).hexdigest()[:16]
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            record = {
                "ts": ts,
                "image_sha": image_sha,
                "candidates": [
                    {
                        "source": c["source"],
                        "score": round(float(c["score"]), 4),
                        "text": c["text"],
                    }
                    for c in scored
                ],
            }
            line = json.dumps(record, ensure_ascii=False)

            # --- stdout ---
            best = scored[0] if scored else {}
            print(
                f"[OCR] {ts} image={image_sha}"
                f" source={best.get('source', '?')}"
                f" score={round(float(best.get('score', 0)), 4)}"
                f" candidates={len(scored)}"
            )
            if scored:
                preview = best.get("text", "")[:200].replace("\n", "\\n")
                print(f"[OCR] text_preview: {preview}")

            # --- Blob Storage (AppendBlob) ---
            self._append_ocr_to_blob(line)

            # --- /tmp ファイル (ローカル用フォールバック) ---
            try:
                with open(self._OCR_DUMP_PATH, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception:
                pass

        except Exception as _exc:
            print(f"[OCR] WARN: 出力失敗: {_exc}")

    def _append_ocr_to_blob(self, line: str) -> None:
        """Append one JSONL line to the AppendBlob in Azure Blob Storage."""
        account = settings.azure_storage_account_name
        key = settings.azure_storage_account_key
        if not account or not key:
            print("[OCR] WARN: AZURE_STORAGE_ACCOUNT_NAME/KEY not set — Blob skipped")
            return
        try:
            from azure.core.exceptions import ResourceExistsError
            from azure.storage.blob import BlobServiceClient

            service = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=key,
            )
            container = service.get_container_client(self._OCR_BLOB_CONTAINER)
            try:
                container.create_container()
            except ResourceExistsError:
                pass

            blob = container.get_blob_client(self._OCR_BLOB_NAME)
            try:
                blob.create_append_blob()
            except ResourceExistsError:
                pass

            blob.append_block((line + "\n").encode("utf-8"))
            print(f"[OCR] Blob write OK: {self._OCR_BLOB_CONTAINER}/{self._OCR_BLOB_NAME}")
        except Exception as exc:
            print(f"[OCR] WARN: Blob write failed: {exc}")

    def _call_azure_di(self, image_bytes: bytes) -> list[tuple[str, str]]:
        """Run both Azure DI passes in parallel and return up to 4 (text, source) pairs.

        Candidates (in evaluation order):
          1. ``azure_di_read``           — prebuilt-read: preserves Japanese text verbatim
          2. ``azure_di_layout_markdown``— prebuilt-layout + FORMULAS + Markdown: accurate LaTeX
          3. ``azure_di_merged``         — positional merge: display formula lines replaced
                                           in-place with accurate LaTeX; Japanese text preserved
          4. ``azure_di_read+formulas``  — fallback: Japanese base + LaTeX appended at bottom,
                                           used when polygon data is unavailable for merging
        """
        if self._di_client is None:
            return []

        try:
            from azure.ai.documentintelligence.models import (
                AnalyzeDocumentRequest,
                DocumentAnalysisFeature,
                DocumentContentFormat,
            )
        except ImportError:
            return []

        # Run both DI passes in parallel to halve OCR latency.
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_read = pool.submit(
                self._ocr_read_pass, image_bytes, AnalyzeDocumentRequest
            )
            future_layout = pool.submit(
                self._ocr_layout_formulas_pass,
                image_bytes,
                AnalyzeDocumentRequest,
                DocumentAnalysisFeature,
                DocumentContentFormat,
            )
            read_text, read_lines = future_read.result()
            rich_formulas, latex_strings, markdown_text = future_layout.result()

        results: list[tuple[str, str]] = []
        if read_text:
            results.append((read_text, "azure_di_read"))
        if markdown_text:
            results.append((markdown_text, "azure_di_layout_markdown"))

        if read_lines and rich_formulas:
            # Preferred: positional merge — replace display formula lines with LaTeX in-place
            merged = self._merge_read_with_formulas(read_lines, rich_formulas)
            if merged:
                results.append((merged, "azure_di_merged"))
        elif read_text and latex_strings:
            # Fallback when polygon data is unavailable: append at bottom
            combined = (
                read_text
                + "\n\n[検出された数式 (LaTeX)]\n"
                + "\n".join(latex_strings)
            )
            results.append((combined, "azure_di_read+formulas"))

        return results

    def _ocr_read_pass(
        self, image_bytes: bytes, RequestModel: Any
    ) -> tuple[str, list[dict]]:
        """prebuilt-read pass.

        Returns ``(plain_text, rich_lines)`` where each element of ``rich_lines`` is
        ``{"content": str, "polygon": list[float] | None}``.
        The polygon is a flat list of page-unit coordinates [x0,y0,x1,y1,x2,y2,x3,y3].
        """
        try:
            result = self._di_client.begin_analyze_document(
                "prebuilt-read",
                RequestModel(bytes_source=image_bytes),
            ).result()
            rich_lines: list[dict] = []
            for page in (result.pages or []):
                for line in (page.lines or []):
                    raw_poly = getattr(line, "polygon", None)
                    # Normalize polygon: may be bytes, Point-list, float-list, or None
                    polygon: list | None = None
                    if raw_poly is not None and not isinstance(raw_poly, (bytes, bytearray)):
                        polygon = raw_poly
                    content = line.content
                    if isinstance(content, (bytes, bytearray)):
                        content = content.decode("utf-8", errors="replace")
                    rich_lines.append({"content": str(content), "polygon": polygon})
            return "\n".join(l["content"] for l in rich_lines), rich_lines
        except Exception:
            return "", []

    def _ocr_layout_formulas_pass(
        self,
        image_bytes: bytes,
        RequestModel: Any,
        AnalysisFeature: Any,
        ContentFormat: Any,
    ) -> tuple[list[dict], list[str], str]:
        """prebuilt-layout + FORMULAS + Markdown pass.

        Returns ``(rich_formulas, latex_strings, markdown_text)``.

        ``rich_formulas`` — list of dicts::

            {"value": str, "kind": "display"|"inline", "polygon": list[float] | None}

        ``latex_strings`` — ``["[display] ...", "[inline] ...", ...]`` (for legacy append).
        ``markdown_text`` — full Markdown content with formula list appended.
        """
        try:
            result = self._di_client.begin_analyze_document(
                "prebuilt-layout",
                RequestModel(bytes_source=image_bytes),
                features=[AnalysisFeature.FORMULAS],
                output_content_format=ContentFormat.MARKDOWN,
            ).result()

            parts: list[str] = []
            if result.content:
                parts.append(result.content)

            rich_formulas: list[dict] = []
            latex_strings: list[str] = []
            for page in (result.pages or []):
                for f in getattr(page, "formulas", None) or []:
                    val = getattr(f, "value", None)
                    if isinstance(val, (bytes, bytearray)):
                        val = val.decode("utf-8", errors="replace")
                    conf = getattr(f, "confidence", 1.0) or 1.0
                    kind = getattr(f, "kind", "") or ""
                    if isinstance(kind, (bytes, bytearray)):
                        kind = kind.decode("utf-8", errors="replace")
                    if not val or conf < 0.5:
                        continue
                    # Polygon lives inside bounding_regions[0].polygon
                    polygon: list | None = None
                    brs = getattr(f, "bounding_regions", None)
                    if brs:
                        raw_poly = getattr(brs[0], "polygon", None)
                        if raw_poly is not None and not isinstance(raw_poly, (bytes, bytearray)):
                            polygon = raw_poly
                    rich_formulas.append({"value": val, "kind": kind, "polygon": polygon})
                    tag = "display" if kind == "display" else "inline"
                    latex_strings.append(f"[{tag}] {val}")

            if latex_strings:
                parts.append("\n[検出された数式 (LaTeX)]\n" + "\n".join(latex_strings))

            markdown_text = "\n".join(parts).strip()
            return rich_formulas, latex_strings, (markdown_text if len(markdown_text) > 20 else "")
        except Exception:
            return [], [], ""

    # ------------------------------------------------------------------
    # Positional OCR merge helpers → BaseMathSolver に共通化済み
    # (_poly_y_range, _y_overlap_ratio, _is_formula_candidate,
    #  _has_formula_signal, _find_formula_regions, _merge_read_with_formulas)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Azure OpenAI 解答生成
    # ------------------------------------------------------------------

    def _generate_with_openai(
        self,
        problem_text: str,
        request: SolveRequest,
        structured_problem: dict[str, object] | None = None,
    ) -> dict:
        """Azure OpenAI GPT-4o で解答を生成する。

        クライアント未設定の場合は親クラスの Bedrock 実装にフォールバック。
        """
        if self._openai_client is None:
            # Azure 環境では Bedrock は利用不可。設定不備として 502 を返す。
            raise HTTPException(
                status_code=502,
                detail=(
                    "Azure OpenAI client is not configured. "
                    "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY environment variables."
                ),
            )

        prompt = self._build_prompt(problem_text, request, structured_problem)

        # accurate モード: 推論モデル（o3-mini 等）に切り替え
        is_accurate = request.options.mode == "accurate"
        accurate_deployment = settings.azure_openai_accurate_deployment
        deployment = accurate_deployment if (is_accurate and bool(accurate_deployment)) else settings.azure_openai_deployment

        # o3-mini/o1 系は temperature・response_format 非対応
        _REASONING_PREFIXES = ("o1", "o3")
        is_reasoning_model = any(deployment.lower().startswith(p) for p in _REASONING_PREFIXES)

        # accurate + 非推論モデル: scratchpad 2段階呼び出し
        use_scratchpad = is_accurate and not is_reasoning_model

        try:
            if use_scratchpad:
                # Stage 1: 計算過程を自由展開
                stage1_prompt = self._build_scratchpad_prompt(
                    problem_text, request, structured_problem
                )
                stage1_resp = self._openai_client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": "あなたは大学入試数学の専門家です。計算を省略せず厳密に解いてください。",
                        },
                        {"role": "user", "content": stage1_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=8192,
                )
                scratchpad = stage1_resp.choices[0].message.content or ""

                # Stage 2: JSON 抽出
                stage2_prompt = self._build_json_extraction_prompt(scratchpad, request)
                response = self._openai_client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": "あなたは JSON フォーマッターです。出力は JSON オブジェクトのみで返してください。",
                        },
                        {"role": "user", "content": stage2_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
            else:
                # 1段階: 推論モデルまたは fast モード
                _token_limit = min(
                    max(request.options.max_tokens, 512),
                    8192 if is_accurate else 2000,
                )
                _token_key = "max_completion_tokens" if is_reasoning_model else "max_tokens"
                create_kwargs: dict = dict(
                    model=deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "あなたは大学入試数学の解答アシスタントです。"
                                "出力は必ず JSON オブジェクトのみで返してください。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    **{_token_key: _token_limit},
                )
                if is_reasoning_model:
                    create_kwargs["temperature"] = 1
                    create_kwargs["extra_body"] = {"reasoning_effort": "medium"}
                else:
                    create_kwargs["temperature"] = 0.0
                    create_kwargs["response_format"] = {"type": "json_object"}
                response = self._openai_client.chat.completions.create(**create_kwargs)

        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Azure OpenAI invocation failed: {exc}",
            ) from exc

        text = response.choices[0].message.content or ""
        parsed = self._parse_json_answer(text)
        if parsed is None:
            parsed = {
                "final": text.strip()[:2000] or "解答を生成できませんでした。",
                "latex": None,
                "steps": [],
                "confidence": 0.3,
            }
        return self._normalize_answer_payload(parsed)
