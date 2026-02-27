# 12 — OCR & Math Solving Service

> Part IV — Feature Reference | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
>
> **Coverage**: `/v1/solve` endpoint, `AzureMathSolver`, `GcpMathSolver`, OCR scoring pipeline, env vars, cost controls, debug endpoints.

---

## Overview

The math solving service provides AI-powered solutions to Japanese university entrance exam problems.
It accepts a problem image (URL or base64), performs multi-pass OCR, and returns a structured answer with LaTeX and step-by-step reasoning.

```
Image (URL or base64)
    │
    ▼
OCR Pass 1 ─── Azure AI Document Intelligence prebuilt-read  (Japanese text)
OCR Pass 2 ─── Azure AI Document Intelligence prebuilt-layout+FORMULAS  (LaTeX)
    │               ── or ──
    │           GCP Cloud Vision API  (Japanese text)
    │           GCP Gemini Vision      (LaTeX extraction)
    ▼
Merge ──────── 2-pass polygon/heuristic merge → best OCR candidate selected
    │
    ▼
LLM ────────── Azure OpenAI (gpt-4o)  or  GCP Vertex AI (gemini-2.0-flash)
    │
    ▼
SolveResponse  { problemText, answer.final, answer.steps, answer.latex, meta }
```

**Supported clouds**: Azure, GCP only.
AWS implementation has been removed (`501 Not Implemented` returned).

---

## Feature Toggle

The service is **disabled by default** to control costs.

```bash
# Enable (set on the Lambda / Cloud Function / Cloud Run service)
SOLVE_ENABLED=true

# Disabled response (HTTP 503):
{"detail": "solve endpoints are currently disabled (SOLVE_ENABLED=false)"}
```

---

## API Endpoints

All endpoints are under the `/v1` prefix and require `SOLVE_ENABLED=true`.

### POST /v1/solve

Solve a math problem from an image.

**Request body** (`SolveRequest`):

```json
{
  "input": {
    "imageUrl": "https://example.com/problem.jpg",
    "imageBase64": null,
    "source": "url"
  },
  "exam": {
    "university": "tokyo",
    "year": 2025,
    "subject": "math",
    "questionNo": "1"
  },
  "options": {
    "mode": "fast",
    "needSteps": true,
    "needLatex": true,
    "maxTokens": 2000,
    "debugOcr": false
  }
}
```

| Field               | Type                     | Default | Notes                                                                          |
| ------------------- | ------------------------ | ------- | ------------------------------------------------------------------------------ |
| `input.imageUrl`    | string\|null             | —       | Public URL of the problem image; mutually exclusive with `imageBase64`         |
| `input.imageBase64` | string\|null             | —       | Base64-encoded image bytes                                                     |
| `input.source`      | `paste`\|`upload`\|`url` | `paste` | Input origin hint                                                              |
| `exam.university`   | string                   | `tokyo` | University code (used for reference PDF lookup)                                |
| `exam.year`         | int\|null                | null    | Exam year (used for reference PDF lookup)                                      |
| `exam.subject`      | string                   | `math`  | Subject code                                                                   |
| `exam.questionNo`   | string\|null             | null    | Question number (e.g. `"1"`, `"2"`)                                            |
| `options.mode`      | `fast`\|`accurate`       | `fast`  | OCR strategy: `fast` = single-pass, `accurate` = multi-pass with PDF reference |
| `options.needSteps` | bool                     | `true`  | Include step-by-step reasoning in response                                     |
| `options.needLatex` | bool                     | `true`  | Include LaTeX in answer                                                        |
| `options.maxTokens` | int 256–4096             | `2000`  | LLM max output tokens                                                          |
| `options.debugOcr`  | bool                     | `false` | Include raw OCR candidates in `meta.ocrDebugTexts`                             |

**Response body** (`SolveResponse`):

```json
{
  "requestId": "abc123",
  "status": "ok",
  "problemText": "lim_{n→∞} n∫_1^2 log(1 + x/n)^{1/2} dx を求めよ。",
  "answer": {
    "final": "答えは log(2)/2 です。",
    "latex": "\\frac{\\log 2}{2}",
    "steps": ["Step 1: ...", "Step 2: ..."],
    "confidence": 0.92
  },
  "meta": {
    "ocrProvider": "azure",
    "ocrSource": "azure_di_merged",
    "ocrScore": 1.3955,
    "ocrCandidates": 6,
    "model": "gpt-4o",
    "latencyMs": 4230,
    "costUsd": 0.0034
  }
}
```

