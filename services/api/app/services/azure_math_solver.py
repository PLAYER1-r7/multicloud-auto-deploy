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
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        """Run both Azure DI passes in parallel and return up to 3 (text, source) pairs.

        Candidates:
          1. ``azure_di_read``           — prebuilt-read: preserves Japanese text
          2. ``azure_di_layout_markdown``— prebuilt-layout + FORMULAS + Markdown: accurate LaTeX
          3. ``azure_di_read+formulas``  — combination: Japanese base + LaTeX formulas appended
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
            read_text: str = future_read.result()
            latex_formulas, markdown_text = future_layout.result()

        results: list[tuple[str, str]] = []
        if read_text:
            results.append((read_text, "azure_di_read"))
        if markdown_text:
            results.append((markdown_text, "azure_di_layout_markdown"))
        # Combined candidate: Japanese text base + accurate LaTeX formulas
        if read_text and latex_formulas:
            combined = (
                read_text
                + "\n\n[検出された数式 (LaTeX)]\n"
                + "\n".join(latex_formulas)
            )
            results.append((combined, "azure_di_read+formulas"))
        return results

    def _ocr_read_pass(self, image_bytes: bytes, RequestModel: Any) -> str:
        """prebuilt-read pass — returns plain line-joined text (preserves Japanese)."""
        try:
            result = self._di_client.begin_analyze_document(
                "prebuilt-read",
                RequestModel(bytes_source=image_bytes),
            ).result()
            lines: list[str] = [
                line.content
                for page in (result.pages or [])
                for line in (page.lines or [])
            ]
            return "\n".join(lines)
        except Exception:
            return ""

    def _ocr_layout_formulas_pass(
        self,
        image_bytes: bytes,
        RequestModel: Any,
        AnalysisFeature: Any,
        ContentFormat: Any,
    ) -> tuple[list[str], str]:
        """prebuilt-layout + FORMULAS + Markdown pass.

        Returns ``(latex_formulas, markdown_text)``.
        ``latex_formulas`` is a list of ``"[display] ..."`` / ``"[inline] ..."`` strings.
        ``markdown_text`` is the full Markdown content with the formula list appended.
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

            latex_formulas: list[str] = [
                f"[{'display' if getattr(f, 'kind', '') == 'display' else 'inline'}] {getattr(f, 'value', '')}"
                for page in (result.pages or [])
                for f in (getattr(page, "formulas", None) or [])
                if getattr(f, "value", None) and (getattr(f, "confidence", 1.0) or 1.0) >= 0.5
            ]
            if latex_formulas:
                parts.append("\n[検出された数式 (LaTeX)]\n" + "\n".join(latex_formulas))

            markdown_text = "\n".join(parts).strip()
            return latex_formulas, (markdown_text if len(markdown_text) > 20 else "")
        except Exception:
            return [], ""

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

        try:
            response = self._openai_client.chat.completions.create(
                model=settings.azure_openai_deployment,
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
                temperature=0.0,
                max_tokens=min(max(request.options.max_tokens, 512), 2000),
                response_format={"type": "json_object"},
            )
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
