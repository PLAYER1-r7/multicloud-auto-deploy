"""GCP バックエンドを使った数学問題ソルバー。

OCR : Google Cloud Vision API (DOCUMENT_TEXT_DETECTION)
      + Gemini Vision による数式抽出 (2パスマージ)
LLM : Vertex AI Gemini (gemini-2.0-flash-001 など)

AWS ソルバーの共通ロジック（OCR スコアリング・プロンプト構築など）を継承し、
GCP 依存のメソッドだけを上書きする。
フォールバック設計:
  - Vision API 未設定 → Bedrock マルチモーダル OCR (親クラス)
  - Vertex AI 未設定  → Bedrock LLM (親クラス)

OCR マージ戦略 (Azure DI の 2パスマージに対応する GCP 実装):
  Pass 1: Vision API で純テキスト取得 (日本語忠実)
  Pass 2: Gemini Vision で画像から LaTeX 数式を JSON 抽出
  Merge : _merge_read_with_formulas() (BaseMathSolver 共通) でヒューリスティックに in-place 置換
  → candidate: gcp_vision_merged
"""

from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.models import SolveAnswer, SolveMeta, SolveRequest, SolveResponse
from app.services.base_math_solver import BaseMathSolver


class GcpMathSolver(BaseMathSolver):
    """GCP Vision API + Vertex AI Gemini を使った数学ソルバー。"""

    def __init__(self) -> None:
        self._sample_pdf_text_cache: dict[str, str] = {}
        self._vision_client = self._build_vision_client()
        self._vertex_model = self._build_vertex_model()

    # ------------------------------------------------------------------
    # クライアント初期化
    # ------------------------------------------------------------------

    def _build_vision_client(self) -> Any:
        """Cloud Vision API クライアントを構築する。"""
        try:
            from google.cloud import vision  # type: ignore[import]

            # Vision API キーが設定されていれば明示的に認証
            api_key = settings.gcp_vision_api_key
            if api_key:
                import google.auth.credentials  # type: ignore[import]

                client_options = {"api_key": api_key}
                return vision.ImageAnnotatorClient(client_options=client_options)
            # Application Default Credentials (ADC) を利用
            return vision.ImageAnnotatorClient()
        except ImportError:
            return None
        except Exception:
            return None

    def _build_vertex_model(self) -> Any:
        """Vertex AI Gemini モデルを構築する。"""
        if not settings.gcp_project_id:
            return None
        try:
            import vertexai  # type: ignore[import]
            from vertexai.generative_models import (
                GenerativeModel,  # type: ignore[import]
            )

            vertexai.init(
                project=settings.gcp_project_id,
                location=settings.gcp_vertex_location,
            )
            return GenerativeModel(settings.gcp_vertex_model)
        except ImportError:
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # solve() エントリポイント（AWS 版を GCP 用に再実装）
    # ------------------------------------------------------------------

    def solve(self, request: SolveRequest) -> SolveResponse:
        start = time.time()
        image_bytes = self._resolve_image(request)
        local_reference_text = self._load_local_reference_problem_text(request)

        if local_reference_text:
            local_reference_clean = self._cleanup_ocr_text(local_reference_text)
            local_reference_score = self._score_ocr_text(
                local_reference_clean, "local_reference_pdf"
            )
            problem_text = local_reference_clean
            ocr_source = "local_reference_pdf"
            ocr_score = round(local_reference_score, 4)
            ocr_candidates = 1
            ocr_top_candidates = [
                {
                    "source": "local_reference_pdf",
                    "score": round(local_reference_score, 4),
                    "textPreview": self._preview_text(local_reference_clean),
                }
            ]
            ocr_debug_texts = [
                {
                    "source": "local_reference_pdf",
                    "score": round(local_reference_score, 4),
                    "text": self._limit_debug_text(local_reference_clean),
                }
            ]

            if local_reference_score < 0.55:
                fallback_image_bytes = self._load_reference_problem_image_bytes(request)
                if fallback_image_bytes:
                    (
                        _fallback_text,
                        _fallback_source,
                        _fallback_score,
                        fallback_candidates,
                        fallback_top_candidates,
                        fallback_debug_texts,
                    ) = self._extract_text_with_vision_api(
                        fallback_image_bytes,
                        request=request,
                    )
                    selected = self._select_fallback_ocr_candidate(
                        fallback_debug_texts, local_reference_score
                    )
                    if selected:
                        problem_text, ocr_source, ocr_score = selected
                        ocr_candidates = fallback_candidates
                        ocr_top_candidates = fallback_top_candidates
                        ocr_debug_texts = fallback_debug_texts
        else:
            (
                problem_text,
                ocr_source,
                ocr_score,
                ocr_candidates,
                ocr_top_candidates,
                ocr_debug_texts,
            ) = self._extract_text_with_vision_api(
                image_bytes,
                image_url=request.input.image_url,
                request=request,
            )

        ocr_replacement_ratio, ocr_non_ascii_ratio = self._compute_ocr_quality_metrics(
            problem_text
        )
        structured_problem = self._build_structured_problem(problem_text, request)
        answer_payload = self._generate_with_gemini(
            problem_text, request, structured_problem
        )
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
            ocr_score, ocr_replacement_ratio, ocr_candidates
        )
        if ocr_needs_review:
            answer_payload = self._apply_ocr_review_warning(answer_payload)

        problem_type = str(structured_problem.get("problemType", "algebra"))
        answer_payload["confidence"] = self._calibrate_answer_confidence(
            raw_confidence=answer_payload.get("confidence", 0.5),
            ocr_score=ocr_score,
            replacement_ratio=ocr_replacement_ratio,
            ocr_source=ocr_source,
            problem_type=problem_type,
            ocr_needs_review=ocr_needs_review,
        )
        answer_payload = self._enforce_output_options(answer_payload, request)
        latency_ms = int((time.time() - start) * 1000)

        return SolveResponse(
            requestId=f"req_{uuid.uuid4().hex[:16]}",
            status="completed",
            problemText=problem_text,
            answer=SolveAnswer(
                final=answer_payload.get("final", ""),
                latex=answer_payload.get("latex"),
                steps=answer_payload.get("steps", []),
                diagramGuide=answer_payload.get("diagramGuide"),
                confidence=float(answer_payload.get("confidence", 0.5)),
            ),
            meta=SolveMeta(
                ocrProvider="gcp_vision",
                ocrSource=ocr_source,
                ocrScore=ocr_score,
                ocrCandidates=ocr_candidates,
                ocrTopCandidates=ocr_top_candidates,
                ocrDebugTexts=ocr_debug_texts if request.options.debug_ocr else None,
                structuredProblem=structured_problem
                if request.options.debug_ocr
                else None,
                ocrReplacementRatio=ocr_replacement_ratio,
                ocrNonAsciiRatio=ocr_non_ascii_ratio,
                ocrNeedsReview=ocr_needs_review,
                model=settings.gcp_vertex_model,
                latencyMs=latency_ms,
                costUsd=0.0,
            ),
        )

    # ------------------------------------------------------------------
    # GCP Vision API OCR
    # ------------------------------------------------------------------

    def _extract_text_with_vision_api(
        self,
        image_bytes: bytes,
        image_url: str | None = None,
        request: SolveRequest | None = None,
    ) -> tuple[
        str,
        str,
        float,
        int,
        list[dict[str, float | str]],
        list[dict[str, float | str]],
    ]:
        """Cloud Vision DOCUMENT_TEXT_DETECTION で OCR し、候補をスコアリングする。

        Vision API 未設定時は Bedrock OCR にフォールバックする。
        """
        candidates: list[tuple[str, str]] = []

        # Vision API + Gemini Vision を並列実行
        vision_text: str = ""
        rich_lines: list[dict] = []
        rich_formulas: list[dict] = []

        if self._vision_client is not None:
            if self._vertex_model is not None:
                # 2パス並列実行
                with ThreadPoolExecutor(max_workers=2) as pool:
                    future_vision = pool.submit(self._ocr_vision_pass, image_bytes)
                    future_formulas = pool.submit(
                        self._extract_formulas_with_gemini_vision, image_bytes
                    )
                    vision_text, rich_lines = future_vision.result()
                    rich_formulas = future_formulas.result()
            else:
                vision_text, rich_lines = self._ocr_vision_pass(image_bytes)

            if vision_text:
                candidates.append((vision_text, "gcp_vision_api"))

            # gcp_vision_merged: Vision テキスト + Gemini 数式 in-place マージ
            if rich_lines and rich_formulas:
                merged = self._merge_read_with_formulas(rich_lines, rich_formulas)
                if merged:
                    candidates.append((merged, "gcp_vision_merged"))

        # PDF 直接テキスト抽出
        pdf_bytes = self._download_pdf_from_image_url(image_url)
        if pdf_bytes:
            pdf_text = self._extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                candidates.append((pdf_text, "pdf_direct"))

        if not candidates:
            raise HTTPException(
                status_code=502,
                detail=(
                    "GCP Vision API returned no OCR candidates. "
                    "Ensure Cloud Vision API is enabled and credentials are configured."
                ),
            )

        # スコアリング
        scored: list[dict] = []
        for text, source in candidates:
            cleaned = self._cleanup_ocr_text(text)
            if not cleaned:
                continue
            if self._is_low_quality_ocr_candidate(cleaned, source):
                continue
            scored.append(
                {
                    "text": cleaned,
                    "source": source,
                    "score": self._score_ocr_text(cleaned, source),
                }
            )

        if not scored:
            # フィルタで全候補が除外された場合はフィルタなしで再スコアリング
            for text, source in candidates:
                cleaned = self._cleanup_ocr_text(text)
                if cleaned:
                    scored.append(
                        {
                            "text": cleaned,
                            "source": source,
                            "score": self._score_ocr_text(cleaned, source),
                        }
                    )

        if not scored:
            raise HTTPException(
                status_code=422, detail="No readable text found in image"
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]

        top_candidates = [
            {
                "source": str(c["source"]),
                "score": round(float(c["score"]), 4),
                "textPreview": self._preview_text(str(c["text"])),
            }
            for c in scored[:3]
        ]
        debug_texts = [
            {
                "source": str(c["source"]),
                "score": round(float(c["score"]), 4),
                "text": self._limit_debug_text(str(c["text"])),
            }
            for c in scored[:5]
        ]

        return (
            str(best["text"]),
            str(best["source"]),
            round(float(best["score"]), 4),
            len(scored),
            top_candidates,
            debug_texts,
        )

    def _call_vision_api(self, image_bytes: bytes) -> str:
        """Cloud Vision DOCUMENT_TEXT_DETECTION を呼び出す（テキスト全文のみ）。"""
        try:
            from google.cloud import vision  # type: ignore[import]

            image = vision.Image(content=image_bytes)
            response = self._vision_client.document_text_detection(image=image)
            if response.error.message:
                return ""
            full_text = response.full_text_annotation.text or ""
            return full_text
        except Exception:
            return ""

    def _ocr_vision_pass(
        self, image_bytes: bytes
    ) -> tuple[str, list[dict]]:
        """Vision API を呼び出し ``(plain_text, rich_lines)`` を返す。

        ``rich_lines`` の各要素は ``{"content": str, "polygon": None}``。
        Vision API はページレベルのバウンディングボックスしか公開しないため
        polygon は常に None とし、Pass 2 のヒューリスティック検出に任せる。
        """
        text = self._call_vision_api(image_bytes)
        if not text:
            return "", []
        lines = [{"content": line, "polygon": None} for line in text.splitlines()]
        return text, lines

    def _extract_formulas_with_gemini_vision(
        self, image_bytes: bytes
    ) -> list[dict]:
        """Gemini Vision で画像から LaTeX 数式を抽出し ``rich_formulas`` リストを返す。

        返り値の各要素: ``{"value": str, "kind": "display"|"inline", "polygon": None}``

        Gemini が利用できない場合や解析エラー時は空リストを返す（非致命的）。
        """
        if self._vertex_model is None:
            return []
        try:
            from vertexai.generative_models import (  # type: ignore[import]
                GenerationConfig,
                Part,
            )

            prompt = (
                "この数学問題の画像から、すべての数式を LaTeX で抽出してください。\n"
                "display 数式（独立した行に表示される数式）は kind を \"display\"、"
                "inline 数式（文章中に埋め込まれた数式）は kind を \"inline\" として分類してください。\n"
                "以下の JSON 配列のみを返してください（コードフェンスや説明は不要）:\n"
                '[{"kind":"display","value":"LaTeX文字列"}, ...]'
            )
            image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
            generation_config = GenerationConfig(
                temperature=0.0,
                max_output_tokens=512,
            )
            response = self._vertex_model.generate_content(
                [prompt, image_part],
                generation_config=generation_config,
            )
            raw = (response.text or "").strip()
            raw = self._strip_code_fences(raw)
            formulas_raw = json.loads(raw)
            if not isinstance(formulas_raw, list):
                return []
            rich: list[dict] = []
            for item in formulas_raw:
                if not isinstance(item, dict):
                    continue
                val = str(item.get("value", "")).strip()
                kind = str(item.get("kind", "display")).strip()
                if not val:
                    continue
                rich.append({"value": val, "kind": kind, "polygon": None})
            print(
                f"[GCP-FORMULA] Gemini Vision extracted {len(rich)} formulas"
                f" ({sum(1 for f in rich if f['kind']=='display')} display,"
                f" {sum(1 for f in rich if f['kind']!='display')} inline)"
            )
            return rich
        except Exception as exc:
            print(f"[GCP-FORMULA] WARN: Gemini Vision formula extraction failed: {exc}")
            return []

    # ------------------------------------------------------------------
    # Vertex AI Gemini LLM 解答生成
    # ------------------------------------------------------------------

    def _generate_with_gemini(
        self,
        problem_text: str,
        request: SolveRequest,
        structured_problem: dict[str, object] | None = None,
    ) -> dict:
        """Vertex AI Gemini で解答を生成する。"""
        if self._vertex_model is None:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Vertex AI Gemini model is not configured. "
                    "Set GCP_PROJECT_ID and ensure Vertex AI API is enabled."
                ),
            )

        prompt = self._build_prompt(problem_text, request, structured_problem)
        system_instruction = (
            "あなたは大学入試数学の解答アシスタントです。"
            "出力は必ず JSON オブジェクトのみで返してください。"
            "余分なテキスト・コードフェンス・説明は一切含めないこと。"
        )

        try:
            from vertexai.generative_models import (
                GenerationConfig,  # type: ignore[import]
            )

            generation_config = GenerationConfig(
                temperature=0.0,
                max_output_tokens=min(
                    max(request.options.max_tokens, 512),
                    8192 if request.options.mode == "accurate" else 2000,
                ),
                response_mime_type="application/json",
            )
            # Gemini はシステム命令をモデル初期化時に渡すか、最初のメッセージに付ける
            full_prompt = f"{system_instruction}\n\n{prompt}"
            response = self._vertex_model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )
            text = response.text or ""
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Vertex AI Gemini invocation failed: {exc}",
            ) from exc

        text = self._strip_code_fences(text)
        parsed = self._parse_json_answer(text)
        if parsed is None:
            parsed = {
                "final": text.strip()[:2000] or "解答を生成できませんでした。",
                "latex": None,
                "steps": [],
                "confidence": 0.3,
            }
        return self._normalize_answer_payload(parsed)