### GET /v1/ocr-debug?limit=20

Returns the last N OCR debug log entries from `ocr-debug/ocr_debug.jsonl` in Azure Blob Storage.
Falls back to `/tmp/ocr_debug.jsonl` if Blob is unavailable.

### GET /v1/ocr-debug/diag

Diagnostic endpoint — tests `/tmp` writability, stdout functioning, and Azure Blob connectivity.
Useful for verifying the debug logging pipeline is operational.

---

## OCR Sources & Scoring

The solver generates multiple OCR candidate texts and selects the highest-scoring one.

| OCR Source                 | Score Bonus | Description                                                    |
| -------------------------- | ----------: | -------------------------------------------------------------- |
| `local_reference_pdf`      |       +0.44 | Text extracted from a local reference PDF (highest quality)    |
| `pdf_direct`               |       +0.34 | Text extracted from a PDF fetched via URL                      |
| `gcp_vision_api`           |       +0.30 | Google Cloud Vision API                                        |
| `azure_di_merged`          |       +0.30 | Azure DI 2-pass merge: Japanese text + in-place LaTeX formulas |
| `gcp_vision_merged`        |       +0.28 | GCP Vision + Gemini Vision formula merge                       |
| `azure_di_read+formulas`   |       +0.26 | Azure DI Japanese text + formula appendix (fallback)           |
| `azure_di_layout_markdown` |       +0.12 | Azure DI Markdown (high LaTeX accuracy but may miss Japanese)  |
| `azure_di_read`            |        0.00 | Azure DI plain text (no formula extraction)                    |

The selected source is reported in `meta.ocrSource` and `meta.ocrScore`.

**Quality thresholds** (`config.py`):

```python
solve_ocr_review_min_score: float = 0.40        # flag as needing review below this
solve_ocr_review_max_replacement_ratio: float = 0.01  # flag if >1% chars replaced
```

---

## 2-Pass Formula Merge (azure_di_merged)

