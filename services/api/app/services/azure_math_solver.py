"""Azure バックエンドを使った数学問題ソルバー。

OCR: Azure AI Document Intelligence (prebuilt-read)
LLM: Azure OpenAI (GPT-4o)

AWS ソルバーの共通ロジック（OCR スコアリング・プロンプト構築など）を継承し、
AWS 依存のメソッドだけを上書きする。
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.models import SolveAnswer, SolveMeta, SolveRequest, SolveResponse
from app.services.aws_math_solver import AwsMathSolver


class AzureMathSolver(AwsMathSolver):
    """Azure DI + OpenAI を使った数学ソルバー。

    AWS クライアント（Bedrock）を使うメソッドを上書きし、
    共通ロジック（スコアリング・プロンプト生成など）は継承で再利用する。
    """

    def __init__(self) -> None:
        # boto3 クライアントは使わないが親 __init__ は呼ばない
        # （boto3 接続が失敗するため）
        self._sample_pdf_text_cache: dict[str, str] = {}
        # 親クラスの except 節で参照される例外クラスを、Azure 環境でも安全に
        # 定義しておく（boto3 のコードパスには実際にはヒットしない）
        self._BotoCoreError = Exception
        self._ClientError = Exception
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

        (
            problem_text,
            ocr_source,
            ocr_score,
            ocr_candidates,
            ocr_top_candidates,
            ocr_debug_texts,
        ) = self._extract_text_with_azure_di(image_bytes, request)

        ocr_replacement_ratio, ocr_non_ascii_ratio = self._compute_ocr_quality_metrics(
            problem_text
        )
        structured_problem = self._build_structured_problem(problem_text, request)
        answer_payload = self._generate_with_openai(
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
            problemText=problem_text,
            answer=answer,
            meta=SolveMeta(
                ocrProvider="azure_document_intelligence",
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
    ) -> tuple[str, str, float, int, list[dict], list[dict]]:
        """Azure DI prebuilt-read で OCR し、候補をスコアリングして返す。

        DI クライアントが設定されていない場合は Bedrock Vision OCR にフォールバック。
        """
        candidates: list[tuple[str, str]] = []

        # --- Azure DI ---
        if self._di_client is not None:
            di_text, di_source = self._call_azure_di(image_bytes)
            if di_text:
                candidates.append((di_text, di_source))

        # --- Bedrock Vision フォールバック（DI 未設定 or 全滅時）---
        if not candidates:
            vision_text = self._extract_with_bedrock_vision_ocr(image_bytes)
            if vision_text:
                candidates.append((vision_text, "bedrock_vision_ocr_fallback"))

        if not candidates:
            raise HTTPException(
                status_code=502, detail="Azure DI returned no OCR candidates"
            )

        # --- スコアリング ---
        scored: list[dict] = []
        for text, source in candidates:
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

        self._dump_ocr_to_file(image_bytes, scored)

        return (
            str(best["text"]),
            str(best["source"]),
            round(float(best["score"]), 4),
            len(scored),
            top_candidates,
            debug_texts,
        )

    # ------------------------------------------------------------------
    # OCR デバッグ出力
    # ------------------------------------------------------------------

    _OCR_DUMP_PATH = "/tmp/ocr_debug.jsonl"

    def _dump_ocr_to_file(self, image_bytes: bytes, scored: list[dict]) -> None:
        """OCR 結果を JSONL ファイルに追記する（デバッグ用）。

        出力先: /tmp/ocr_debug.jsonl
        形式  : 1 行 = 1 リクエスト分の JSON オブジェクト
        フィールド:
          ts         : ISO8601 タイムスタンプ (UTC)
          image_sha  : 画像 SHA-256 先頭 16 文字
          candidates : [{source, score, text}] — スコア降順
        """
        try:
            image_sha = hashlib.sha256(image_bytes).hexdigest()[:16]
            record = {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            with open(self._OCR_DUMP_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # ファイル書き込み失敗は無視

    def _call_azure_di(self, image_bytes: bytes) -> tuple[str, str]:
        """Azure DI で OCR してテキストとソース名のタプルを返す。

        Pass 1 (推奨): prebuilt-layout + FORMULAS feature + Markdown 出力
          - result.content に構造を保持したマークダウンテキストが入る
          - page.formulas  に数式の LaTeX 文字列が入る
          -> 添字・指数・分数・積分記号が正確に復元される

        Pass 2 (フォールバック): prebuilt-read + 行単位テキスト
          - FORMULAS feature 非対応リージョン / エラー時に使用
        """
        try:
            from azure.ai.documentintelligence.models import (
                AnalyzeDocumentRequest,
                DocumentAnalysisFeature,
                DocumentContentFormat,
            )
        except ImportError:
            return "", "azure_di_read"

        # ---- Pass 1: prebuilt-layout + FORMULAS + Markdown ----
        try:
            poller = self._di_client.begin_analyze_document(
                "prebuilt-layout",
                AnalyzeDocumentRequest(bytes_source=image_bytes),
                features=[DocumentAnalysisFeature.FORMULAS],
                output_content_format=DocumentContentFormat.MARKDOWN,
            )
            result = poller.result()

            parts: list[str] = []
            # result.content は Markdown 形式のドキュメント全文
            if result.content:
                parts.append(result.content)

            # ページごとの数式オブジェクト（LaTeX）を抽出
            latex_formulas: list[str] = []
            if result.pages:
                for page in result.pages:
                    formulas = getattr(page, "formulas", None) or []
                    for formula in formulas:
                        val = getattr(formula, "value", None)
                        conf = getattr(formula, "confidence", 1.0)
                        kind = getattr(formula, "kind", "")
                        if val and (conf or 1.0) >= 0.5:
                            tag = "display" if kind == "display" else "inline"
                            latex_formulas.append(f"[{tag}] {val}")

            if latex_formulas:
                parts.append(
                    "\n[検出された数式 (LaTeX)]\n" + "\n".join(latex_formulas)
                )

            text = "\n".join(parts).strip()
            if len(text) > 20:
                return text, "azure_di_layout_markdown"
        except Exception:
            pass  # フォールバックへ

        # ---- Pass 2: prebuilt-read（従来の行ベース実装） ----
        try:
            poller = self._di_client.begin_analyze_document(
                "prebuilt-read",
                AnalyzeDocumentRequest(bytes_source=image_bytes),
            )
            result = poller.result()

            lines: list[str] = []
            if result.pages:
                for page in result.pages:
                    if page.lines:
                        for line in page.lines:
                            lines.append(line.content)
            return "\n".join(lines), "azure_di_read"
        except Exception:
            return "", "azure_di_read"

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
