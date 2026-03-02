# 12 — OCR・数式解答サービス

> Part IV — 機能リファレンス | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
>
> **カバー範囲**: `/v1/solve` エンドポイント、`AzureMathSolver`、`GcpMathSolver`、OCR スコアリングパイプライン、環境変数、コスト制御、デバッグエンドポイント。

---

## 概要

数学解答サービスは、日本の大学入試問題に対して AI による解答を提供します。
問題画像（URL または base64）を受け取り、複数パス OCR を実行し、LaTeX と段階的な解法を含む構造化レスポンスを返します。

```
画像（URL または base64）
    │
    ▼
OCR Pass 1 ─── Azure AI Document Intelligence prebuilt-read（日本語テキスト）
OCR Pass 2 ─── Azure AI Document Intelligence prebuilt-layout+FORMULAS（LaTeX）
    │               ── または ──
    │           GCP Cloud Vision API（日本語テキスト）
    │           GCP Gemini Vision（LaTeX 抽出）
    ▼
Merge ──────── 2-pass polygon/heuristic merge → 最良 OCR 候補を選択
    │
    ▼
LLM ────────── Azure OpenAI（gpt-4o）または GCP Vertex AI（gemini-2.0-flash）
    │
    ▼
SolveResponse  { problemText, answer.final, answer.steps, answer.latex, meta }
```

**対応クラウド**: Azure と GCP のみ。
AWS 実装は削除済みで、`501 Not Implemented` を返します。

---

## 機能トグル

コスト制御のため、このサービスは**デフォルトで無効**です。

```bash
# 有効化（Lambda / Cloud Function / Cloud Run サービスで設定）
SOLVE_ENABLED=true

# 無効時レスポンス（HTTP 503）:
{"detail": "solve endpoints are currently disabled (SOLVE_ENABLED=false)"}
```

---

## API エンドポイント

すべてのエンドポイントは `/v1` プレフィックス配下で、`SOLVE_ENABLED=true` が必要です。

### POST /v1/solve

画像から数学問題を解きます。

**リクエストボディ**（`SolveRequest`）:

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

| フィールド          | 型                       | 既定値  | 説明                                                              |
| ------------------- | ------------------------ | ------- | ----------------------------------------------------------------- |
| `input.imageUrl`    | string\|null             | —       | 問題画像の公開 URL。`imageBase64` と排他                          |
| `input.imageBase64` | string\|null             | —       | base64 エンコード済み画像バイト列                                 |
| `input.source`      | `paste`\|`upload`\|`url` | `paste` | 入力元ヒント                                                      |
| `exam.university`   | string                   | `tokyo` | 大学コード（参照 PDF 検索に使用）                                 |
| `exam.year`         | int\|null                | null    | 年度（参照 PDF 検索に使用）                                       |
| `exam.subject`      | string                   | `math`  | 科目コード                                                        |
| `exam.questionNo`   | string\|null             | null    | 問題番号（例: `"1"`, `"2"`）                                      |
| `options.mode`      | `fast`\|`accurate`       | `fast`  | OCR 戦略: `fast` は単一パス、`accurate` は参照 PDF 併用マルチパス |
| `options.needSteps` | bool                     | `true`  | レスポンスに段階的解法を含める                                    |
| `options.needLatex` | bool                     | `true`  | レスポンスに LaTeX を含める                                       |
| `options.maxTokens` | int 256–4096             | `2000`  | LLM 最大出力トークン数                                            |
| `options.debugOcr`  | bool                     | `false` | `meta.ocrDebugTexts` に生 OCR 候補を含める                        |

**レスポンスボディ**（`SolveResponse`）:

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

Azure Blob Storage の `ocr-debug/ocr_debug.jsonl` から最新 N 件の OCR デバッグログを返します。
Blob が利用できない場合は `/tmp/ocr_debug.jsonl` にフォールバックします。

### GET /v1/ocr-debug/diag

診断用エンドポイント。`/tmp` 書き込み可否、stdout 動作、Azure Blob 接続性を確認します。
デバッグログパイプラインが正常に動作しているかを検証するために有用です。

---

## OCR ソースとスコアリング

ソルバーは複数の OCR 候補テキストを生成し、最高スコアの候補を採用します。