See [AI_AGENT_11_BUG_FIX_REPORTS.md §10](AI_AGENT_11_BUG_FIX_REPORTS.md#10-ocr-formula-merge-bugs-2026-02-27) for bug history.

```
Pass 1: Y-polygon overlap ≥ 30% → replace formula fragment inline
Pass 2: _find_formula_regions() heuristic → pair remaining display formulas
Safety net: still-unmatched display formulas appended as [display] at end
Inline formulas: always appended as [inline] at end
```

**Heuristic formula region detection** (`_find_formula_regions`):

- Line has no CJK characters
- Line ≤ 80 characters
- At least one strong math signal: `[\\∞∫∑∏√]|lim|log|sin|cos|tan` or 2+ consecutive operators

---

## Environment Variables

### Azure Solver (AzureMathSolver)

| Variable                               | Required | Description                                 |
| -------------------------------------- | -------- | ------------------------------------------- |
| `SOLVE_ENABLED`                        | ✓        | Must be `true` to enable endpoints          |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | ✓        | Azure AI DI endpoint URL                    |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY`      | ✓        | Azure AI DI API key                         |
| `AZURE_OPENAI_ENDPOINT`                | ✓        | Azure OpenAI endpoint URL                   |
| `AZURE_OPENAI_KEY`                     | ✓        | Azure OpenAI API key                        |
| `AZURE_OPENAI_DEPLOYMENT`              |          | LLM deployment name (default: `gpt-4o`)     |
| `AZURE_OPENAI_API_VERSION`             |          | API version (default: `2024-12-01-preview`) |
| `AZURE_STORAGE_ACCOUNT_NAME`           |          | For OCR debug log Blob Storage (optional)   |
| `AZURE_STORAGE_ACCOUNT_KEY`            |          | For OCR debug log Blob Storage (optional)   |

### GCP Solver (GcpMathSolver)

| Variable              | Required | Description                                     |
| --------------------- | -------- | ----------------------------------------------- |
| `SOLVE_ENABLED`       | ✓        | Must be `true` to enable endpoints              |
| `GCP_SERVICE_ACCOUNT` | ✓        | Service account email for signed URL generation |
| `GCP_VERTEX_LOCATION` |          | Vertex AI region (default: `us-central1`)       |
| `GCP_VERTEX_MODEL`    |          | Gemini model (default: `gemini-2.0-flash-001`)  |
| `GCP_VISION_API_KEY`  |          | Vision API key; omit to use ADC                 |

### Cost Control Variables

| Variable                       | Default          | Description                                             |
| ------------------------------ | ---------------- | ------------------------------------------------------- |
| `SOLVE_ENABLED`                | `false`          | Global kill switch — set `false` to stop all costs      |
| `SOLVE_ALLOW_REMOTE_IMAGE_URL` | `true`           | Allow image download from URL (disable to prevent SSRF) |
| `SOLVE_MAX_IMAGE_BYTES`        | `5242880` (5 MB) | Maximum image size; larger images are rejected with 400 |
| `AZURE_OPENAI_DEPLOYMENT`      | `gpt-4o`         | Switch to a cheaper model to reduce cost                |
| `options.maxTokens`            | `2000`           | Reduce per-request to cut LLM cost                      |

---

## Reference PDF Lookup

The solver can optionally fetch a reference PDF of the original exam problem to improve OCR quality.

**Lookup order** (`BaseMathSolver._resolve_reference_pdf_urls`):

1. `{university}/{year}/{subject}/{questionNo}.pdf` from a local path (dev only)
2. Remote URL derived from `exam.university`, `exam.year`, `exam.subject`, `exam.questionNo`

Reference PDFs are used as authoritative OCR candidates (`local_reference_pdf` or `pdf_direct` source) and contribute the highest possible score bonus (+0.44 or +0.34).

---

## Source Files

| File                                             | Description                                                                                            |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `services/api/app/routes/solve.py`               | FastAPI router: `/v1/solve`, `/v1/ocr-debug`, `/v1/ocr-debug/diag`                                     |
| `services/api/app/services/base_math_solver.py`  | Base class: image resolution, OCR scoring, formula merge, PDF extraction                               |
| `services/api/app/services/azure_math_solver.py` | Azure DI + Azure OpenAI implementation                                                                 |
| `services/api/app/services/gcp_math_solver.py`   | GCP Vision + Gemini implementation                                                                     |
| `services/api/app/models.py`                     | `SolveRequest`, `SolveResponse`, `SolveInput`, `SolveExam`, `SolveOptions`, `SolveAnswer`, `SolveMeta` |
| `services/api/app/config.py`                     | All `solve_*`, `azure_*`, `gcp_vertex_*` settings                                                      |

---

## Quick Test

```bash
# Enable locally
export SOLVE_ENABLED=true
export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
export AZURE_DOCUMENT_INTELLIGENCE_KEY=...
export AZURE_OPENAI_ENDPOINT=https://...
export AZURE_OPENAI_KEY=...

# Minimal curl request (image URL)
curl -s -X POST http://localhost:8000/v1/solve \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"imageUrl": "https://example.com/problem.jpg", "source": "url"},
    "exam": {"university": "tokyo", "year": 2025, "questionNo": "1"},
    "options": {"mode": "fast", "debugOcr": true}
  }' | python3 -m json.tool

# Check recent OCR debug logs
curl -s "http://localhost:8000/v1/ocr-debug?limit=5" | python3 -m json.tool

