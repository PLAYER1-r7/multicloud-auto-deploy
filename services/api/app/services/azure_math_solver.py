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
    # Positional OCR merge helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _poly_y_range(polygon: list | None) -> tuple[float, float] | None:
        """Return (y_min, y_max) from a polygon, or None if unavailable.

        Handles two formats returned by different Azure DI SDK builds:
          - Flat float list: ``[x0, y0, x1, y1, x2, y2, x3, y3]``
          - Point-object list: ``[Point(x=..., y=...), ...]``
        """
        if not polygon or len(polygon) < 2:
            return None
        try:
            if hasattr(polygon[0], "y"):
                y_vals = [p.y for p in polygon]
            else:
                y_vals = polygon[1::2]  # flat list: y at odd indices
            if not y_vals:
                return None
            return float(min(y_vals)), float(max(y_vals))
        except Exception:
            return None

    @staticmethod
    def _y_overlap_ratio(a_min: float, a_max: float, b_min: float, b_max: float) -> float:
        """Fraction of the smaller vertical span that overlaps with the other span."""
        overlap = min(a_max, b_max) - max(a_min, b_min)
        if overlap <= 0:
            return 0.0
        smaller = min(a_max - a_min, b_max - b_min)
        return overlap / max(smaller, 1e-9)

    @staticmethod
    def _is_formula_candidate(content: str) -> bool:
        """Return True if this line *could* be part of a formula region.

        Weak criterion: no CJK characters, not a problem-number label, short enough.
        Used to group consecutive candidate lines; the group is only treated as a
        formula region when it contains at least one strong math signal.
        """
        s = content.strip()
        if not s:
            return False
        # Problem-number labels like "(1)", "(2)" are not formula parts
        import re as _re
        if _re.fullmatch(r"\(\d+\)", s):
            return False
        # Lines with CJK characters are Japanese problem text
        cjk = sum(1 for c in s if "\u3040" <= c <= "\u9fff" or "\uff00" <= c <= "\uffef")
        if cjk > 0:
            return False
        return len(s) <= 80

    @staticmethod
    def _has_formula_signal(lines: list[str]) -> bool:
        """Return True if at least one line in the group contains a strong math signal."""
        import re as _re
        pattern = _re.compile(
            r"[\\∞∫∑∏√]|lim|log|sin|cos|tan|rightarrow|\bint\b|d[a-z]\b"
            r"|[+\-*/^=<>]{2,}|[+\-*/^].*[+\-*/^]",
            _re.IGNORECASE,
        )
        return any(pattern.search(l) for l in lines)

    def _find_formula_regions(self, read_lines: list[dict]) -> list[tuple[int, int]]:
        """Find contiguous runs of formula-candidate lines that contain a math signal.

        Returns a list of (start_idx, end_idx_exclusive) ranges.
        """
        regions: list[tuple[int, int]] = []
        i = 0
        n = len(read_lines)
        while i < n:
            if self._is_formula_candidate(read_lines[i]["content"]):
                j = i
                while j < n and self._is_formula_candidate(read_lines[j]["content"]):
                    j += 1
                group_texts = [read_lines[k]["content"] for k in range(i, j)]
                if self._has_formula_signal(group_texts):
                    regions.append((i, j))
                i = j
            else:
                i += 1
        return regions

    def _merge_read_with_formulas(
        self,
        read_lines: list[dict],
        rich_formulas: list[dict],
    ) -> str:
        """Replace display-formula lines in prebuilt-read output with accurate LaTeX.

        Strategy (two-pass):
          1. Polygon overlap (≥30 % Y-overlap) — preferred when polygon data exists.
          2. Heuristic region matching — fallback when polygons are None.
             Detects consecutive runs of formula-fragment lines and replaces each
             run with the next available display formula in document order.
          3. Display formulas with no polygon AND no heuristic match are appended
             at the bottom so they are never silently dropped.
          4. Inline formulas are always appended at the bottom for LLM context.
        """
        if not rich_formulas:
            return "\n".join(l["content"] for l in read_lines)

        display_formulas = [
            (f, self._poly_y_range(f.get("polygon")))
            for f in rich_formulas
            if f.get("kind") == "display"
        ]
        inline_latex = [
            f["value"]
            for f in rich_formulas
            if f.get("kind") != "display"
        ]

        # --- Pass 1: polygon-based matching ---
        line_formula: list[dict | None] = [None] * len(read_lines)
        for f, f_yr in display_formulas:
            if f_yr is None:
                continue
            for li, line in enumerate(read_lines):
                if line_formula[li] is not None:
                    continue
                l_yr = self._poly_y_range(line.get("polygon"))
                if l_yr and self._y_overlap_ratio(l_yr[0], l_yr[1], f_yr[0], f_yr[1]) >= 0.3:
                    line_formula[li] = f

        # Determine which display formulas are matched via polygons
        poly_emitted: set[int] = set()
        for f_on_line in line_formula:
            if f_on_line is not None:
                poly_emitted.add(id(f_on_line))

        # --- Pass 2: heuristic matching for unmatched display formulas ---
        unmatched_display = [f for f, _ in display_formulas if id(f) not in poly_emitted]
        if unmatched_display:
            regions = self._find_formula_regions(read_lines)
            print(f"[OCR-MERGE] heuristic regions={regions}, "
                  f"unmatched_display={len(unmatched_display)}")
            for region, fm in zip(regions, unmatched_display):
                start, end = region
                for li in range(start, end):
                    line_formula[li] = fm  # mark entire region as this formula
                poly_emitted.add(id(fm))  # now considered matched

        # --- Build output ---
        parts: list[str] = []
        emitted: set[int] = set()
        li = 0
        while li < len(read_lines):
            f = line_formula[li]
            if f is None:
                parts.append(read_lines[li]["content"])
                li += 1
            else:
                fid = id(f)
                if fid not in emitted:
                    emitted.add(fid)
                    parts.append(f"$${f['value']}$$")
                # Skip all read lines sthat belong to this formula's region
                while li < len(read_lines) and line_formula[li] is f:
                    li += 1

        # Safety net: display formulas still not emitted → append at bottom
        still_unmatched = [f["value"] for f, _ in display_formulas if id(f) not in emitted]
        if still_unmatched or inline_latex:
            parts.append("\n[検出された数式 (LaTeX)]")
            for val in still_unmatched:
                parts.append(f"[display] {val}")
            for val in inline_latex:
                parts.append(f"[inline] {val}")

        return "\n".join(parts)

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