| OCR ソース                 | ボーナス | 説明                                                              |
| -------------------------- | -------: | ----------------------------------------------------------------- |
| `local_reference_pdf`      |    +0.44 | ローカル参照 PDF から抽出したテキスト（最高品質）                 |
| `pdf_direct`               |    +0.34 | URL 経由で取得した PDF から抽出したテキスト                       |
| `gcp_vision_api`           |    +0.30 | Google Cloud Vision API                                           |
| `azure_di_merged`          |    +0.30 | Azure DI 2パスマージ: 日本語テキスト + in-place LaTeX 数式        |
| `gcp_vision_merged`        |    +0.28 | GCP Vision + Gemini Vision の数式マージ                           |
| `azure_di_read+formulas`   |    +0.26 | Azure DI 日本語テキスト + 数式付録（フォールバック）              |
| `azure_di_layout_markdown` |    +0.12 | Azure DI Markdown（LaTeX 精度は高いが日本語を取りこぼす場合あり） |
| `azure_di_read`            |     0.00 | Azure DI プレーンテキスト（数式抽出なし）                         |

選択されたソースは `meta.ocrSource` と `meta.ocrScore` に出力されます。

**品質しきい値**（`config.py`）:

```python
solve_ocr_review_min_score: float = 0.40        # これ未満は要レビューとしてフラグ
solve_ocr_review_max_replacement_ratio: float = 0.01  # 置換文字率 >1% でフラグ
```

---

## 2パス数式マージ（azure_di_merged）

不具合履歴は [AI_AGENT_11_BUG_FIX_REPORTS.md §10](AI_AGENT_11_BUG_FIX_REPORTS.md#10-ocr-formula-merge-bugs-2026-02-27) を参照してください。

```
Pass 1: Y-polygon overlap ≥ 30% → 数式断片をインライン置換
Pass 2: _find_formula_regions() ヒューリスティック → 残り display 数式を対応付け
Safety net: 未対応の display 数式は末尾に [display] として追記
Inline formulas: 常に末尾に [inline] として追記
```

**ヒューリスティックな数式領域検出**（`_find_formula_regions`）:

- 行に CJK 文字が含まれない
- 行長が 80 文字以下
- 強い数式シグナルを少なくとも1つ含む: `[\\∞∫∑∏√]|lim|log|sin|cos|tan` または演算子2連続以上

---

## 環境変数

### Azure Solver（AzureMathSolver）

| 変数                                   | 必須 | 説明                                         |
| -------------------------------------- | ---- | -------------------------------------------- |
| `SOLVE_ENABLED`                        | ✓    | エンドポイント有効化には `true` が必須       |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | ✓    | Azure AI DI endpoint URL                     |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY`      | ✓    | Azure AI DI API key                          |
| `AZURE_OPENAI_ENDPOINT`                | ✓    | Azure OpenAI endpoint URL                    |
| `AZURE_OPENAI_KEY`                     | ✓    | Azure OpenAI API key                         |
| `AZURE_OPENAI_DEPLOYMENT`              |      | LLM デプロイ名（既定: `gpt-4o`）             |
| `AZURE_OPENAI_API_VERSION`             |      | API バージョン（既定: `2024-12-01-preview`） |
| `AZURE_STORAGE_ACCOUNT_NAME`           |      | OCR デバッグログ Blob Storage 用（任意）     |
| `AZURE_STORAGE_ACCOUNT_KEY`            |      | OCR デバッグログ Blob Storage 用（任意）     |

### GCP Solver（GcpMathSolver）

| 変数                  | 必須 | 説明                                          |
| --------------------- | ---- | --------------------------------------------- |
| `SOLVE_ENABLED`       | ✓    | エンドポイント有効化には `true` が必須        |
| `GCP_SERVICE_ACCOUNT` | ✓    | 署名付き URL 生成用サービスアカウントメール   |
| `GCP_VERTEX_LOCATION` |      | Vertex AI リージョン（既定: `us-central1`）   |
| `GCP_VERTEX_MODEL`    |      | Gemini モデル（既定: `gemini-2.0-flash-001`） |
| `GCP_VISION_API_KEY`  |      | Vision API key。未設定時は ADC を使用         |

### コスト制御用変数

| 変数                           | 既定値           | 説明                                                 |
| ------------------------------ | ---------------- | ---------------------------------------------------- |
| `SOLVE_ENABLED`                | `false`          | グローバル kill switch。`false` で全コストを停止     |
| `SOLVE_ALLOW_REMOTE_IMAGE_URL` | `true`           | URL からの画像取得を許可（無効化で SSRF リスク抑制） |
| `SOLVE_MAX_IMAGE_BYTES`        | `5242880` (5 MB) | 最大画像サイズ。超過は 400 で拒否                    |
| `AZURE_OPENAI_DEPLOYMENT`      | `gpt-4o`         | より安価なモデルへ切替可能                           |
| `options.maxTokens`            | `2000`           | リクエストあたりを削減して LLM コスト圧縮            |

---

## 参照 PDF 検索

ソルバーは OCR 品質向上のため、元問題の参照 PDF を任意で取得できます。

**検索順序**（`BaseMathSolver._resolve_reference_pdf_urls`）:

1. ローカルパス（開発時のみ）から `{university}/{year}/{subject}/{questionNo}.pdf`
2. `exam.university`、`exam.year`、`exam.subject`、`exam.questionNo` から導出したリモート URL

参照 PDF は権威ソース OCR 候補（`local_reference_pdf` または `pdf_direct`）として扱われ、最高ボーナス（+0.44 または +0.34）を加算します。

---

## ソースファイル

| ファイル                                         | 説明                                                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `services/api/app/routes/solve.py`               | FastAPI ルーター: `/v1/solve`, `/v1/ocr-debug`, `/v1/ocr-debug/diag`                                   |
| `services/api/app/services/base_math_solver.py`  | 基底クラス: 画像解決、OCR スコアリング、数式マージ、PDF 抽出                                           |
| `services/api/app/services/azure_math_solver.py` | Azure DI + Azure OpenAI 実装                                                                           |
| `services/api/app/services/gcp_math_solver.py`   | GCP Vision + Gemini 実装                                                                               |
| `services/api/app/models.py`                     | `SolveRequest`, `SolveResponse`, `SolveInput`, `SolveExam`, `SolveOptions`, `SolveAnswer`, `SolveMeta` |
| `services/api/app/config.py`                     | `solve_*`, `azure_*`, `gcp_vertex_*` の全設定                                                          |

---

## クイックテスト

```bash
# ローカルで有効化
export SOLVE_ENABLED=true
export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
export AZURE_DOCUMENT_INTELLIGENCE_KEY=...
export AZURE_OPENAI_ENDPOINT=https://...
export AZURE_OPENAI_KEY=...

# 最小 curl リクエスト（画像 URL）
curl -s -X POST http://localhost:8000/v1/solve \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"imageUrl": "https://example.com/problem.jpg", "source": "url"},
    "exam": {"university": "tokyo", "year": 2025, "questionNo": "1"},
    "options": {"mode": "fast", "debugOcr": true}
  }' | python3 -m json.tool

