import base64
import json
import re
import time
import uuid
from io import BytesIO

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException
from PIL import Image, ImageEnhance, ImageOps
from pypdf import PdfReader

from app.config import settings
from app.models import SolveAnswer, SolveMeta, SolveRequest, SolveResponse


class AwsMathSolver:
    def __init__(self):
        self._textract = boto3.client("textract", region_name=settings.textract_region)
        self._bedrock = boto3.client(
            "bedrock-runtime", region_name=settings.bedrock_region
        )

    def solve(self, request: SolveRequest) -> SolveResponse:
        start = time.time()
        image_bytes = self._resolve_image(request)
        problem_text, ocr_source, ocr_score, ocr_candidates, ocr_top_candidates = (
            self._extract_text_with_textract(image_bytes, request.input.image_url)
        )
        ocr_replacement_ratio, ocr_non_ascii_ratio = self._compute_ocr_quality_metrics(
            problem_text
        )
        answer_payload = self._generate_with_bedrock(problem_text, request)
        ocr_needs_review = self._should_flag_ocr_review(
            ocr_score, ocr_replacement_ratio, ocr_candidates
        )
        if ocr_needs_review:
            answer_payload = self._apply_ocr_review_warning(answer_payload)
        latency_ms = int((time.time() - start) * 1000)

        answer = SolveAnswer(
            final=answer_payload.get("final", ""),
            latex=answer_payload.get("latex"),
            steps=answer_payload.get("steps", []),
            confidence=float(answer_payload.get("confidence", 0.5)),
        )

        return SolveResponse(
            requestId=f"req_{uuid.uuid4().hex[:16]}",
            status="completed",
            problemText=problem_text,
            answer=answer,
            meta=SolveMeta(
                ocrProvider="textract",
                ocrSource=ocr_source,
                ocrScore=ocr_score,
                ocrCandidates=ocr_candidates,
                ocrTopCandidates=ocr_top_candidates,
                ocrReplacementRatio=ocr_replacement_ratio,
                ocrNonAsciiRatio=ocr_non_ascii_ratio,
                ocrNeedsReview=ocr_needs_review,
                model=settings.bedrock_model_id,
                latencyMs=latency_ms,
                costUsd=0.0,
            ),
        )

    def _resolve_image(self, request: SolveRequest) -> bytes:
        if request.input.image_base64:
            return self._decode_image_base64(request.input.image_base64)

        if request.input.image_url:
            if not settings.solve_allow_remote_image_url:
                raise HTTPException(status_code=400, detail="imageUrl is disabled")
            return self._download_image(request.input.image_url)

        raise HTTPException(
            status_code=400, detail="imageBase64 or imageUrl is required"
        )

    def _decode_image_base64(self, image_base64: str) -> bytes:
        raw = image_base64
        if "," in image_base64 and image_base64.startswith("data:"):
            raw = image_base64.split(",", 1)[1]

        try:
            data = base64.b64decode(raw, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid imageBase64") from exc

        self._validate_image_size(data)
        return data

    def _download_image(self, image_url: str) -> bytes:
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=400, detail="failed to fetch imageUrl"
            ) from exc

        content_type = response.headers.get("Content-Type", "")
        if "image/" not in content_type:
            raise HTTPException(status_code=400, detail="imageUrl is not an image")

        data = response.content
        self._validate_image_size(data)
        return data

    def _validate_image_size(self, data: bytes) -> None:
        if len(data) > settings.solve_max_image_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"image size exceeds limit ({settings.solve_max_image_bytes} bytes)",
            )

    def _extract_text_with_textract(
        self, image_bytes: bytes, image_url: str | None = None
    ) -> tuple[str, str, float, int, list[dict[str, float | str]]]:
        candidates: list[tuple[str, str]] = []

        variants = self._build_ocr_image_variants(image_bytes)
        for variant in variants:
            detect_text = self._extract_with_detect_document_text(variant)
            if detect_text:
                candidates.append((detect_text, "textract_detect_image"))

            analyze_text = self._extract_with_analyze_document(variant)
            if analyze_text:
                candidates.append((analyze_text, "textract_analyze_image"))

        pdf_bytes = self._download_pdf_from_image_url(image_url)
        if pdf_bytes:
            pdf_text = self._extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                candidates.append((pdf_text, "pdf_direct"))

            detect_text = self._extract_with_detect_document_text(pdf_bytes)
            if detect_text:
                candidates.append((detect_text, "textract_detect_pdf"))

            analyze_text = self._extract_with_analyze_document(pdf_bytes)
            if analyze_text:
                candidates.append((analyze_text, "textract_analyze_pdf"))

        if not candidates:
            raise HTTPException(
                status_code=502, detail="Textract returned no OCR candidates"
            )

        scored_candidates = [
            {
                "text": text,
                "source": source,
                "score": self._score_ocr_text(text, source),
            }
            for text, source in candidates
        ]
        scored_candidates.sort(key=lambda item: item["score"], reverse=True)

        top_candidates = [
            {
                "source": str(item["source"]),
                "score": round(float(item["score"]), 4),
                "textPreview": self._preview_text(str(item["text"])),
            }
            for item in scored_candidates[:3]
        ]

        best_text, best_source = max(
            candidates, key=lambda item: self._score_ocr_text(item[0], item[1])
        )
        best_score = self._score_ocr_text(best_text, best_source)
        problem_text = self._cleanup_ocr_text(best_text)
        if not problem_text:
            raise HTTPException(
                status_code=422, detail="No readable text found in image"
            )
        return (
            problem_text,
            best_source,
            round(best_score, 4),
            len(candidates),
            top_candidates,
        )

    def _build_ocr_image_variants(self, image_bytes: bytes) -> list[bytes]:
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                base = ImageOps.exif_transpose(img).convert("RGB")
                variants: list[Image.Image] = [base]

                gray = ImageOps.grayscale(base)
                contrast = ImageEnhance.Contrast(gray).enhance(2.2)
                variants.append(contrast)

                binary = contrast.point(
                    lambda x: 255 if x > 150 else 0, mode="1"
                ).convert("L")
                variants.append(binary)

                upscaled = binary.resize(
                    (binary.width * 2, binary.height * 2),
                    Image.Resampling.LANCZOS,
                )
                variants.append(upscaled)

                return [self._image_to_png_bytes(v) for v in variants]
        except Exception:
            return [image_bytes]

    def _image_to_png_bytes(self, image: Image.Image) -> bytes:
        buf = BytesIO()
        image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def _download_pdf_from_image_url(self, image_url: str | None) -> bytes | None:
        if not image_url:
            return None

        pdf_url = self._derive_pdf_url(image_url)
        if not pdf_url:
            return None

        try:
            response = requests.get(pdf_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return None

        data = response.content
        if not data or not data.startswith(b"%PDF"):
            return None

        self._validate_image_size(data)
        return data

    def _derive_pdf_url(self, image_url: str) -> str | None:
        if "/q_jpg/" in image_url:
            return re.sub(
                r"/q_jpg/([^/?#]+)\.(jpg|jpeg|png)$", r"/q_pdf/\1.pdf", image_url
            )

        lowered = image_url.lower()
        if (
            lowered.endswith(".jpg")
            or lowered.endswith(".jpeg")
            or lowered.endswith(".png")
        ):
            return re.sub(r"\.(jpg|jpeg|png)$", ".pdf", image_url, flags=re.IGNORECASE)

        return None

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            texts: list[str] = []
            for page in reader.pages:
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    texts.append(page_text)
            return "\n".join(texts).strip()
        except Exception:
            return ""

    def _extract_with_detect_document_text(self, image_bytes: bytes) -> str:
        try:
            resp = self._textract.detect_document_text(Document={"Bytes": image_bytes})
        except (BotoCoreError, ClientError):
            return ""

        return self._blocks_to_text(resp.get("Blocks", []), min_confidence=55.0)

    def _extract_with_analyze_document(self, image_bytes: bytes) -> str:
        try:
            resp = self._textract.analyze_document(
                Document={"Bytes": image_bytes},
                FeatureTypes=["FORMS", "TABLES", "LAYOUT"],
            )
        except (BotoCoreError, ClientError):
            return ""

        return self._blocks_to_text(resp.get("Blocks", []), min_confidence=45.0)

    def _blocks_to_text(self, blocks: list[dict], min_confidence: float) -> str:
        lines: list[str] = []
        for block in blocks:
            if block.get("BlockType") != "LINE":
                continue
            if float(block.get("Confidence", 0.0)) < min_confidence:
                continue
            text = (block.get("Text") or "").strip()
            if text:
                lines.append(text)
        return "\n".join(lines)

    def _cleanup_ocr_text(self, text: str) -> str:
        normalized = text.replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _score_ocr_text(self, text: str, source: str) -> float:
        if not text:
            return 0.0

        length_score = min(len(text), 4000) / 4000
        replacement_penalty = text.count("�") * 0.015
        math_tokens = re.findall(r"[A-Za-z0-9=+\-*/^()\[\]{}<>∫√πΣΔ∞]", text)
        math_score = min(len(math_tokens), 600) / 600
        line_score = (
            min(len([line for line in text.splitlines() if line.strip()]), 60) / 60
        )

        source_bonus_map = {
            "pdf_direct": 0.18,
            "textract_analyze_pdf": 0.08,
            "textract_detect_pdf": 0.05,
            "textract_analyze_image": 0.02,
            "textract_detect_image": 0.0,
        }
        source_bonus = source_bonus_map.get(source, 0.0)

        score = (
            (length_score * 0.45)
            + (math_score * 0.35)
            + (line_score * 0.20)
            + source_bonus
        )
        return max(score - replacement_penalty, 0.0)

    def _generate_with_bedrock(self, problem_text: str, request: SolveRequest) -> dict:
        prompt = self._build_prompt(problem_text, request)
        body = self._build_bedrock_request_body(prompt, request)

        try:
            response = self._bedrock.invoke_model(
                modelId=settings.bedrock_model_id,
                body=json.dumps(body).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Bedrock invocation failed: {exc.__class__.__name__}: {str(exc)}",
            ) from exc

        raw_body = response.get("body")
        payload = json.loads(raw_body.read()) if raw_body else {}
        text = self._extract_bedrock_text(payload)

        parsed = self._parse_json_answer(text)
        if parsed is None:
            parsed = {
                "final": text.strip()[:2000] or "解答を生成できませんでした。",
                "latex": None,
                "steps": [],
                "confidence": 0.3,
            }
        return self._normalize_answer_payload(parsed)

    def _build_bedrock_request_body(self, prompt: str, request: SolveRequest) -> dict:
        model_id = settings.bedrock_model_id.lower()

        if model_id.startswith("amazon.nova"):
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": request.options.max_tokens,
                    "temperature": 0.0,
                },
            }

        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.options.max_tokens,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        }
                    ],
                }
            ],
        }

    def _extract_bedrock_text(self, payload: dict) -> str:
        model_id = settings.bedrock_model_id.lower()

        if model_id.startswith("amazon.nova"):
            content = payload.get("output", {}).get("message", {}).get("content", [])
            if content and isinstance(content[0], dict):
                return content[0].get("text", "")
            return ""

        content = payload.get("content", [])
        if content and isinstance(content[0], dict):
            return content[0].get("text", "")
        return ""

    def _parse_json_answer(self, text: str) -> dict | None:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    def _normalize_answer_payload(self, payload: dict) -> dict:
        normalized = {
            "final": str(payload.get("final", "")).strip(),
            "latex": payload.get("latex"),
            "steps": payload.get("steps", []),
            "confidence": payload.get("confidence", 0.5),
        }

        final_text = normalized["final"]
        nested = self._parse_json_answer(final_text)
        if nested and any(
            k in nested for k in ["final", "latex", "steps", "confidence"]
        ):
            normalized["final"] = str(nested.get("final", "")).strip()
            normalized["latex"] = nested.get("latex", normalized["latex"])
            normalized["steps"] = nested.get("steps", normalized["steps"])
            normalized["confidence"] = nested.get(
                "confidence", normalized["confidence"]
            )
        else:
            normalized["final"] = self._strip_code_fences(final_text)

        if not isinstance(normalized["steps"], list):
            normalized["steps"] = [
                str(normalized["steps"]) if normalized["steps"] else ""
            ]
        normalized["steps"] = [
            str(step).strip() for step in normalized["steps"] if str(step).strip()
        ]

        try:
            normalized["confidence"] = float(normalized["confidence"])
        except (TypeError, ValueError):
            normalized["confidence"] = 0.5
        normalized["confidence"] = max(0.0, min(1.0, normalized["confidence"]))

        if normalized["latex"] is not None:
            normalized["latex"] = str(normalized["latex"]).strip() or None

        if not normalized["final"]:
            normalized["final"] = "解答を生成できませんでした。"

        return normalized

    def _strip_code_fences(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        return stripped.strip()

    def _preview_text(self, text: str, max_len: int = 80) -> str:
        one_line = re.sub(r"\s+", " ", text).strip()
        if len(one_line) <= max_len:
            return one_line
        return one_line[:max_len].rstrip() + "…"

    def _compute_ocr_quality_metrics(self, text: str) -> tuple[float, float]:
        if not text:
            return 0.0, 0.0

        replacement_count = text.count("�")
        text_len = max(len(text), 1)
        non_ascii_count = sum(1 for char in text if ord(char) > 127)

        replacement_ratio = round(replacement_count / text_len, 4)
        non_ascii_ratio = round(non_ascii_count / text_len, 4)
        return replacement_ratio, non_ascii_ratio

    def _should_flag_ocr_review(
        self, ocr_score: float, replacement_ratio: float, candidate_count: int
    ) -> bool:
        if candidate_count <= 0:
            return True
        if replacement_ratio >= settings.solve_ocr_review_max_replacement_ratio:
            return True
        return ocr_score < settings.solve_ocr_review_min_score

    def _apply_ocr_review_warning(self, answer_payload: dict) -> dict:
        final_text = str(answer_payload.get("final", "")).strip()
        warning = "【OCR要再確認】"
        if final_text and not final_text.startswith(warning):
            answer_payload["final"] = f"{warning} {final_text}"
        elif not final_text:
            answer_payload["final"] = (
                "【OCR要再確認】問題文の読み取り精度が低いため、解答を確定できません。"
            )
        return answer_payload

    def _build_prompt(self, problem_text: str, request: SolveRequest) -> str:
        steps_req = "必要" if request.options.need_steps else "不要"
        latex_req = "必要" if request.options.need_latex else "不要"
        return (
            "あなたは大学入試数学の解答アシスタントです。"
            "与えられた問題文を読み、厳密に解答してください。"
            "OCR由来のノイズや誤字が含まれる可能性があります。数学として自然な表記へ補正して解釈してください。"
            "出力は必ずJSONオブジェクトのみで返してください。\n"
            "JSON形式:"
            '{"final":"最終答案","latex":"LaTeX文字列またはnull",'
            '"steps":["手順1","手順2"],"confidence":0.0から1.0}\n\n'
            f"大学: {request.exam.university}\n"
            f"年度: {request.exam.year}\n"
            f"科目: {request.exam.subject}\n"
            f"問題番号: {request.exam.question_no}\n"
            f"解法手順: {steps_req}\n"
            f"LaTeX: {latex_req}\n\n"
            "問題文:\n"
            f"{problem_text}"
        )
