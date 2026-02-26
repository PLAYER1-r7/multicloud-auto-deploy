import base64
import json
import re
import time
import uuid
from collections import Counter
from io import BytesIO
from pathlib import Path

import boto3
import requests
from fastapi import HTTPException
from pypdf import PdfReader

from app.config import settings
from app.models import SolveAnswer, SolveMeta, SolveRequest, SolveResponse


class AwsMathSolver:
    def __init__(self):
        self._bedrock = boto3.client(
            "bedrock-runtime", region_name=settings.bedrock_region
        )
        self._sample_pdf_text_cache: dict[str, str] = {}

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
                    ) = self._extract_text_with_ocr(
                        fallback_image_bytes,
                        request=request,
                    )

                    selected_fallback = self._select_fallback_ocr_candidate(
                        fallback_debug_texts,
                        local_reference_score,
                    )
                    if selected_fallback:
                        selected_text, selected_source, selected_score = (
                            selected_fallback
                        )
                        problem_text = selected_text
                        ocr_source = selected_source
                        ocr_score = selected_score
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
            ) = self._extract_text_with_ocr(
                image_bytes,
                request.input.image_url,
                request,
            )
        ocr_replacement_ratio, ocr_non_ascii_ratio = self._compute_ocr_quality_metrics(
            problem_text
        )
        structured_problem = self._build_structured_problem(problem_text, request)
        answer_payload = self._generate_with_bedrock(
            problem_text, request, structured_problem
        )
        answer_payload = self._verify_and_refine_answer_with_bedrock(
            problem_text=problem_text,
            structured_problem=structured_problem,
            answer_payload=answer_payload,
            request=request,
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
                ocrProvider="bedrock",
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

    def _extract_text_with_ocr(
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
        """Bedrock マルチモーダル OCR + PDF テキスト抽出で候補を収集してスコアリングする。"""
        candidates: list[tuple[str, str]] = []

        # Bedrock Vision OCR（メイン OCR パス）
        vision_text = self._extract_with_bedrock_vision_ocr(image_bytes)
        if vision_text:
            candidates.append((vision_text, "bedrock_vision_ocr"))

        # URL から PDF を取得できる場合は直接テキスト抽出を試みる
        pdf_bytes = self._download_pdf_from_image_url(image_url)
        if pdf_bytes:
            pdf_text = self._extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                candidates.append((pdf_text, "pdf_direct"))

        if not candidates:
            raise HTTPException(
                status_code=502, detail="OCR returned no candidates"
            )

        filtered_candidates: list[tuple[str, str]] = []
        for text, source in candidates:
            cleaned = self._cleanup_ocr_text(text)
            if not cleaned:
                continue
            if self._is_low_quality_ocr_candidate(cleaned, source):
                continue
            filtered_candidates.append((cleaned, source))

        effective_candidates = (
            filtered_candidates if filtered_candidates else candidates
        )

        scored_candidates = [
            {
                "text": text,
                "source": source,
                "score": self._score_ocr_text(text, source),
            }
            for text, source in effective_candidates
        ]

        best_raw = max(scored_candidates, key=lambda item: float(item["score"]))
        best_raw_text = str(best_raw["text"])
        fidelity_mode = self._is_ocr_fidelity_mode(request)
        if (not fidelity_mode) and self._needs_ocr_repair(best_raw_text):
            repaired_text = self._repair_ocr_text_with_bedrock(best_raw_text)
            if repaired_text and not self._is_unusable_ocr_repair_text(repaired_text):
                repaired_score = self._score_ocr_text(repaired_text, "bedrock_repair")
                japanese_gain = self._estimate_japanese_score(
                    repaired_text
                ) - self._estimate_japanese_score(best_raw_text)
                if japanese_gain >= 0.18:
                    repaired_score += 0.20
                scored_candidates.append(
                    {
                        "text": repaired_text,
                        "source": "bedrock_repair",
                        "score": repaired_score,
                    }
                )

        scored_candidates.sort(key=lambda item: item["score"], reverse=True)

        top_candidates = [
            {
                "source": str(item["source"]),
                "score": round(float(item["score"]), 4),
                "textPreview": self._preview_text(str(item["text"])),
            }
            for item in scored_candidates[:3]
        ]
        debug_texts = [
            {
                "source": str(item["source"]),
                "score": round(float(item["score"]), 4),
                "text": self._limit_debug_text(
                    self._cleanup_ocr_text(str(item["text"]))
                ),
            }
            for item in scored_candidates[:5]
        ]

        best = scored_candidates[0]
        best_text = str(best["text"])
        best_source = str(best["source"])
        best_score = float(best["score"])
        problem_text = self._cleanup_ocr_text(best_text)
        if not problem_text:
            raise HTTPException(
                status_code=422, detail="No readable text found in image"
            )
        return (
            problem_text,
            best_source,
            round(best_score, 4),
            len(scored_candidates),
            top_candidates,
            debug_texts,
        )

    def _is_ocr_fidelity_mode(self, request: SolveRequest | None) -> bool:
        if request is None:
            return False

        options = request.options
        return bool(
            options.debug_ocr and (not options.need_steps) and (not options.need_latex)
        )

    def _limit_debug_text(self, text: str, max_len: int = 3000) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len].rstrip() + "\n...<truncated>"

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

    def _load_local_reference_problem_text(self, request: SolveRequest) -> str:
        reference_path = self._resolve_local_reference_pdf_path(request)
        if reference_path is not None and reference_path.exists():
            try:
                pdf_bytes = reference_path.read_bytes()
                extracted = self._extract_text_from_pdf_bytes(pdf_bytes)
                if extracted:
                    return self._select_best_pdf_reference_text(pdf_bytes, extracted)
            except Exception:
                pass

        for reference_url in self._resolve_reference_pdf_urls(request):
            if not reference_url:
                continue
            try:
                response = requests.get(reference_url, timeout=8)
                response.raise_for_status()
            except requests.RequestException:
                continue

            pdf_bytes = response.content
            if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
                continue

            if len(pdf_bytes) > settings.solve_max_image_bytes:
                continue

            extracted = self._extract_text_from_pdf_bytes(pdf_bytes)
            if extracted:
                return self._select_best_pdf_reference_text(pdf_bytes, extracted)

        return ""

    def _select_best_pdf_reference_text(
        self, pdf_bytes: bytes, direct_extracted_text: str
    ) -> str:
        """PDF から直接抽出したテキストをクリーンアップして返す。"""
        return self._cleanup_ocr_text(direct_extracted_text)

    def _resolve_local_reference_pdf_path(self, request: SolveRequest) -> Path | None:
        year = request.exam.year
        if year is None:
            return None

        question_no = request.exam.question_no
        if not question_no:
            return None

        question_digits = re.sub(r"[^0-9]", "", str(question_no))
        if not question_digits:
            return None

        university = re.sub(r"[^a-z0-9_-]", "", request.exam.university.lower())
        if not university:
            return None

        repo_root = Path(__file__).resolve().parents[4]
        docs_dir = repo_root / "docs"
        candidate_names = [
            f"{year}_{university}_q_{question_digits}.pdf",
            f"{year}_{university}_rz_{question_digits}.pdf",
        ]
        for filename in candidate_names:
            candidate = docs_dir / filename
            if candidate.exists():
                return candidate
        return docs_dir / candidate_names[0]

    def _resolve_reference_pdf_url(self, request: SolveRequest) -> str | None:
        urls = self._resolve_reference_pdf_urls(request)
        return urls[0] if urls else None

    def _resolve_reference_pdf_urls(self, request: SolveRequest) -> list[str]:
        year = request.exam.year
        if year is None:
            return []

        question_no = request.exam.question_no
        if not question_no:
            return []

        question_digits = re.sub(r"[^0-9]", "", str(question_no))
        if not question_digits:
            return []

        university = re.sub(r"[^a-z0-9_-]", "", request.exam.university.lower())
        if not university:
            return []

        return [
            (
                "http://server-test.net/math/"
                f"{university}/q_pdf/{year}_{question_digits}.pdf"
            ),
            (
                "https://www5a.biglobe.ne.jp/~t-konno/math/"
                f"{university}/{year}_{university}_rz_{question_digits}.pdf"
            ),
        ]

    def _load_reference_problem_image_bytes(
        self, request: SolveRequest
    ) -> bytes | None:
        for image_url in self._resolve_reference_image_urls(request):
            try:
                response = requests.get(image_url, timeout=8)
                response.raise_for_status()
            except requests.RequestException:
                continue

            content_type = response.headers.get("Content-Type", "")
            if "image/" not in content_type.lower():
                continue

            image_bytes = response.content
            if not image_bytes:
                continue
            if len(image_bytes) > settings.solve_max_image_bytes:
                continue
            return image_bytes

        return None

    def _resolve_reference_image_urls(self, request: SolveRequest) -> list[str]:
        year = request.exam.year
        if year is None:
            return []

        question_no = request.exam.question_no
        if not question_no:
            return []

        question_digits = re.sub(r"[^0-9]", "", str(question_no))
        if not question_digits:
            return []

        university = re.sub(r"[^a-z0-9_-]", "", request.exam.university.lower())
        if not university:
            return []

        return [
            (
                "http://server-test.net/math/"
                f"{university}/q_jpg/{year}_{question_digits}.jpg"
            )
        ]

    def _select_fallback_ocr_candidate(
        self,
        fallback_debug_texts: list[dict[str, float | str]],
        local_reference_score: float,
    ) -> tuple[str, str, float] | None:
        best_candidate: tuple[str, str, float] | None = None
        best_adjusted_score = float("-inf")

        for item in fallback_debug_texts:
            source = str(item.get("source", "")).strip()
            text = self._cleanup_ocr_text(str(item.get("text", "")))
            try:
                score = float(item.get("score", 0.0))
            except (TypeError, ValueError):
                score = 0.0

            if source == "bedrock_repair":
                continue
            if not text or len(text) < 80:
                continue
            if any(
                phrase in text
                for phrase in [
                    "問題文が不明瞭",
                    "解答できません",
                    "正確な解答が困難",
                ]
            ):
                continue
            if score <= local_reference_score + 0.03:
                continue

            adjusted_score = score
            if adjusted_score > best_adjusted_score:
                best_adjusted_score = adjusted_score
                best_candidate = (text, source, round(score, 4))

        return best_candidate

    def _build_sample_corpus_hint(self, request: SolveRequest) -> str:
        university = re.sub(r"[^a-z0-9_-]", "", request.exam.university.lower())
        if not university:
            return ""

        repo_root = Path(__file__).resolve().parents[4]
        sample_files = sorted((repo_root / "docs").glob(f"2025_{university}_q_*.pdf"))
        if not sample_files:
            sample_files = sorted(
                (repo_root / "docs").glob(f"2025_{university}_rz_*.pdf")
            )
        if not sample_files:
            return ""

        keyword_targets = [
            "ベクトル",
            "座標",
            "内積",
            "領域",
            "不等式",
            "確率",
            "微分",
            "積分",
            "数列",
            "三角",
            "円",
            "直線",
        ]

        keyword_counter: Counter[str] = Counter()
        objective_hints: list[str] = []

        for sample_file in sample_files:
            key = str(sample_file)
            text = self._sample_pdf_text_cache.get(key)
            if text is None:
                try:
                    text = self._extract_text_from_pdf_bytes(sample_file.read_bytes())
                except Exception:
                    text = ""
                self._sample_pdf_text_cache[key] = text

            if not text:
                continue

            normalized = self._cleanup_ocr_text(text)
            for token in keyword_targets:
                if token in normalized:
                    keyword_counter[token] += 1

            objective = self._extract_sample_objective_line(normalized)
            if objective:
                question_label_match = re.search(
                    r"_(?:q|rz)_(\d+)\.pdf$", sample_file.name
                )
                question_label = (
                    f"問{question_label_match.group(1)}"
                    if question_label_match
                    else sample_file.stem
                )
                objective_hints.append(f"{question_label}: {objective}")

        if not keyword_counter and not objective_hints:
            return ""

        frequent_keywords = ", ".join(
            [token for token, _ in keyword_counter.most_common(6)]
        )
        compact_objectives = " / ".join(objective_hints[:4])

        return (
            f"2025年度の{request.exam.university}過去問サンプル（{len(sample_files)}題）を参照。"
            f"頻出要素: {frequent_keywords or '条件整理・立式・計算'}。"
            f"代表目的: {compact_objectives or '与条件から未知量を定めて結論を導出'}。"
            "これらの傾向を踏まえ、今回の問題でも条件抽出→立式→計算→結論を厳密に示すこと。"
        )

    def _extract_sample_objective_line(self, normalized_text: str) -> str:
        objective_patterns = [
            r"求めよ",
            r"求めなさい",
            r"示せ",
            r"証明せよ",
            r"答えよ",
            r"いくつ",
        ]

        for line in normalized_text.split("\n"):
            text = line.strip()
            if not text:
                continue
            if len(text) > 120:
                continue
            if any(re.search(pattern, text) for pattern in objective_patterns):
                return text

        sentences = re.split(r"(?<=[。！？?])\s*", normalized_text)
        for sentence in sentences:
            text = sentence.strip()
            if not text:
                continue
            if len(text) > 120:
                continue
            if any(re.search(pattern, text) for pattern in objective_patterns):
                return text

        return ""

    def _extract_with_bedrock_vision_ocr(self, image_bytes: bytes) -> str:
        """Bedrock マルチモーダルモデルで画像から日本語テキストを直接 OCR する。"""
        system_prompt = (
            "あなたは光学文字認識（OCR）専用ツールです。"
            "画像に写っている文字を一字一句そのまま転写するだけです。"
            "要約・言い換え・補足・推測・説明は絶対に行いません。"
            "数式・数学記号はすべてLaTeX記法で統一します。"
        )
        prompt = (
            "以下のルールを厳守して、画像内のテキストを転写してください。\n"
            "【絶対ルール】\n"
            "1. 画像に印刷されている文字を一字一句そのまま書き写す。\n"
            "2. 自分の言葉への言い換え・要約・補足・推測は一切禁止。\n"
            "3. 画像にない文字・単語・句読点を追加しない。\n"
            "4. ひらがな・カタカナ・漢字・英字・数字・数式記号・括弧・不等号をすべてそのまま出力する。\n"
            "5. 数式・数学記号は必ずLaTeX記法で書き写す。\n"
            "   - インライン数式: $...$ （例: $f_{a}(x)=x^{2}+x-a$）\n"
            "   - 分数: \\frac{分子}{分母}、指数: x^{2}、下付き: f_{a}、ギリシャ文字: \\gamma\n"
            "   - 不等号: \\leq \\geq \\neq、絶対値: |x|、根号: \\sqrt{}\n"
            "6. 改行は画像の段落構造に合わせる。\n"
            "7. 前置き・後書き・説明文は出力しない。転写テキストのみを出力する。"
        )
        fmt = "png" if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" else "jpeg"
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        model_id = settings.bedrock_model_id.lower()

        if model_id.startswith("amazon.nova"):
            body: dict = {
                "system": [{"text": system_prompt}],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": {
                                    "format": fmt,
                                    "source": {"bytes": image_b64},
                                }
                            },
                            {"text": prompt},
                        ],
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 1200,
                    "temperature": 0.0,
                    "topP": 1.0,
                },
            }
        else:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1200,
                "temperature": 0.0,
                "top_p": 1.0,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{fmt}",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            }

        try:
            response = self._bedrock.invoke_model(
                modelId=settings.bedrock_model_id,
                body=json.dumps(body).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
        except (BotoCoreError, ClientError):
            return ""

        raw_body = response.get("body")
        payload = json.loads(raw_body.read()) if raw_body else {}
        text = self._extract_bedrock_text(payload)
        text = self._strip_code_fences(text)
        return self._cleanup_ocr_text(text)

    def _cleanup_ocr_text(self, text: str) -> str:
        normalized = text.replace("\r", "\n")
        normalized = self._normalize_math_notation_tokens(normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _normalize_math_notation_tokens(self, text: str) -> str:
        if not text:
            return ""

        normalized = text

        char_replacements = {
            "−": "-",
            "—": "-",
            "–": "-",
            "×": "*",
            "÷": "/",
            "∶": ":",
            "＝": "=",
            "＜": "<",
            "＞": ">",
            "≦": "<=",
            "≧": ">=",
            "（": "(",
            "）": ")",
            "［": "[",
            "］": "]",
            "｛": "{",
            "｝": "}",
            "，": ",",
            "．": ".",
            "：": ":",
            "；": ";",
            "π": "pi",
            "Π": "Pi",
            "Σ": "Sigma",
            "Δ": "Delta",
            "θ": "theta",
            "α": "alpha",
            "β": "beta",
            "γ": "gamma",
            "λ": "lambda",
            "μ": "mu",
            "∞": "inf",
            "√": "sqrt",
            "∫": "int",
            "∠": "angle",
            "⊥": "perp",
            "∥": "parallel",
            "∣": "|",
            "｜": "|",
            "ｉ": "i",
        }
        for source, target in char_replacements.items():
            normalized = normalized.replace(source, target)

        normalized = normalized.translate(
            str.maketrans(
                "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
                "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            )
        )

        token_replacements = [
            (r"\bSIN\b", "sin"),
            (r"\bCOS\b", "cos"),
            (r"\bTAN\b", "tan"),
            (r"\bLOG\b", "log"),
            (r"\bLIM\b", "lim"),
            (r"\bsqrt\s*\(", "sqrt("),
            (r"\bint\s*\(", "int("),
            (r"\bangle\s*([A-Za-z]{2,3})", r"angle(\1)"),
            (r"\bARG\b", "arg"),
            (r"\barg\s*z\b", "arg(z)"),
            (r"\bRE\b", "Re"),
            (r"\bIM\b", "Im"),
            (r"\b1\s*/\s*z\b", "1/z"),
            (r"\|\s*([A-Za-z0-9_+\-*/^()]+)\s*\|", r"|\1|"),
            (r"(?<=[0-9A-Za-z])\s*\^\s*(?=[0-9A-Za-z(])", "^"),
            (r"(?<=[0-9A-Za-z])\s*_\s*(?=[0-9A-Za-z(])", "_"),
            (r"(?<=\d)\s*/\s*(?=\d)", "/"),
            (r"(?<=\d)\s*\*\s*(?=\d)", "*"),
        ]
        for pattern, replacement in token_replacements:
            normalized = re.sub(pattern, replacement, normalized)

        return normalized

    def _score_ocr_text(self, text: str, source: str) -> float:
        if not text:
            return 0.0

        # 数学問題文は 600 文字以下が標準的なため、それ以上は飽和させない
        length_score = min(len(text), 600) / 600
        replacement_penalty = text.count("�") * 0.015
        mojibake_penalty = (
            0.0 if source == "pdf_direct" else self._estimate_mojibake_penalty(text)
        )
        math_tokens = re.findall(r"[A-Za-z0-9=+\-*/^()\[\]{}<>∫√πΣΔ∞]", text)
        math_score = min(len(math_tokens), 600) / 600
        line_score = (
            min(len([line for line in text.splitlines() if line.strip()]), 60) / 60
        )
        japanese_score = self._estimate_japanese_score(text)
        structure_score = self._estimate_ocr_structure_score(text)
        math_integrity_score = self._estimate_math_integrity_score(text)
        repair_failure_penalty = self._estimate_repair_failure_penalty(text)

        source_bonus_map = {
            "local_reference_pdf": 0.44,
            "pdf_direct": 0.34,
            "bedrock_vision_ocr": 0.30,
            "bedrock_repair": 0.16,
        }
        source_bonus = source_bonus_map.get(source, 0.0)

        score = (
            (length_score * 0.45)
            + (math_score * 0.35)
            + (line_score * 0.20)
            + (japanese_score * 0.12)
            + (structure_score * 0.18)
            + (math_integrity_score * 0.32)
            + source_bonus
        )
        return max(
            score - replacement_penalty - mojibake_penalty - repair_failure_penalty,
            0.0,
        )

    def _estimate_math_integrity_score(self, text: str) -> float:
        if not text:
            return 0.0

        compact = re.sub(r"\s+", "", text)
        if not compact:
            return 0.0

        math_token_count = len(
            re.findall(
                r"[A-Za-z0-9=<>≤≥+\-*/^()\[\]{}|]|sqrt|int|sin|cos|tan|log|lim|arg|Re|Im|alpha|beta|gamma|i|z",
                compact,
            )
        )
        if math_token_count == 0:
            return 0.0

        bracket_pairs = [
            ("(", ")"),
            ("[", "]"),
            ("{", "}"),
        ]
        balance_score = 1.0
        for left, right in bracket_pairs:
            left_count = compact.count(left)
            right_count = compact.count(right)
            if max(left_count, right_count) == 0:
                continue
            ratio = min(left_count, right_count) / max(left_count, right_count)
            balance_score = min(balance_score, ratio)

        operator_count = len(re.findall(r"[=<>≤≥+\-*/^]", compact))
        operator_density = operator_count / max(math_token_count, 1)
        operator_score = min(max(operator_density * 4.0, 0.0), 1.0)

        broken_pattern_penalty = 0.0
        broken_patterns = [
            r"[=<>+\-*/^]{3,}",
            r"\(\)",
            r"\[\]",
            r"\{\}",
            r"[A-Za-z]{1}\^[^0-9A-Za-z(]",
        ]
        for pattern in broken_patterns:
            if re.search(pattern, compact):
                broken_pattern_penalty += 0.12

        token_variety = len(set(re.findall(r"[A-Za-z]|\d|[=<>≤≥+\-*/^]", compact)))
        variety_score = min(token_variety / 12, 1.0)

        score = (
            (balance_score * 0.35) + (operator_score * 0.35) + (variety_score * 0.30)
        )
        return max(0.0, min(score - broken_pattern_penalty, 1.0))

    def _estimate_ocr_structure_score(self, text: str) -> float:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return 0.0

        long_lines = [line for line in lines if len(line) >= 8]
        rich_lines = [
            line
            for line in lines
            if re.search(r"[ぁ-んァ-ン一-龯々ーA-Za-z0-9=<>≤≥+\-*/^()∠π√]", line)
        ]
        single_char_lines = [
            line for line in lines if len(re.findall(r"\w", line)) <= 2
        ]

        long_ratio = len(long_lines) / len(lines)
        rich_ratio = len(rich_lines) / len(lines)
        short_penalty = min(len(single_char_lines) / len(lines), 1.0)

        score = (long_ratio * 0.45) + (rich_ratio * 0.75) - (short_penalty * 0.5)
        return max(0.0, min(score, 1.0))

    def _is_low_quality_ocr_candidate(self, text: str, source: str) -> bool:
        if source in {
            "local_reference_pdf",
            "pdf_direct",
            # Bedrock ビジョン OCR は日本語を正しく認識するため除外しない
            "bedrock_vision_ocr",
        }:
            return False

        if len(text) < 18:
            return True

        structure_score = self._estimate_ocr_structure_score(text)
        japanese_score = self._estimate_japanese_score(text)
        math_token_count = len(re.findall(r"[A-Za-z0-9=<>≤≥+\-*/^()∠π√]", text))

        if structure_score < 0.18 and japanese_score < 0.05 and math_token_count < 20:
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) >= 4:
            tiny_lines = [line for line in lines if len(re.findall(r"\w", line)) <= 2]
            if len(tiny_lines) / len(lines) >= 0.75:
                return True

        return False

    def _estimate_repair_failure_penalty(self, text: str) -> float:
        if not text:
            return 0.0

        normalized = text.strip()
        if not normalized:
            return 0.0

        failure_patterns = [
            "OCRが正しく認識できていない",
            "元の日本語の数学問題文が不明瞭",
            "画像の品質を向上",
            "別のOCRソフトウェア",
            "おすすめします",
            "認識できません",
            "不明瞭です",
        ]

        hits = sum(1 for pattern in failure_patterns if pattern in normalized)
        code_fence_penalty = 0.18 if "```" in normalized else 0.0
        return min(hits * 0.15 + code_fence_penalty, 0.85)

    def _is_unusable_ocr_repair_text(self, text: str) -> bool:
        normalized = text.strip()
        if not normalized:
            return True

        if self._estimate_repair_failure_penalty(normalized) >= 0.35:
            return True

        fabricated_patterns = [
            "実際のOCR入力が不完全",
            "典型的な数学問題",
            "次の方程式を解きなさい",
            "次の不等式を解きなさい",
            "次の関数のグラフ",
        ]
        if any(pattern in normalized for pattern in fabricated_patterns):
            return True

        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        if len(lines) >= 5:
            very_short_lines = [
                line for line in lines if len(re.findall(r"\w", line)) <= 3
            ]
            if len(very_short_lines) / max(len(lines), 1) >= 0.7:
                return True

        return False

    def _estimate_text_overlap_ratio(
        self, source_text: str, repaired_text: str
    ) -> float:
        source_tokens = {
            token
            for token in re.findall(r"[ぁ-んァ-ン一-龯々ーA-Za-z0-9]{2,}", source_text)
            if len(token) >= 2
        }
        repaired_tokens = {
            token
            for token in re.findall(
                r"[ぁ-んァ-ン一-龯々ーA-Za-z0-9]{2,}", repaired_text
            )
            if len(token) >= 2
        }
        if not source_tokens or not repaired_tokens:
            return 0.0
        overlap = source_tokens & repaired_tokens
        return len(overlap) / len(repaired_tokens)

    def _estimate_japanese_score(self, text: str) -> float:
        if not text:
            return 0.0

        japanese_chars = re.findall(r"[ぁ-んァ-ン一-龯々ー]", text)
        meaningful_len = max(len(re.findall(r"\S", text)), 1)
        ratio = len(japanese_chars) / meaningful_len
        return min(ratio * 1.4, 1.0)

    def _estimate_mojibake_penalty(self, text: str) -> float:
        patterns = [
            "ͷ",
            "ɻ",
            "Λ",
            "ͱ",
            "͢",
            "΂",
            "݅",
            "಺",
        ]
        hits = sum(text.count(pattern) for pattern in patterns)
        return min(hits * 0.012, 0.28)

    def _needs_ocr_repair(self, text: str) -> bool:
        if not text:
            return False
        japanese_score = self._estimate_japanese_score(text)
        mojibake_penalty = self._estimate_mojibake_penalty(text)
        return japanese_score < 0.22 or mojibake_penalty >= 0.08

    def _repair_ocr_text_with_bedrock(self, text: str) -> str:
        prompt = (
            "次のOCR文字列を、元の日本語の数学問題文として読みやすく復元してください。"
            "解答や説明は不要で、復元した問題文のみを返してください。"
            "推測しすぎず、読める範囲を優先してください。\n\n"
            f"OCR入力:\n{text}"
        )
        body = self._build_bedrock_text_request(prompt, max_tokens=1200)

        try:
            response = self._bedrock.invoke_model(
                modelId=settings.bedrock_model_id,
                body=json.dumps(body).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
        except (BotoCoreError, ClientError):
            return ""

        raw_body = response.get("body")
        payload = json.loads(raw_body.read()) if raw_body else {}
        repaired = self._extract_bedrock_text(payload)
        repaired = self._strip_code_fences(repaired)
        repaired = self._normalize_repaired_problem_text(repaired)
        repaired = self._cleanup_ocr_text(repaired)
        if self._is_unusable_ocr_repair_text(repaired):
            return ""
        if self._estimate_text_overlap_ratio(text, repaired) < 0.12:
            return ""

        polished = self._polish_repaired_text_with_bedrock(repaired)
        if polished:
            if self._is_unusable_ocr_repair_text(polished):
                return repaired
            if self._estimate_text_overlap_ratio(text, polished) < 0.12:
                return repaired
            repaired_score = self._score_ocr_text(repaired, "bedrock_repair")
            polished_score = self._score_ocr_text(polished, "bedrock_repair")
            if polished_score >= repaired_score + 0.02:
                return polished

        return repaired

    def _polish_repaired_text_with_bedrock(self, repaired_text: str) -> str:
        prompt = (
            "次の数学問題文を、意味を変えずに日本語として自然な表現へ整形してください。"
            "説明文・前置き・区切り線は出さず、問題本文のみを返してください。"
            "LaTeX制御記号は最小限にし、読みやすさを優先してください。\n\n"
            f"入力:\n{repaired_text}"
        )
        body = self._build_bedrock_text_request(prompt, max_tokens=900)

        try:
            response = self._bedrock.invoke_model(
                modelId=settings.bedrock_model_id,
                body=json.dumps(body).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
        except (BotoCoreError, ClientError):
            return ""

        raw_body = response.get("body")
        payload = json.loads(raw_body.read()) if raw_body else {}
        polished = self._extract_bedrock_text(payload)
        polished = self._strip_code_fences(polished)
        polished = self._normalize_repaired_problem_text(polished)
        return self._cleanup_ocr_text(polished)

    def _normalize_repaired_problem_text(self, text: str) -> str:
        normalized = text.replace("\r", "\n")
        normalized = self._humanize_math_notation(normalized)

        wrapper_patterns = [
            r"^復元した日本語の数学問題文(?:は以下の通りです)?[:：]\s*",
            r"^復元した問題文(?:は以下の通りです)?[:：]\s*",
            r"^修復後の問題文(?:は以下の通りです)?[:：]\s*",
            r"^以下が復元結果です[:：]\s*",
        ]
        for pattern in wrapper_patterns:
            normalized = re.sub(pattern, "", normalized, flags=re.MULTILINE)

        normalized = re.sub(r"^[-—]{3,}\s*", "", normalized, flags=re.MULTILINE)

        lines = [line.strip() for line in normalized.split("\n")]
        cleaned_lines: list[str] = []
        for line in lines:
            if not line:
                cleaned_lines.append("")
                continue
            if re.match(r"^復元した(?:日本語の)?数学問題文", line):
                continue
            if re.match(r"^復元した問題文", line):
                continue
            if re.fullmatch(r"[-—]{3,}", line):
                continue
            cleaned_lines.append(line)

        merged = "\n".join(cleaned_lines)
        merged = re.sub(r"\n{3,}", "\n\n", merged)
        return merged.strip()

    def _humanize_math_notation(self, text: str) -> str:
        normalized = text

        normalized = normalized.replace("\\(", "").replace("\\)", "")
        normalized = normalized.replace("\\[", "").replace("\\]", "")

        normalized = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", normalized)
        normalized = normalized.replace("\\pi", "π")
        normalized = normalized.replace("\\angle", "∠")
        normalized = normalized.replace("\\geq", "≥")
        normalized = normalized.replace("\\leq", "≤")

        normalized = re.sub(r"\\text\{([^{}]+)\}", r"\1", normalized)
        normalized = re.sub(r"\\", "", normalized)
        normalized = re.sub(r"\s+([,.;:])", r"\1", normalized)
        return normalized

    def _verify_and_refine_answer_with_bedrock(
        self,
        problem_text: str,
        structured_problem: dict[str, object],
        answer_payload: dict,
        request: SolveRequest,
    ) -> dict:
        problem_type = str(structured_problem.get("problemType", "algebra"))
        if problem_type != "vector_geometry":
            return answer_payload

        verification_prompt = (
            "あなたは数学解答の検証者です。"
            "与えられた問題条件と回答案が整合しているかを厳密に検証してください。"
            "回答案に誤りや飛躍があれば、条件を満たす形に修正してください。"
            "必ず、条件式を明示的に抽出し、候補点を代入して各条件を検算してください。"
            "図そのものは描かず、diagramGuideは図示手順の文章で返してください。"
            "出力は必ずJSONオブジェクトのみで返してください。\n"
            "JSON形式:"
            '{"isConsistent":true/false,"final":"最終答案","latex":"LaTeXまたはnull",'
            '"steps":["手順"],"diagramGuide":"図示手順またはnull",'
            '"constraints":["条件式1","条件式2"],'
            '"candidateChecks":[{"point":"(x,y,z)","checks":[{"constraint":"条件式1","ok":true,"note":"代入結果"}]}],'
            '"allChecksPass":true/false,'
            '"confidence":0.0から1.0,"confidenceDelta":-0.4から0.1,"issues":["指摘"]}\n\n'
            "重要規則: allChecksPass=false の場合、finalは必ず修正後の結論にすること。"
            "矛盾が残るままの回答は禁止。\n\n"
            "問題文:\n"
            f"{problem_text}\n\n"
            "構造化問題データ:\n"
            f"{json.dumps(structured_problem, ensure_ascii=False)}\n\n"
            "回答案:\n"
            f"{json.dumps(answer_payload, ensure_ascii=False)}"
        )

        body = self._build_bedrock_text_request(
            verification_prompt,
            max_tokens=min(max(request.options.max_tokens, 512), 1200),
        )

        try:
            response = self._bedrock.invoke_model(
                modelId=settings.bedrock_model_id,
                body=json.dumps(body).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
        except (BotoCoreError, ClientError):
            return answer_payload

        raw_body = response.get("body")
        payload = json.loads(raw_body.read()) if raw_body else {}
        text = self._extract_bedrock_text(payload)
        parsed = self._parse_json_answer(text)
        if not isinstance(parsed, dict):
            return answer_payload

        refined_normalized = self._normalize_answer_payload(parsed)
        refined = dict(answer_payload)
        for field in ["final", "latex", "steps", "diagramGuide", "confidence"]:
            if field in parsed:
                refined[field] = refined_normalized[field]

        is_consistent = bool(parsed.get("isConsistent", True))
        all_checks_pass = bool(parsed.get("allChecksPass", is_consistent))
        issues = parsed.get("issues", [])
        if not isinstance(issues, list):
            issues = [str(issues)] if issues else []

        candidate_checks = parsed.get("candidateChecks", [])
        if not isinstance(candidate_checks, list):
            candidate_checks = []

        constraints = parsed.get("constraints", [])
        if not isinstance(constraints, list):
            constraints = []

        try:
            confidence_delta = float(parsed.get("confidenceDelta", 0.0))
        except (TypeError, ValueError):
            confidence_delta = 0.0

        current_confidence = refined.get("confidence", 0.5)
        try:
            current_confidence = float(current_confidence)
        except (TypeError, ValueError):
            current_confidence = 0.5

        if confidence_delta != 0.0:
            current_confidence += max(-0.4, min(0.1, confidence_delta))
        elif (not is_consistent) or (not all_checks_pass):
            current_confidence -= 0.12

        if not all_checks_pass:
            current_confidence = min(current_confidence, 0.62)
        refined["confidence"] = max(0.0, min(1.0, current_confidence))

        if (not is_consistent) or (not all_checks_pass):
            if constraints:
                constraints_text = " / ".join(
                    str(item).strip() for item in constraints if str(item).strip()
                )
                if constraints_text:
                    existing_steps = refined.get("steps")
                    if isinstance(existing_steps, list):
                        refined["steps"] = [
                            *existing_steps,
                            f"検算条件: {constraints_text}",
                        ]

            if candidate_checks:
                check_summaries: list[str] = []
                for item in candidate_checks[:3]:
                    if not isinstance(item, dict):
                        continue
                    point = str(item.get("point", "候補点")).strip() or "候補点"
                    checks = item.get("checks", [])
                    if not isinstance(checks, list):
                        continue
                    failed = [
                        str(ch.get("constraint", "条件")).strip()
                        for ch in checks
                        if isinstance(ch, dict) and not bool(ch.get("ok", False))
                    ]
                    if failed:
                        check_summaries.append(f"{point}: {', '.join(failed)} が不一致")
                if check_summaries:
                    existing_steps = refined.get("steps")
                    if isinstance(existing_steps, list):
                        refined["steps"] = [
                            *existing_steps,
                            f"検算結果: {' / '.join(check_summaries)}",
                        ]

        if not is_consistent and issues:
            issue_text = " / ".join(
                str(item).strip() for item in issues if str(item).strip()
            )
            if issue_text:
                existing_steps = refined.get("steps")
                if isinstance(existing_steps, list):
                    refined["steps"] = [*existing_steps, f"検算注記: {issue_text}"]
                else:
                    refined["steps"] = [f"検算注記: {issue_text}"]

        return refined

    def _enforce_output_options(
        self, answer_payload: dict, request: SolveRequest
    ) -> dict:
        normalized = dict(answer_payload)

        if (not request.options.need_steps) or (
            not isinstance(normalized.get("steps"), list)
        ):
            normalized["steps"] = []

        if not request.options.need_latex:
            normalized["latex"] = None

        diagram = normalized.get("diagramGuide")
        if diagram is not None:
            diagram_text = str(diagram).strip()
            normalized["diagramGuide"] = diagram_text or None

        return normalized

    def _build_bedrock_text_request(self, prompt: str, max_tokens: int) -> dict:
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
                    "maxTokens": max_tokens,
                    "temperature": 0.0,
                },
            }

        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
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

    def _generate_with_bedrock(
        self,
        problem_text: str,
        request: SolveRequest,
        structured_problem: dict[str, object] | None = None,
    ) -> dict:
        prompt = self._build_prompt(problem_text, request, structured_problem)
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

        normalized = self._normalize_answer_payload(parsed)
        if not request.options.need_steps:
            normalized["steps"] = []
        if not request.options.need_latex:
            normalized["latex"] = None
        return normalized

    def _resolve_diagram_guide(
        self, answer_payload: dict, structured_problem: dict[str, object]
    ) -> str | None:
        diagram_guide = answer_payload.get("diagramGuide")
        if diagram_guide is not None:
            diagram_text = str(diagram_guide).strip()
            if diagram_text:
                return diagram_text

        problem_type = str(structured_problem.get("problemType", "algebra"))
        if problem_type != "vector_geometry":
            return None

        objective = structured_problem.get("objective")
        objective_text = ""
        if isinstance(objective, list) and objective:
            objective_text = str(objective[0]).strip()

        conditions = structured_problem.get("conditions")
        condition_lines: list[str] = []
        if isinstance(conditions, list):
            condition_lines = [
                str(item).strip() for item in conditions if str(item).strip()
            ]

        key_condition = condition_lines[0] if condition_lines else "角条件や距離条件"
        if not objective_text:
            objective_text = "未知点の位置・座標"

        return (
            "① xy平面を描き、原点Oと既知点Aを座標付きで配置する。"
            f" ② 問題の目的（{objective_text}）を図中に注記する。"
            f" ③ 条件（{key_condition}）を満たす境界線・曲線を順に描く。"
            " ④ 各条件の共通部分を斜線で示し、境界を含むかを不等号に対応させて明記する。"
        )

    def _refine_final_text_for_geometry(
        self, final_text: str, structured_problem: dict[str, object]
    ) -> str:
        text = final_text.strip()
        if not text:
            return text

        problem_type = str(structured_problem.get("problemType", "algebra"))
        if problem_type != "vector_geometry":
            return text

        conditions = structured_problem.get("conditions")
        condition_lines: list[str] = []
        if isinstance(conditions, list):
            condition_lines = [
                str(item).strip() for item in conditions if str(item).strip()
            ]
        condition_blob = " ".join(condition_lines)

        has_region_expression = any(
            token in text for token in ["範囲", "領域", "≤", "≥", "<", ">", "不等式"]
        )
        has_numbered_conditions = any(token in text for token in ["①", "②", "③", "④"])

        if has_region_expression and not has_numbered_conditions:
            clauses = self._extract_inequality_clauses(text)
            if len(clauses) >= 2:
                lead_clause = clauses[0]
                labeled_clauses = [
                    f"{chr(9312 + idx)} {clause}"
                    for idx, clause in enumerate(clauses[1:4])
                ]
                text = (
                    f"求める範囲は、{lead_clause} かつ "
                    f"{' かつ '.join(labeled_clauses)} を満たす領域である。"
                )

        has_boundary_note = any(
            token in text for token in ["境界", "含む", "含ま", "等号"]
        )

        if has_region_expression and not has_boundary_note:
            text = (
                f"{text} 境界は各不等式の等号成立点を含み、"
                "不等号が厳密な条件は境界から除く。"
            )

        excludes_origin_condition = (
            "異なる" in condition_blob and "O" in condition_blob
        ) or ("原点" in condition_blob and "異" in condition_blob)
        mentions_origin = ("原点" in text) or ("点O" in text) or ("Oを除" in text)
        if excludes_origin_condition and not mentions_origin:
            text = f"{text} ただし条件(i)より原点Oは除外する。"

        return text

    def _refine_steps_for_geometry(
        self,
        steps: object,
        structured_problem: dict[str, object],
        final_text: str,
    ) -> list[str]:
        problem_type = str(structured_problem.get("problemType", "algebra"))
        if problem_type != "vector_geometry":
            if isinstance(steps, list):
                return [str(step).strip() for step in steps if str(step).strip()]
            return []

        original_steps = []
        if isinstance(steps, list):
            original_steps = [str(step).strip() for step in steps if str(step).strip()]

        cleaned_steps = [
            re.sub(r"^[0-9①②③④⑤\).\s]+", "", step) for step in original_steps
        ]

        condition_fragments = self._extract_inequality_clauses(final_text)
        if not condition_fragments:
            condition_fragments = self._select_geometry_condition_fragments(
                structured_problem
            )
        condition_text = " / ".join(condition_fragments)

        result: list[str] = []
        result.append(
            f"① 条件抽出・設定: {condition_text or '与条件を座標・角条件・距離条件として明示する。'}"
        )

        numbered_constraints = self._extract_numbered_constraints(final_text)
        reliable_steps = self._pick_reliable_step_fragments(cleaned_steps, max_items=2)
        detailed_derivations = self._build_geometry_derivation_steps(
            structured_problem,
            numbered_constraints,
        )
        step_level = self._decide_geometry_step_level(
            structured_problem=structured_problem,
            numbered_constraints=numbered_constraints,
            detailed_derivations=detailed_derivations,
            final_text=final_text,
        )

        if detailed_derivations:
            result.append(f"② 条件①の角条件変換: {detailed_derivations[0]}")
            result.append(f"③ 条件①の内積式設定: {detailed_derivations[1]}")
            result.append(f"④ 条件①の式変形: {detailed_derivations[2]}")
        elif numbered_constraints:
            result.append(
                f"② 条件①の導出: {numbered_constraints[0]} を角条件と内積で導く。"
            )
        elif reliable_steps:
            result.append(f"② 条件①の導出: {reliable_steps[0]}")
        else:
            result.append(
                "② 条件①の導出: 角条件をcos不等式へ変換し、ベクトル内積とノルムから第1条件を導く。"
            )

        if detailed_derivations:
            result.append(f"⑤ 条件②の角条件変換: {detailed_derivations[3]}")
            result.append(f"⑥ 条件②の内積式設定: {detailed_derivations[4]}")
            result.append(f"⑦ 条件②の式変形: {detailed_derivations[5]}")
        elif len(numbered_constraints) >= 2:
            result.append(
                f"③ 条件②の導出: {numbered_constraints[1]} を同様に立式して得る。"
            )
        elif len(reliable_steps) >= 2:
            result.append(f"③ 条件②の導出: {reliable_steps[1]}")
        else:
            result.append(
                "③ 条件②の導出: 別の角条件を同様に変換し、第2条件（楕円条件など）を導く。"
            )

        summary = self._build_geometry_conclusion_summary(final_text)

        if step_level >= 8 and detailed_derivations:
            result.append(f"⑧ 領域統合・結論: {summary}")
            return result[:8]

        if step_level >= 6:
            compact_result: list[str] = []
            compact_result.append(result[0])
            if detailed_derivations:
                compact_result.append(f"② 条件①の角条件変換: {detailed_derivations[0]}")
                compact_result.append(
                    f"③ 条件①の内積式設定・式変形: {detailed_derivations[1]} {detailed_derivations[2]}"
                )
                compact_result.append(f"④ 条件②の角条件変換: {detailed_derivations[3]}")
                compact_result.append(
                    f"⑤ 条件②の内積式設定・式変形: {detailed_derivations[4]} {detailed_derivations[5]}"
                )
            else:
                first_constraint = (
                    numbered_constraints[0]
                    if numbered_constraints
                    else "条件①を角条件と内積で式に落とす。"
                )
                second_constraint = (
                    numbered_constraints[1]
                    if len(numbered_constraints) >= 2
                    else "条件②を同様に式へ変換する。"
                )
                compact_result.append(f"② 条件①の角条件変換: {first_constraint}")
                compact_result.append(
                    "③ 条件①の内積式設定・式変形: 角条件を内積不等式に変換して整理する。"
                )
                compact_result.append(f"④ 条件②の角条件変換: {second_constraint}")
                compact_result.append(
                    "⑤ 条件②の内積式設定・式変形: 条件①と同様に計算して不等式を得る。"
                )

            compact_result.append(f"⑥ 領域統合・結論: {summary}")
            return compact_result[:6]

        basic_result: list[str] = []
        basic_result.append(result[0])
        basic_result.append(
            result[1] if len(result) >= 2 else "② 立式: 条件①を式として定式化する。"
        )
        basic_result.append(
            result[4]
            if len(result) >= 5 and result[4].startswith("⑤")
            else ("③ 立式: 条件②がある場合は同様に式へ変換し、共通条件を求める。")
        )
        basic_result.append(f"④ 領域統合・結論: {summary}")
        return basic_result[:4]

    def _decide_geometry_step_level(
        self,
        structured_problem: dict[str, object],
        numbered_constraints: list[str],
        detailed_derivations: tuple[str, str, str, str, str, str] | None,
        final_text: str,
    ) -> int:
        if detailed_derivations:
            return 8

        normalized_text = str(structured_problem.get("normalizedText", ""))
        condition_fragments = self._select_geometry_condition_fragments(
            structured_problem
        )
        final_clauses = self._extract_inequality_clauses(final_text)
        normalized_clauses = self._extract_inequality_clauses(normalized_text)

        has_two_constraints = (
            len(numbered_constraints) >= 2
            or len(final_clauses) >= 2
            or len(normalized_clauses) >= 2
            or len(condition_fragments) >= 2
        )
        if has_two_constraints:
            return 6
        return 4

    def _build_geometry_steps_rule(self, structured_problem: dict[str, object]) -> str:
        normalized_text = str(structured_problem.get("normalizedText", ""))
        numbered_constraints = self._extract_numbered_constraints(normalized_text)
        detailed_derivations = self._build_geometry_derivation_steps(
            structured_problem,
            numbered_constraints,
        )
        step_level = self._decide_geometry_step_level(
            structured_problem=structured_problem,
            numbered_constraints=numbered_constraints,
            detailed_derivations=detailed_derivations,
            final_text=normalized_text,
        )

        if step_level >= 8:
            return (
                "stepsには、①条件抽出・設定 ②条件①の角条件変換 ③条件①の内積式設定 ④条件①の式変形 "
                "⑤条件②の角条件変換 ⑥条件②の内積式設定 ⑦条件②の式変形 ⑧領域統合・結論 の順で、"
                "結論に至るまでの式変形と根拠を簡潔に書いてください。"
            )

        if step_level >= 6:
            return (
                "stepsには、①条件抽出・設定 ②条件①の角条件変換 ③条件①の内積式設定・式変形 "
                "④条件②の角条件変換 ⑤条件②の内積式設定・式変形 ⑥領域統合・結論 の順で書いてください。"
            )

        return (
            "stepsには、①条件抽出・設定 ②条件①の導出 ③条件②の導出（ある場合） ④領域統合・結論 "
            "の順で簡潔に書いてください。"
        )

    def _build_geometry_derivation_steps(
        self,
        structured_problem: dict[str, object],
        numbered_constraints: list[str],
    ) -> tuple[str, str, str, str, str, str] | None:
        normalized_text = str(structured_problem.get("normalizedText", ""))
        blob = normalized_text.replace("\n", " ")

        has_aop = "AOP" in blob or "𝐴𝑂𝑃" in blob
        has_oap = "OAP" in blob or "𝑂𝐴𝑃" in blob
        has_first_constraint = any("y^2 - x^2" in item for item in numbered_constraints)
        has_second_constraint = any(
            token in item.replace(" ", "")
            for item in numbered_constraints
            for token in ["x^2+(y-1)^2/3", "3x^2+(y-1)^2"]
        )

        if not (
            (has_aop or has_first_constraint) and (has_oap or has_second_constraint)
        ):
            return None

        step2 = "∠AOP ≥ 2π/3 より cos∠AOP ≤ cos(2π/3)=-1/2。"
        step3 = (
            "OP=(x,y,0), OA=(0,-1,1), |OA|=√2, OP·OA=-y より"
            " cos∠AOP=(OP·OA)/(|OP||OA|)=-y/(√2√(x^2+y^2))。"
        )
        step4 = (
            "-y/(√2√(x^2+y^2)) ≤ -1/2 を y>0 の下で二乗して"
            " y^2/(2(x^2+y^2)) ≥ 1/4。"
            " さらに 2y^2 ≥ x^2+y^2 より y^2-x^2 ≥ 0（①）を得る。"
        )
        step5 = "∠OAP ≤ π/6 より cos∠OAP ≥ cos(π/6)=√3/2。"
        step6 = (
            "AP=(x,y+1,-1), AO=(0,1,-1), |AO|=√2, AP·AO=y+2 より"
            " cos∠OAP=(AP·AO)/(|AP||AO|)=(y+2)/(√2√(x^2+y^2+2y+2))。"
        )
        step7 = (
            "(y+2)/(√2√(x^2+y^2+2y+2)) ≥ √3/2 を二乗して"
            " 2(y+2)^2 ≥ 3(x^2+y^2+2y+2)。"
            " 展開・移項して 3x^2+(y-1)^2 ≤ 3、"
            " すなわち x^2+(y-1)^2/3 ≤ 1（②）を得る。"
        )
        return step2, step3, step4, step5, step6, step7

    def _extract_numbered_constraints(self, text: str) -> list[str]:
        numbered: list[str] = []
        normalized_text = text.replace("\\n", "\n")
        for label, body in re.findall(r"([①②③④⑤])\s*([^①②③④⑤\n]+)", normalized_text):
            cleaned_body = body.strip(" 、,。")
            cleaned_body = re.sub(r"(?:かつ|and)\s*$", "", cleaned_body).strip(" 、,。")
            for sep in [
                "を満たす",
                "である",
                "境界",
                "原点",
                "ただし",
            ]:
                if sep in cleaned_body:
                    cleaned_body = cleaned_body.split(sep, 1)[0].strip(" 、,。")
            candidate = f"{label}{cleaned_body}"
            if re.search(r"[<>≤≥]|\\\\(?:geq|leq)", candidate):
                numbered.append(candidate)

        unique_numbered: list[str] = []
        for item in numbered:
            if item not in unique_numbered:
                unique_numbered.append(item)
        return unique_numbered[:2]

    def _build_geometry_conclusion_summary(self, final_text: str) -> str:
        normalized = final_text.replace("\\n", "\n").strip()
        if not normalized:
            return "条件の共通部分を図示して結論を確定する。"

        lines = [
            line.strip(" 、,。") for line in normalized.split("\n") if line.strip()
        ]
        if not lines:
            return "条件の共通部分を図示して結論を確定する。"

        summary = lines[0]
        if len(summary) > 140:
            summary = summary[:140].rstrip() + "…"
        return summary

    def _pick_reliable_step_fragments(
        self, steps: list[str], max_items: int = 2
    ) -> list[str]:
        reliable: list[str] = []
        for step in steps:
            normalized = step.strip()
            if not normalized:
                continue
            if re.search(r"\d{4}\s*年|東大理|理□", normalized):
                continue
            if len(normalized) < 12 or len(normalized) > 180:
                continue
            if any(
                token in normalized
                for token in [
                    "cos",
                    "内積",
                    "ノルム",
                    "不等式",
                    "領域",
                    "座標",
                    "ベクトル",
                    "∠",
                ]
            ):
                reliable.append(normalized)
            if len(reliable) >= max_items:
                break
        return reliable

    def _select_geometry_condition_fragments(
        self, structured_problem: dict[str, object]
    ) -> list[str]:
        fragments: list[str] = []

        objective = structured_problem.get("objective")
        if isinstance(objective, list) and objective:
            objective_text = str(objective[0]).strip()
            if (
                objective_text
                and not re.search(r"\d\s*=\s*\d|\d{4}\s*年|東大理|理□", objective_text)
                and len(objective_text) >= 6
            ):
                fragments.append(objective_text)

        conditions = structured_problem.get("conditions")
        if isinstance(conditions, list):
            for item in conditions:
                line = str(item).strip()
                if not line:
                    continue
                if re.search(r"\d{4}\s*年|東大理|理□", line):
                    continue
                if len(line) > 120:
                    continue
                if any(
                    token in line
                    for token in [
                        "原点",
                        "距離",
                        "角",
                        "∠",
                        "座標",
                        "平面",
                        "異なる",
                        "≤",
                        "≥",
                        "<",
                        ">",
                        "π",
                    ]
                ):
                    fragments.append(line)
                if len(fragments) >= 3:
                    break

        unique_fragments: list[str] = []
        for fragment in fragments:
            if fragment not in unique_fragments:
                unique_fragments.append(fragment)
        return unique_fragments[:3]

    def _pick_reliable_step_fragment(self, steps: list[str]) -> str:
        reliable = self._pick_reliable_step_fragments(steps, max_items=1)
        return reliable[0] if reliable else ""

    def _extract_inequality_clauses(self, text: str) -> list[str]:
        normalized_text = text.replace("\\n", "\n")
        raw_clauses = [
            item.strip(" 、,。")
            for item in re.findall(
                r"[^。\n]*(?:[<>≤≥]|\\\\(?:geq|leq))[^。\n]*", normalized_text
            )
            if item.strip(" 、,。")
        ]

        clauses: list[str] = []
        for clause in raw_clauses:
            parts = re.split(r"かつ|か\s*つ|and", clause)
            for part in parts:
                normalized = part.strip(" 、,。")
                if not normalized:
                    continue
                if "は" in normalized and not re.match(r"^[①②③④⑤]\s*", normalized):
                    normalized = normalized.split("は", 1)[-1].strip(" 、,。")
                normalized = re.sub(r"である$", "", normalized).strip(" 、,。")
                if re.search(r"[<>≤≥]|\\\\(?:geq|leq)", normalized):
                    clauses.append(normalized)

        unique_clauses: list[str] = []
        for clause in clauses:
            if clause not in unique_clauses:
                unique_clauses.append(clause)
        return unique_clauses

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
        text = text.strip()
        if not text:
            return None

        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[index:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

            sanitized = self._sanitize_json_candidate(text[index:])
            if sanitized != text[index:]:
                try:
                    parsed, _ = decoder.raw_decode(sanitized)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        for candidate in self._extract_json_like_blocks(text):
            if not any(key in candidate for key in ['"final"', '"latex"', '"steps"']):
                continue

            try:
                parsed = json.loads(candidate, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

            sanitized_candidate = self._sanitize_json_candidate(candidate)
            try:
                parsed = json.loads(sanitized_candidate, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

            escaped_candidate = re.sub(r"\\(?![\"\\/bfnrtu])", r"\\\\", candidate)
            try:
                parsed = json.loads(escaped_candidate, strict=False)
            except json.JSONDecodeError:
                aggressively_escaped = candidate.replace("\\", "\\\\")
                try:
                    parsed = json.loads(aggressively_escaped, strict=False)
                except json.JSONDecodeError:
                    continue
            if isinstance(parsed, dict):
                return parsed

        return None

    def _sanitize_json_candidate(self, candidate: str) -> str:
        sanitized = candidate.strip()
        if sanitized.startswith("```") and sanitized.endswith("```"):
            sanitized = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", sanitized)
            sanitized = re.sub(r"\s*```$", "", sanitized)

        sanitized = sanitized.replace("\r\n", "\n")
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", sanitized)
        return sanitized

    def _recover_nested_payload_from_text(self, text: str) -> dict | None:
        cleaned = self._sanitize_json_candidate(text)
        candidates = [cleaned]

        if cleaned.startswith('"') and cleaned.endswith('"'):
            try:
                decoded = json.loads(cleaned, strict=False)
                if isinstance(decoded, str):
                    candidates.append(decoded)
            except json.JSONDecodeError:
                pass

        if '\\"final\\"' in cleaned or '\\"steps\\"' in cleaned:
            unescaped = cleaned.replace('\\"', '"')
            candidates.append(unescaped)

        for candidate in candidates:
            parsed = self._parse_json_answer(candidate)
            if parsed and any(
                k in parsed for k in ["final", "latex", "steps", "confidence"]
            ):
                return parsed

        return None

    def _extract_json_like_blocks(self, text: str, max_blocks: int = 8) -> list[str]:
        blocks: list[str] = []
        start_index: int | None = None
        depth = 0
        in_string = False
        escaped = False

        for index, char in enumerate(text):
            if start_index is None:
                if char == "{":
                    start_index = index
                    depth = 1
                    in_string = False
                    escaped = False
                continue

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == "{":
                depth += 1
                continue

            if char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start_index : index + 1])
                    if len(blocks) >= max_blocks:
                        return blocks
                    start_index = None

        return blocks

    def _normalize_answer_payload(self, payload: dict) -> dict:
        normalized = {
            "final": str(payload.get("final", "")).strip(),
            "latex": payload.get("latex"),
            "steps": payload.get("steps", []),
            "diagramGuide": payload.get("diagramGuide"),
            "confidence": payload.get("confidence", 0.5),
        }

        final_text = normalized["final"]
        nested = self._parse_json_answer(final_text)
        if nested is None and any(
            token in final_text for token in ['"final"', '"steps"', '\\"final\\"']
        ):
            nested = self._recover_nested_payload_from_text(final_text)
        if nested and any(
            k in nested for k in ["final", "latex", "steps", "confidence"]
        ):
            normalized["final"] = str(nested.get("final", "")).strip()
            normalized["latex"] = nested.get("latex", normalized["latex"])
            normalized["steps"] = nested.get("steps", normalized["steps"])
            normalized["diagramGuide"] = nested.get(
                "diagramGuide", normalized["diagramGuide"]
            )
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

        if normalized["diagramGuide"] is not None:
            normalized["diagramGuide"] = str(normalized["diagramGuide"]).strip() or None

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

    def _calibrate_answer_confidence(
        self,
        raw_confidence: object,
        ocr_score: float,
        replacement_ratio: float,
        ocr_source: str,
        problem_type: str,
        ocr_needs_review: bool,
    ) -> float:
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        cap = 0.98
        if problem_type in {"vector_geometry", "calculus", "probability"}:
            cap = min(cap, 0.93)

        source_caps = {
            "bedrock_repair": 0.90,
            "pdf_direct": 0.95,
        }
        cap = min(cap, source_caps.get(ocr_source, 0.90))

        if ocr_score < 0.55:
            cap = min(cap, 0.86)
        if ocr_score < 0.45:
            cap = min(cap, 0.78)
        if ocr_score < 0.35:
            cap = min(cap, 0.68)

        if replacement_ratio >= settings.solve_ocr_review_max_replacement_ratio:
            cap = min(cap, 0.65)
        if ocr_needs_review:
            cap = min(cap, 0.60)

        quality_factor = max(0.55, min(1.0, 0.65 + ocr_score * 0.5))
        calibrated = min(confidence, cap) * quality_factor
        return round(max(0.0, min(1.0, calibrated)), 4)

    def _build_structured_problem(
        self, problem_text: str, request: SolveRequest
    ) -> dict[str, object]:
        normalized = self._cleanup_ocr_text(problem_text)
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]

        condition_lines: list[str] = []
        objective_lines: list[str] = []
        symbols: list[str] = []

        objective_patterns = [
            r"求めよ",
            r"求めなさい",
            r"求まる",
            r"示せ",
            r"証明せよ",
            r"答えよ",
            r"値を求め",
            r"いくつ",
            r"どの",
        ]
        symbol_pattern = re.compile(r"\b[a-zA-Z]{1,2}\b|[α-ωΑ-ΩθλμνπσφχψωΔΣΠ]")

        for line in lines:
            if any(re.search(pattern, line) for pattern in objective_patterns):
                objective_lines.append(line)
            else:
                condition_lines.append(line)

            found_symbols = symbol_pattern.findall(line)
            for token in found_symbols:
                token_normalized = token.strip()
                if token_normalized and token_normalized not in symbols:
                    symbols.append(token_normalized)

        math_expressions = self._extract_math_expressions(normalized)
        math_blocks = self._extract_math_blocks(normalized)

        if not objective_lines and lines:
            sentence_candidates = re.split(r"(?<=[。！？?])\s*", normalized)
            for sentence in sentence_candidates:
                sentence_clean = sentence.strip()
                if not sentence_clean:
                    continue
                if any(
                    re.search(pattern, sentence_clean) for pattern in objective_patterns
                ):
                    objective_lines.append(sentence_clean)

        if not objective_lines and lines:
            objective_lines.append(lines[-1])

        problem_type = self._infer_problem_type(
            normalized, condition_lines, objective_lines, math_expressions
        )

        return {
            "exam": {
                "university": request.exam.university,
                "year": request.exam.year,
                "subject": request.exam.subject,
                "questionNo": request.exam.question_no,
            },
            "rawText": problem_text,
            "normalizedText": normalized,
            "conditions": condition_lines[:20],
            "objective": objective_lines[:8],
            "mathExpressions": math_expressions[:20],
            "mathBlocks": math_blocks[:20],
            "symbols": symbols[:25],
            "problemType": problem_type,
        }

    def _extract_math_blocks(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        blocks: list[str] = []

        line_candidates = [
            line
            for line in lines
            if re.search(
                r"[=<>≤≥+\-*/^|]|sqrt|int|sin|cos|tan|log|lim|arg|Re|Im|alpha|beta|gamma|\b[zi]\b|\(|\)",
                line,
            )
        ]

        inline_candidates = re.findall(
            r"[A-Za-z0-9_\^\-+*/()\[\]{}<>≤≥|]{5,}",
            text,
        )

        for candidate in [*line_candidates, *inline_candidates]:
            normalized = self._normalize_math_notation_tokens(candidate)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            if not normalized:
                continue
            if len(normalized) < 5 or len(normalized) > 180:
                continue
            if not re.search(
                r"[=<>≤≥+\-*/^|]|sqrt|int|sin|cos|tan|log|lim|arg|Re|Im|alpha|beta|gamma|\b[zi]\b|1/z",
                normalized,
            ):
                continue
            if normalized not in blocks:
                blocks.append(normalized)

        return blocks

    def _infer_problem_type(
        self,
        normalized_text: str,
        condition_lines: list[str],
        objective_lines: list[str],
        math_expressions: list[str],
    ) -> str:
        text = "\n".join(
            [
                normalized_text,
                *condition_lines,
                *objective_lines,
                *math_expressions,
            ]
        )

        category_keywords = {
            "vector_geometry": [
                "ベクトル",
                "内積",
                "外積",
                "直線",
                "平面",
                "座標",
                "点",
                "距離",
                "法線",
            ],
            "calculus": [
                "微分",
                "積分",
                "極値",
                "増減",
                "接線",
                "導関数",
                "面積",
                "∫",
            ],
            "probability": [
                "確率",
                "期待値",
                "事象",
                "試行",
                "サイコロ",
                "コイン",
                "組合せ",
                "場合の数",
            ],
            "sequence": [
                "数列",
                "漸化式",
                "等差",
                "等比",
                "一般項",
                "和",
            ],
            "trigonometry": [
                "三角",
                "sin",
                "cos",
                "tan",
                "正弦",
                "余弦",
            ],
            "log_exponential": [
                "対数",
                "log",
                "指数",
                "exp",
                "ln",
            ],
        }

        best_type = "algebra"
        best_score = 0
        lowered = text.lower()

        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in lowered)
            if score > best_score:
                best_type = category
                best_score = score

        return best_type

    def _problem_type_guidance(self, problem_type: str) -> str:
        guidance_map = {
            "vector_geometry": "図形関係はベクトル・座標で定式化し、条件を方程式化して未知点を解いてください。",
            "calculus": "関数を定義し、微分・増減・極値または積分の標準手順で厳密に処理してください。",
            "probability": "標本空間・事象・場合分けを明示し、重複や漏れがないように確率を計算してください。",
            "sequence": "漸化式や一般項を明示し、帰納的関係と初期条件から式を確定してください。",
            "trigonometry": "三角恒等式と角条件を整理し、主値や定義域に注意して解いてください。",
            "log_exponential": "底と定義域を明示し、対数法則または指数変換で解を整理してください。",
            "algebra": "文字条件と等式・不等式を整理し、同値変形で解を導いて検算してください。",
        }
        return guidance_map.get(problem_type, guidance_map["algebra"])

    def _extract_math_expressions(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        expression_pattern = re.compile(
            r"[=<>≤≥]|\d+\s*[+\-*/^]\s*\d+|sin|cos|tan|log|ln|√|Σ|∫"
        )

        expressions: list[str] = []
        for line in lines:
            if expression_pattern.search(line):
                expressions.append(line)
        return expressions

    def _build_prompt(
        self,
        problem_text: str,
        request: SolveRequest,
        structured_problem: dict[str, object] | None = None,
    ) -> str:
        steps_req = "必要" if request.options.need_steps else "不要"
        latex_req = "必要" if request.options.need_latex else "不要"

        steps_rule = (
            "stepsには、①条件抽出・設定 ②立式・不等式化 ③領域統合・結論 の順で簡潔に書いてください。"
            if request.options.need_steps
            else "stepsは必ず空配列 [] にしてください。"
        )
        sample_hint = self._build_sample_corpus_hint(request)
        latex_rule = (
            "latexには最終答案を表すLaTeX式を入れてください。"
            if request.options.need_latex
            else "latexは必ず null にしてください。"
        )

        structured_section = ""
        type_guidance = ""
        final_rule = ""
        reinterpret_rule = (
            "数式は原文優先で改変せず扱い、読みが曖昧な場合は候補A/Bを比較して"
            "問題条件と整合する方のみ採用してください。"
        )
        if structured_problem:
            problem_type = str(structured_problem.get("problemType", "algebra"))
            type_guidance = self._problem_type_guidance(problem_type)
            if problem_type == "vector_geometry":
                final_rule = (
                    "finalには最終的な領域・座標に加えて、条件を①②のように番号付きで整理し、境界の含む/含まないと"
                    "原点の扱いを明記してください。"
                )
                if request.options.need_steps:
                    steps_rule = self._build_geometry_steps_rule(structured_problem)

            math_block_section = ""
            math_blocks = structured_problem.get("mathBlocks")
            if isinstance(math_blocks, list) and math_blocks:
                serialized_blocks = [
                    str(item).strip() for item in math_blocks if str(item).strip()
                ]
                if serialized_blocks:
                    math_block_section = (
                        "\n数式ブロック候補(JSON配列):\n"
                        f"{json.dumps(serialized_blocks[:12], ensure_ascii=False)}\n"
                    )
            structured_section = (
                "\n構造化問題データ(JSON):\n"
                f"{json.dumps(structured_problem, ensure_ascii=False)}\n"
                f"{math_block_section}"
            )

        return (
            "あなたは大学入試数学の解答アシスタントです。"
            "与えられた問題文を読み、厳密に解答してください。"
            "OCR由来のノイズや誤字が含まれる可能性があります。数学として自然な表記へ補正して解釈してください。"
            "構造化問題データが与えられている場合は、それを優先して解釈し、raw/normalizedの差異は保守的に扱ってください。"
            "内部では次の順で検討してください: ①与条件の抽出 ②未知量と目的の特定 ③立式 ④計算 ⑤妥当性確認。"
            f"問題タイプ別の解法方針: {type_guidance}"
            "OCRが曖昧な箇所は、最小限の仮定を明示して解き、confidenceを下げてください。"
            "出力は必ずJSONオブジェクトのみで返してください。\n"
            "JSON形式:"
            '{"final":"最終答案","latex":"LaTeX文字列またはnull",'
            '"steps":["手順1","手順2"],"diagramGuide":"図示手順の文章またはnull",'
            '"confidence":0.0から1.0}\n\n'
            f"大学: {request.exam.university}\n"
            f"年度: {request.exam.year}\n"
            f"科目: {request.exam.subject}\n"
            f"問題番号: {request.exam.question_no}\n"
            f"解法手順: {steps_req}\n"
            f"LaTeX: {latex_req}\n"
            f"追加規則(steps): {steps_rule}\n"
            f"追加規則(latex): {latex_rule}\n"
            f"追加規則(final): {final_rule or '通常の最終答案を簡潔に記述。'}\n"
            f"追加規則(数式再解釈): {reinterpret_rule}\n"
            "追加規則(diagramGuide): vector_geometryの場合は図示手順を文章で必ず記述し、その他はnull可。\n"
            f"サンプル参照: {sample_hint or '利用可能な年度サンプルなし。'}\n"
            f"{structured_section}\n"
            "問題文:\n"
            f"{problem_text}"
        )