# 最新 OCR デバッグログを確認
curl -s "http://localhost:8000/v1/ocr-debug?limit=5" | python3 -m json.tool

# Staging（Azure）
STAGING_API="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"
curl -s "${STAGING_API}/v1/ocr-debug/diag" | python3 -m json.tool
```

---

## AWS 非対応の理由

`CLOUD_PROVIDER=aws` の場合、`/v1/solve` は **HTTP 501 Not Implemented** を返します。
これは一時的な欠落ではなく、意図的なアーキテクチャ判断です。

### 1. AWS Textract に LaTeX 数式抽出機能がない（最大の障壁）

本サービス OCR パイプラインの核心は、**Azure Document Intelligence `prebuilt-layout` + FORMULAS** による LaTeX 数式の in-place 抽出です。

| 機能                    | Azure DI                                  | AWS Textract                 | 影響                   |
| ----------------------- | ----------------------------------------- | ---------------------------- | ---------------------- |
| 日本語テキスト認識      | ✓ `prebuilt-read`                         | △ 対応はしているが精度が低い | 問題文の誤読           |
| 数式を LaTeX で出力     | ✓ `kind=display/inline` + `value` (LaTeX) | ✗ 対応なし                   | 数式ゼロが極まる       |
| ポリゴン座標付き数式    | ✓ `bounding_regions[0].polygon`           | ✗                            | in-place マージ不可    |
| 日本語 + 数式の同時抽出 | ✓ 2パス並列で両立                         | ✗                            | パイプライン全体が崩壊 |

AWS Textract の Equations 機能（2023年追加）は LaTeX を返さず、数式領域のバウンディングボックスのみを提供するため、本サービスの `_merge_read_with_formulas()` が動作しません。

### 2. API Gateway の 29 秒応答タイムアウト

AWS Lambda 自体の最大実行時間は 15 分ですが、**API Gateway（REST API / HTTP API）の統合タイムアウトは最大 29 秒で変更不可**です。

本サービス `accurate` モードの処理時間目安:

| フェーズ                   | 所要時間目安  |
| -------------------------- | ------------- |
| Azure DI 2パス並列 OCR     | 8〜20 秒      |
| 参照 PDF ダウンロード+抽出 | 3〜10 秒      |
| Azure OpenAI gpt-4o 推論   | 5〜20 秒      |
| **合計（accurate mode）**  | **16〜50 秒** |

`fast` モードでも参照 PDF なしで 15〜30 秒かかる場合があります。
API Gateway 29 秒制限により、**accurate モードは AWS では構造的に実現不可能**です。

> Lambda Function URL を直接使えばタイムアウト回避は可能ですが、本プロジェクトではマルチクラウド構成上 API Gateway を必須インフラとしており、迂回構成は採用しません。

### 3. gpt-4o と Gemini は AWS Bedrock で提供されていない

本サービスで使用している LLM:

| クラウド | LLM                              | 特徴                                     |
| -------- | -------------------------------- | ---------------------------------------- |
| Azure    | Azure OpenAI `gpt-4o`            | 日本語数学記述・LaTeX 出力品質が高水準   |
| GCP      | Vertex AI `gemini-2.0-flash-001` | マルチモーダル（画像入力直接対応）・高速 |

AWS Bedrock が提供するのは Claude、Llama、Mistral、Titan などです。
`gpt-4o` は Microsoft/OpenAI 提供のため AWS Bedrock では利用できません。
`Gemini` シリーズも Google Cloud 提供のため AWS Bedrock では利用できません。

Claude（Bedrock）で代替実装すること自体は可能ですが、評価済みプロンプト・スキーマ（`SolveAnswer.steps`、`SolveAnswer.latex`、`diagramGuide` 等）の再調整が必要で、品質保証の観点から採用していません。

### 4. 設計経緯 — 以前は Bedrock フォールバックがあった

コードコメントにあるとおり、初期設計では `BaseMathSolver` に Bedrock フォールバックが実装されていました:

```python
# services/api/app/services/gcp_math_solver.py (ドキュメントコメント)
# フォールバック設計:
#   - Vision API 未設定 → Bedrock マルチモーダル OCR (親クラス)
#   - Vertex AI 未設定  → Bedrock LLM (親クラス)
```

しかし次の理由で `BaseMathSolver` から削除され、現在は "Shared utilities only — no AWS/Bedrock clients" になっています。

- Textract では数式抽出が機能せず、OCR スコアが常に最低値になる
- API Gateway タイムアウトにより accurate mode が完走しない
- LLM 品質（Claude vs gpt-4o）の差が日本語数学問題で顕著

### 5. まとめ — AWS で solve を動かすために必要な変更

将来 AWS 対応を検討する場合に必要な全体像:

| 課題         | 必要な対応                                                                   |
| ------------ | ---------------------------------------------------------------------------- |
| LaTeX OCR    | Textract の代替として外部 OCR API（例: Mathpix）を統合                       |
| タイムアウト | Lambda Function URL + API Gateway バイパス、または非同期ジョブキュー化       |
| LLM          | Claude Sonnet/Haiku 向けにプロンプト再調整（品質検証が必要）                 |
| 数式マージ   | `_merge_read_with_formulas()` の入力形式変更（ポリゴン付き数式データが必要） |

現状は **対応予定なし**。AWS で数学 OCR が必要な場合は Azure または GCP へルーティングする設計を推奨します。

---

## 既知の制約と今後の改善

| 項目                       | 詳細                                                                   |
| -------------------------- | ---------------------------------------------------------------------- |
| AWS 未対応                 | AWS の `/v1/solve` は 501 を返す。詳細は上記「AWS 非対応の理由」参照   |
| CJK-Latin OCR 混同         | `ェ` が `x` と誤読される。後処理正規化は未対応                         |
| `[display] \quad` の誤検出 | `_has_formula_signal` が広すぎるため、`\quad` のブラックリスト化が必要 |
| 分数 OCR                   | `1/2` → `112` の誤読。構造認識は未実装                                 |
| GCP Vision merged          | `gcp_vision_merged` は新規ソース（2026-02-27）で、大規模検証は未実施   |
| コストトラッキング         | `meta.costUsd` はトークン数ベースの推定値で、実課金値ではない          |

---

_最終更新: 2026-02-27_