# Staging (Azure)
STAGING_API="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"
curl -s "${STAGING_API}/v1/ocr-debug/diag" | python3 -m json.tool
```

---

## Why AWS Is Not Supported

`/v1/solve` returns **HTTP 501 Not Implemented** when `CLOUD_PROVIDER=aws`.
This is a deliberate architectural decision, not a temporary omission.

### 1. AWS Textract に LaTeX 数式抽出機能がない（最大の障壁）

本サービスの OCR パイプラインの核心は **Azure Document Intelligence `prebuilt-layout` + FORMULAS** による LaTeX 数式の in-place 抽出である。

| 機能                    | Azure DI                                  | AWS Textract                 | 影響                   |
| ----------------------- | ----------------------------------------- | ---------------------------- | ---------------------- |
| 日本語テキスト認識      | ✓ `prebuilt-read`                         | △ 対応はしているが精度が低い | 問題文の誤読           |
| 数式を LaTeX で出力     | ✓ `kind=display/inline` + `value` (LaTeX) | ✗ 対応なし                   | 数式ゼロが極まる       |
| ポリゴン座標付き数式    | ✓ `bounding_regions[0].polygon`           | ✗                            | in-place マージ不可    |
| 日本語 + 数式の同時抽出 | ✓ 2パス並列で両立                         | ✗                            | パイプライン全体が崩壊 |

AWS Textract の Equations 機能（2023 年追加）は LaTeX を返さず、数式領域のバウンディングボックスのみを提供するため、本サービスの `_merge_read_with_formulas()` が動作しない。

### 2. API Gateway の 29 秒応答タイムアウト

AWS Lambda 自体の最大実行時間は 15 分だが、**API Gateway (REST API / HTTP API) の統合タイムアウトは最大 29 秒で変更不可**。

本サービスの `accurate` モードのパイプライン所要時間:

| フェーズ                   | 所要時間目安  |
| -------------------------- | ------------- |
| Azure DI 2パス並列 OCR     | 8〜20 秒      |
| 参照 PDF ダウンロード+抽出 | 3〜10 秒      |
| Azure OpenAI gpt-4o 推論   | 5〜20 秒      |
| **合計 (accurate mode)**   | **16〜50 秒** |

`fast` モードでも参照 PDF なしで 15〜30 秒かかることがある。
API Gateway 29 秒制限により、**accurate モードは AWS では構造的に実現不可能**。

> Lambda Function URL を直接使えばタイムアウトは回避できるが、マルチクラウド構成上の API Gateway は本プロジェクトでは必須インフラであり、それを迂回する構成は採用しない方針。

### 3. gpt-4o および Gemini が AWS Bedrock で提供されていない

本サービスは以下の LLM を使用する:

| クラウド | LLM                              | 特徴                                     |
| -------- | -------------------------------- | ---------------------------------------- |
| Azure    | Azure OpenAI `gpt-4o`            | 日本語数学記述、LaTeX 出力品質が最高水準 |
| GCP      | Vertex AI `gemini-2.0-flash-001` | マルチモーダル（画像入力直接対応）、高速 |

AWS Bedrock が提供するのは Claude, Llama, Mistral, Titan など。
`gpt-4o` は Microsoft/OpenAI 独占提供のため AWS Bedrock で利用不可。
`Gemini` シリーズも Google Cloud 独占提供のため AWS Bedrock で利用不可。

Claude (Bedrock) での代替実装は技術的には可能だが、評価済みプロンプト・スキーマ（`SolveAnswer.steps`, `SolveAnswer.latex`, `diagramGuide` 等）の再チューニングが必要であり、品質保証の観点から採用しない。

### 4. 設計経緯 — 一度 Bedrock フォールバックが存在した

コードコメントに残っているとおり、初期設計では `BaseMathSolver` に Bedrock フォールバックが組み込まれていた:

```python
# services/api/app/services/gcp_math_solver.py (ドキュメントコメント)
# フォールバック設計:
#   - Vision API 未設定 → Bedrock マルチモーダル OCR (親クラス)
#   - Vertex AI 未設定  → Bedrock LLM (親クラス)
```

しかし以下の理由で `BaseMathSolver` から削除され、現在は "Shared utilities only — no AWS/Bedrock clients" となっている:

- Textract による数式抽出が機能せず OCR スコアが常に最低値になる
- API Gateway タイムアウトにより accurate mode が完走しない
- LLM 品質（Claude vs gpt-4o）の差が日本語数学問題で顕著

### 5. まとめ — AWS で solve を動かすために必要な変更

将来 AWS 対応を検討する場合に必要な変更の全体像:

| 課題         | 必要な対応                                                                           |
| ------------ | ------------------------------------------------------------------------------------ |
| LaTeX OCR    | Textract の代わりに外部 OCR API（e.g. Mathpix）を統合                                |
| タイムアウト | Lambda Function URL + API Gateway バイパス、または非同期ジョブキュー化               |
| LLM          | Claude Sonnet/Haiku でプロンプト再チューニング（品質検証が必要）                     |
| 数式マージ   | `_merge_read_with_formulas()` の入力フォーマット変更（ポリゴン付き数式データが必要） |

現状では **対応予定なし**。AWS で数学 OCR が必要な場合は Azure または GCP にルーティングする設計を推奨する。

---

## Known Limitations & Future Work

| Item                             | Detail                                                                     |
| -------------------------------- | -------------------------------------------------------------------------- |
| AWS not supported                | `/v1/solve` returns 501 on AWS; 詳細は上記「Why AWS Is Not Supported」参照 |
| CJK-Latin OCR confusion          | `ェ` misread as `x`; post-processing normalization pending                 |
| `[display] \quad` false positive | `_has_formula_signal` too broad; `\quad` should be blacklisted             |
| Fraction OCR                     | `1/2` → `112`; structural recognition not yet implemented                  |
| GCP Vision merged                | `gcp_vision_merged` source is new (2026-02-27); not yet validated at scale |
| Cost tracking                    | `meta.costUsd` is estimated based on token counts, not actual billing      |

---

_Last updated: 2026-02-27_
