# 06 — Environment Status

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> Last verified: 2026-02-28 Session 3 (Azure OpenAI o3-mini JSON 出力修正完了 ✅ / OCR→LLM パイプライン正常動作 ✅)
> Previous: 2026-02-28 Session 2 (Azure OpenAI 401 修正・mcad-openai-v2 再作成 ✅ / gpt-4o パイプライン HTTP 200 ✅ / o3-mini デプロイ完了 ✅)
> Previous: 2026-02-28 Session 1 (Azure staging AFD 削除後の復旧完了 ✅ / `/exam` 自動作成導入 ✅ / Pulumi 監視アラート修正 ✅)

---

## Session 2026-02-28 (Continuation 3): Azure OpenAI o3-mini JSON 出力修正

### Completed Work

| Task                           | Result                                                                                                                        | Status |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| o3-mini トークン上限バグ修正   | `min(max(2000,512), 8192)=2000` になっていた問題を修正。推論モデルは `max(request.options.max_tokens, 8192)` で最低 8192 保証 | ✅     |
| o3-mini `response_format` 追加 | `is_reasoning_model=True` 時も `response_format={"type":"json_object"}` を設定                                                | ✅     |
| Docker ビルド & デプロイ       | Python 3.11-slim Docker ビルド (18MB) → Azure Function App デプロイ                                                           | ✅     |
| 動作検証                       | HTTP 200 / `final: '(1) Uₜ = ..., (2) 面積 = 3/5, ...'` / `steps: 4` / `confidence: 0.9`                                      | ✅     |

### 修正内容詳細 (`services/api/app/services/azure_math_solver.py`)

**バグ1: トークン上限の誤算**

```python
# 修正前 (バグ): min(max(2000, 512), 8192) = 2000 になる
_token_limit = min(
    max(request.options.max_tokens, 512),
    8192 if (is_accurate or is_reasoning_model) else 2000,
)

# 修正後: 推論モデルは常に min(8192, ...) でなく max(8192, user_max) を保証
if is_reasoning_model:
    _token_limit = max(request.options.max_tokens, 8192)
else:
    _token_limit = min(
        max(request.options.max_tokens, 512),
        8192 if is_accurate else 2000,
    )
```

**バグ2: `response_format` 未設定**

```python
# 修正前: is_reasoning_model 時は response_format なし → 自由テキスト返却 → JSON パース失敗
if is_reasoning_model:
    create_kwargs["temperature"] = 1
else:
    create_kwargs["temperature"] = 0.0
    create_kwargs["response_format"] = {"type": "json_object"}

# 修正後: 推論モデルにも response_format を付与
if is_reasoning_model:
    create_kwargs["temperature"] = 1
    create_kwargs["response_format"] = {"type": "json_object"}  # Azure o3-mini 対応
else:
    create_kwargs["temperature"] = 0.0
    create_kwargs["response_format"] = {"type": "json_object"}
```

### 修正後の動作確認結果

```
HTTP: 200
status: completed
model: azure_openai/o3-mini
latency: ~20 秒
final: '(1) Uₜ = (t²(3-2t), 3t(1-t)), (2) 面積 = 3/5, (3) 弧長 = 2a³ - 3a² + 3a.'
steps count: 4
confidence: 0.9
```

---

## Session 2026-02-28 (Continuation 2): Azure OpenAI 認証修正 & o3-mini 移行

### Completed Work

| Task                                   | Result                                                                                                                             | Status |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Azure OpenAI 401 根本原因特定          | `mcad-openai-cea07c11` が `--custom-domain` なしで作成 → 共有エンドポイント `japaneast.api.cognitive.microsoft.com` → API キー不可 | ✅     |
| `mcad-openai-v2` 再作成                | `--custom-domain mcad-openai-v2` 付きで作成 → `https://mcad-openai-v2.openai.azure.com/`                                           | ✅     |
| gpt-4o デプロイ & 検証                 | `gpt-4o` (2024-11-20) デプロイ / HTTP 200 / latency 23秒                                                                           | ✅     |
| o3-mini デプロイ                       | `mcad-openai-v2` に `o3-mini` デプロイ                                                                                             | ✅     |
| Function App 環境変数更新              | `AZURE_OPENAI_ACCURATE_DEPLOYMENT=o3-mini` 設定                                                                                    | ✅     |
| `extra_body` 削除                      | `{"reasoning_effort":"medium"}` は Azure OpenAI 非対応 → 削除                                                                      | ✅     |
| `reasoning_content` フォールバック追加 | `message.content` が None の場合に `reasoning_content` を参照するよう修正                                                          | ✅     |

### Azure OpenAI リソース変更履歴

| リソース               | 状態        | エンドポイント                                   | 問題                                                       |
| ---------------------- | ----------- | ------------------------------------------------ | ---------------------------------------------------------- |
| `mcad-openai-cea07c11` | ❌ 削除済み | `https://japaneast.api.cognitive.microsoft.com/` | `--custom-domain` なし → 共有エンドポイント → API キー無効 |
| `mcad-openai-v2`       | ✅ 使用中   | `https://mcad-openai-v2.openai.azure.com/`       | 正常                                                       |

### 現在の環境変数 (staging Function App)

| 変数                               | 値                                         |
| ---------------------------------- | ------------------------------------------ |
| `AZURE_OPENAI_ENDPOINT`            | `https://mcad-openai-v2.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT`          | `gpt-4o`                                   |
| `AZURE_OPENAI_ACCURATE_DEPLOYMENT` | `o3-mini`                                  |
| `AZURE_OPENAI_API_VERSION`         | `2024-12-01-preview`                       |

### o3-mini 対応で判明した仕様

| 項目                          | gpt-4o            | o3-mini (Azure)                         |
| ----------------------------- | ----------------- | --------------------------------------- |
| `temperature`                 | 0.0〜2.0 自由設定 | 1 固定                                  |
| `max_tokens`                  | ✅                | ❌ → `max_completion_tokens`            |
| `response_format`             | ✅ json_object    | ✅ json_object                          |
| `extra_body.reasoning_effort` | N/A               | ❌ Azure 非対応                         |
| 推論トークン消費              | なし              | 推論に内部トークン消費 → 最低 8192 必要 |

---

## Session 2026-02-28 (Continuation 1): Azure Staging Reset After AFD Removal

### Completed Work

| Task                                  | Result                                                                                         | Status |
| ------------------------------------- | ---------------------------------------------------------------------------------------------- | ------ |
| Confirm staging AFD removal           | Azure Front Door for staging is removed; production AFD remains active                         | ✅     |
| Recover exam entry URL                | Added static website shortcut `/exam/index.html` as copy of `/sns/index.html`                  | ✅     |
| Automate shortcut creation in CI/CD   | Added `Create /exam shortcut` step to `deploy-azure.yml`                                       | ✅     |
| Fix Pulumi failure after AFD deletion | Updated Azure monitoring to skip Front Door metric alerts when `frontdoor_profile_id` is unset | ✅     |
| Validate end-to-end deployment        | GitHub Actions run succeeded; `/exam` returns 200 and serves React SPA                         | ✅     |

### Azure Staging Notes (2026-02-28)

- Staging frontend now runs directly on Azure Storage Static Website (no Front Door layer).
- `/exam` is supported without CDN rules by copying `/sns/index.html` to `/exam/index.html`.
- `Create /exam shortcut` runs on each Azure deploy to keep exam entry path in sync.
- Monitoring no longer attempts to create/update Front Door alerts when CDN is disabled.

---

## Session 2026-02-27 (Continuation 4): Architecture Diagram Icon Enhancement

### Completed Work

| Task                                         | Result                                                                | Status |
| -------------------------------------------- | --------------------------------------------------------------------- | ------ |
| **デュアルアイコン配置実装**                 | ノード左上（24px）+ テキスト横（20px）の2箇所にアイコン表示           | ✅     |
| **generate_icon_diagram.py JavaScript 更新** | foreignObject / text要素の両方に対応するスマート検出ロジック実装      | ✅     |
| **3環境HTML再生成**                          | staging/production/combined の3ファイル全て再生成（78KB, 78KB, 84KB） | ✅     |
| **CLOUD_ARCHITECTURE_MAPPER.md 更新**        | Features / Technical Details / Known Limitations セクション更新       | ✅     |
| **CHANGELOG.md 更新**                        | 2026-02-27 エントリに詳細な実装内容とファイルサイズ更新               | ✅     |
| **README.md アーキテクチャリンク追加**       | インタラクティブHTML図への直接リンク追加済み                          | ✅     |

### Technical Implementation Details

**Icon Placement Strategy**:

1. **Top-left corner icon** (24x24px):
   - Position: (rect.x + 6, rect.y + 6)
   - Purpose: Quick visual resource type identification
   - Always visible regardless of node size

2. **Text-inline icon** (20x20px):
   - Position: 4px left of node label text
   - Purpose: Enhanced readability with text association
   - Smart detection: Handles both `foreignObject` and native SVG `text`/`tspan` elements

**JavaScript DOM Manipulation**:

```javascript
// 1. Top-left corner
const topIcon = createSVGImage(iconUrl, rectX + 6, rectY + 6, 24, 24);
node.appendChild(topIcon);

// 2. Text-inline (foreignObject vs text element detection)
if (textElement.tagName === "foreignObject") {
  textX = parseFloat(textElement.getAttribute("x") || 0);
  textY =
    parseFloat(textElement.getAttribute("y") || 0) + height / 2 - iconSize / 2;
} else {
  const tspan = textElement.querySelector("tspan");
  textX = parseFloat((tspan || textElement).getAttribute("x") || 0);
  textY =
    parseFloat((tspan || textElement).getAttribute("y") || 0) - iconSize / 2;
}
const textIcon = createSVGImage(iconUrl, textX - 24, textY, 20, 20);
labelGroup.insertBefore(textIcon, labelGroup.firstChild);
```

### Generated Files

| File                           | Size | Icons                         | Description                            |
| ------------------------------ | ---- | ----------------------------- | -------------------------------------- |
| `architecture.staging.html`    | 78KB | AWS (5) + Azure (4) + GCP (5) | Staging環境（デュアルアイコン配置）    |
| `architecture.production.html` | 78KB | AWS (5) + Azure (4) + GCP (5) | Production環境（デュアルアイコン配置） |
| `architecture-combined.html`   | 84KB | AWS (5) + Azure (4) + GCP (5) | 統合ビュー（color-coded nodes）        |

**Icon Sources**:

- AWS: 14KB (cloudfront, lambda, s3, dynamodb, api-gateway)
- Azure: 16KB (cdn, function, storage, cosmos-db)
- GCP: 20KB (cdn, run, storage, firestore, load-balancer)
- **Total embedded assets**: ~50KB Base64-encoded SVG data URIs

### Documentation Updates

✅ **CLOUD_ARCHITECTURE_MAPPER.md**:

- Features section: Added "Dual icon placement" bullet point
- Technical Details: Expanded JavaScript code samples with dual placement logic
- Known Limitations: Added text-inline positioning variance note

✅ **CHANGELOG.md**:

- Updated 2026-02-27 entry with detailed implementation notes
- Added file size changes (85KB → 78KB for staging/production)
- Documented dual icon placement strategy

✅ **README.md**:

- Architecture section now links to all 3 interactive HTML diagrams
- Added visual indicators (📊) for diagram links

---

## Session 2026-02-27 (Continuation 3): Security Deployment & Documentation Update

### Completed Work

| Task                                       | Result                                                                                               | Status |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ------ |
| S1: GCP staging pulumi up                  | HTTPS redirect / Audit logs 反映済み（33 unchanged）                                                 | ✅     |
| S1: AWS production pulumi up               | CloudTrail / CORS 反映済み（40 unchanged）                                                           | ✅     |
| S1: GCP production refresh+up              | State drift 解決後、Audit logs 反映済み（34 unchanged）                                              | ✅     |
| S1: Azure staging pulumi up                | Key Vault purge protection 反映（1 updated, 32 unchanged）                                           | ✅     |
| S1: Azure production pulumi up             | Key Vault purge protection 本番反映済み（33 unchanged）                                              | ✅     |
| **S2: Function App Managed Identity**      | staging/production 両方に SystemAssigned MSI 割り当て成功                                            | ✅     |
| **Task 13: Update README**                 | エンドポイント・セキュリティ実装・テスト結果・デプロイ状況を最新情報に更新                           | ✅     |
| Task 20/21 補完: Key Vault 診断設定（CLI） | `az monitor diagnostic-settings create` で Log Analytics との統合が完了（AuditEvent ストリーミング） | ✅     |

### Production Endpoints (As of 2026-02-27)

| Cloud     | CDN / Frontend                                                                   | API                                                                                                             | Status        |
| --------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------- |
| **AWS**   | [CloudFront](https://d1qob7569mn5nw.cloudfront.net) ✅                           | [API Gateway](https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com)                                      | ✅ 本番運用中 |
| **Azure** | [Front Door](https://mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net) ✅ | [Functions](https://multicloud-auto-deploy-production-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api) | ✅ 本番運用中 |
| **GCP**   | [CDN（www.gcp.ashnova.jp）](https://www.gcp.ashnova.jp) ✅                       | [Cloud Functions](https://multicloud-auto-deploy-production-api-***-an.a.run.app)                               | ✅ 本番運用中 |

### Security Implementation Status (Deployed to Production)

| Measure                    | AWS | Azure               | GCP | Status                |
| -------------------------- | --- | ------------------- | --- | --------------------- |
| CORS 絞り込み              | ✅  | ✅                  | ✅  | ✅ 本番反映           |
| CloudTrail / Audit Logs    | ✅  | ✅                  | ✅  | ✅ 本番反映           |
| Key Vault Purge Protection | —   | ✅                  | —   | ✅ 本番反映           |
| Key Vault 診断ログ         | —   | ✅（Log Analytics） | —   | ✅ 本番反映           |
| Managed Identity           | —   | ✅                  | —   | ✅ staging/production |
| HTTPS Redirect             | —   | —                   | ✅  | ✅ 本番反映           |
| Cloud Armor                | —   | —                   | ✅  | ✅ 本番反映           |

---

## Session 2026-02-27: GCP Audit Logs & Billing Budget Remediation

### Completed Work

| Task                                          | Result                                                                                                                                                 | Status |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| GCP audit logs re-enable (IAMAuditConfig)     | staging/production で Cloud Audit Logs (`allServices`) を有効化。Pulumi リソース作成完了                                                               | ✅     |
| ADC (Application Default Credentials) refresh | `gcloud auth application-default login` で sat0sh1kawada00@gmail.com 再認証。quota project=ashnova に設定                                              | ✅     |
| GCP billing account config                    | Pulumi設定に `billingAccountId: 01F139-282A95-9BBA25` を追加                                                                                           | ✅     |
| Billing budget error mitigation               | ADC quota project エラー回避。monitoring.py で `billing_account_id` をoptional パラメータ化。コードで `enable_billing_budget=False` にデフォルト無効化 | ✅     |
| GCP side budget cleanup                       | `gcloud billing budgets delete` で古いbudgetリソース削除                                                                                               | ✅     |
| monitoring.py refactor                        | `create_billing_budget()` に `billing_account_id` 追加。`setup_monitoring()` で `billing_budget=None` when not enabled                                 | ✅     |

### Code Changes

- **infrastructure/pulumi/gcp/**main**.py**: `enable_billing_budget = False` (hardcoded disable) + `billing_account_id=None` を常時 monitoring へ参照
- **infrastructure/pulumi/gcp/monitoring.py**: `billing_account_id` パラメータ追加、optional化。budget作成条件を `if stack=="production" and billing_account_id:` に変更

### Known Issues / Next Steps

- GCP production `pulumi up` が preview conflict 状態。コード修正後は再実行予定（次セッション）
- staging/production 共にaudit logs有効化完了、billing warning 回避完了
- billingbudgets API 認証エラーは ADC quotaProjectで解消するが、service account接続時の権限不足で deprecated。本番運用では GCP service account 設定または ignore_changes で対応推奨

---

## Staging Environment Summary

| Cloud     | Landing (`/`) | SNS App (`/sns/`) | API                                       |
| --------- | ------------- | ----------------- | ----------------------------------------- |
| **GCP**   | ✅            | ✅                | ✅ Cloud Run + Firebase Auth (2026-02-24) |
| **AWS**   | ✅            | ✅                | ✅ Lambda (fully operational, 2026-02-24) |
| **Azure** | ✅            | ✅                | ✅ Azure Functions FC1 (2026-02-24)       |

---

## AWS (ap-northeast-1)

```
CDN URL  : https://d1tf3uumcm4bo1.cloudfront.net
API URL  : https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
```

| Resource              | Name / ID                                                                  | Status |
| --------------------- | -------------------------------------------------------------------------- | ------ |
| CloudFront            | `E1TBH4R432SZBZ` (PriceClass_200: NA/EU/JP/KR/IN)                          | ✅     |
| CloudFront RHP        | `multicloud-auto-deploy-staging-security-headers` (HSTS + CSP + 4 headers) | ✅     |
| S3 (frontend)         | `multicloud-auto-deploy-staging-frontend`                                  | ✅     |
| S3 (images)           | `multicloud-auto-deploy-staging-images` (CORS: \*)                         | ✅     |
| Lambda (API)          | `multicloud-auto-deploy-staging-api` (Python 3.12, **1769MB** = 1 vCPU)    | ✅     |
| Lambda (frontend-web) | `multicloud-auto-deploy-staging-frontend-web` (512MB, 30s)                 | ✅     |
| API Gateway           | `z42qmqdqac` (HTTP API v2)                                                 | ✅     |
| DynamoDB              | `multicloud-auto-deploy-staging-posts` (PAY_PER_REQUEST)                   | ✅     |
| Cognito               | Pool `ap-northeast-1_AoDxOvCib` / Client `1k41lqkds4oah55ns8iod30dv2`      | ✅     |
| WAF                   | WebACL attached to CloudFront                                              | ✅     |

**Confirmed working (verified 2026-02-22)**:

- Cognito login → `/sns/auth/callback` → session cookie set ✅
- Post feed, create post with up to 10 images ✅
- Images display correctly (S3 presigned GET URLs, 1-hour expiry) ✅
- `GET /posts/{post_id}` individual post view ✅
- Profile page (nickname, avatar, bio) ✅
- Nickname stored and displayed in post list ✅
- Image upload: S3 presigned URLs, limit enforced server-side via `MAX_IMAGES_PER_POST` ✅
- `GET /limits` endpoint (no auth) returns `{"maxImagesPerPost": 10}` ✅
- Logout → Cognito-hosted logout → redirect back to `/sns/` ✅
- CI/CD pipeline: env vars set correctly on every push ✅
- Frontend bundle built with `VITE_BASE_PATH=/sns/` — asset paths correct ✅
- CloudFront custom error pages: `/sns/index.html` (403+404) ✅
- CloudFront Response Headers Policy: HSTS/CSP(`upgrade-insecure-requests`)/X-Content-Type-Options/X-Frame-Options/Referrer-Policy/XSS-Protection ✅ (2026-02-23)
- CloudFront PriceClass_200: 日本・韓国・インドのエッジを使用 ✅ (旧: PriceClass_100 = 米国/欧州のみ)
- OAuth フロー PKCE (S256) 実装: `response_type=code` + code_verifier/challenge ✅ (2026-02-23)
- Cognito `implicit` フロー削除: `allowed_oauth_flows=["code"]` のみ ✅ (2026-02-23)
- S3 パブリックアクセス完全遮断: `BlockPublicAcls/IgnorePublicAcls/BlockPublicPolicy/RestrictPublicBuckets=True` ✅ (2026-02-23)
- S3 バケットポリシー OAI 専用: `Principal:*` 削除 ✅ (2026-02-23)
- Lambda `_resolve_image_urls`: `http://` URL をスキップして Mixed Content を防止 ✅ (2026-02-23)

**Current frontend bundle**: `index-B0gzRu__.js` (uploaded 2026-02-23, PKCE対応)

**Build command for AWS staging**:

```bash
cd services/frontend_react
set -a && source .env.aws.staging && set +a
VITE_BASE_PATH=/sns/ npm run build
```

**Known limitations**:

- Production stack shares staging resources (independent prod stack not yet deployed).
- WAF rule set not tuned.
- `DELETE /posts` may fail on SNS Unsubscribe call (not tested in this session).

---

## Azure (japaneast)

```
Frontend URL : https://mcadwebd45ihd.z11.web.core.windows.net
Exam URL     : https://mcadwebd45ihd.z11.web.core.windows.net/exam
API URL      : https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net
```

| Resource        | Name                                                                | Status |
| --------------- | ------------------------------------------------------------------- | ------ |
| Front Door      | staging AFD removed (cost optimization)                             | ✅     |
| Storage Account | `mcadwebd45ihd`                                                     | ✅     |
| Function App    | `multicloud-auto-deploy-staging-func` (Python 3.12, always-ready=1) | ✅     |
| Cosmos DB       | `simple-sns-cosmos` (Serverless)                                    | ✅     |
| Resource Group  | `multicloud-auto-deploy-staging-rg`                                 | ✅     |

**Configured (2026-02-23)**:

- FlexConsumption always-ready instances: `http=1` → コールドスタート解消 ✅

**Unresolved issues**:

- End-to-end verification of `PUT /posts/{id}` is incomplete.
- Some test scripts still default `AZURE_FD_URL` to legacy staging AFD; override to Storage URL when running old scripts.

---

## GCP (asia-northeast1)

```
CDN URL : http://34.117.111.182
API URL : https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app
```

| Resource              | Name / ID                                                      | Status |
| --------------------- | -------------------------------------------------------------- | ------ |
| Global IP             | `34.117.111.182`                                               | ✅     |
| GCS Bucket (frontend) | `ashnova-multicloud-auto-deploy-staging-frontend`              | ✅     |
| GCS Bucket (uploads)  | `ashnova-multicloud-auto-deploy-staging-uploads` (public read) | ✅     |
| Cloud Run (API)       | `multicloud-auto-deploy-staging-api` (Python 3.12, **min=1**)  | ✅     |
| Firestore             | `(default)` — collections: messages, posts                     | ✅     |
| Backend Bucket        | `multicloud-auto-deploy-staging-cdn-backend`                   | ✅     |

**Confirmed working (verified 2026-02-21)**:

- Firebase Google Sign-In → `/sns/auth/callback` → httponly Cookie session ✅
- Post feed, create/edit/delete post ✅
- Image upload: GCS presigned URLs (signed via IAM `signBlob` API), up to 16 files per post ✅
- Uploaded images displayed in post feed ✅
- Firebase ID token auto-refresh (`onIdTokenChanged`) ✅
- Dark theme background SVGs (starfield, ring) rendered correctly ✅

**Fixed issues (2026-02-21)**:

- `GcpBackend` had unimplemented `like_post`/`unlike_post` abstract methods → `TypeError` → `/posts` returned 500
  → Added stub implementations for `like_post`/`unlike_post` (commit `a9bc85e`)
- `frontend-web` Cloud Run `API_BASE_URL` was unset → falling back to localhost:8000
  → Set environment variable via `gcloud run services update`
- Firebase Auth not implemented → Implemented the full Google Sign-In flow (commit `3813577`)
- `x-ms-blob-type` header not registered in GCS CORS → Updated CORS + fixed uploads.js (commits `1cf53b7`, `b5b4de5`)
- GCS presigned URL generation had `content_type` hardcoded as `"image/jpeg"` → Now uses `content_types[index]` correctly (commit `148b7b5`)
- Firebase ID token expiry (401) → Auto-refresh via `onIdTokenChanged` (commit `8110d20`)
- `GCP_SERVICE_ACCOUNT` env var missing in CI/CD → Added to `deploy-gcp.yml` (commit `27b10cc`)
- CSS background SVGs used absolute path `/static/` → Changed to relative path `./` (commit `0ed0805`)
- GCS uploads bucket was private → Granted `allUsers:objectViewer` + added IAMBinding to Pulumi definition (commit `0ed0805`)

**Configured (2026-02-23)**:

- Cloud Run `--min-instances=1` → コールドスタート（最大5秒）解消 ✅
- `gcp_backend.py`: `google.auth.default()` を `__init__()` でキャッシュ → リクエストごとのメタデータサーバー呼び出し排除 ✅

**Remaining issues**:

- HTTPS not configured for CDN (HTTP only). Requires `TargetHttpsProxy` + managed SSL certificate.
- SPA deep links via CDN return HTTP 404 (Cloud Run URL works correctly in browsers).

---

## Quick Connectivity Check Commands

```bash
# GCP
curl -s http://34.117.111.182/ | head -3
curl -s https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app/health

# AWS
curl -I https://d1tf3uumcm4bo1.cloudfront.net/
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/health

# Azure
curl -I https://mcadwebd45ihd.z11.web.core.windows.net/sns/
curl -I https://mcadwebd45ihd.z11.web.core.windows.net/exam
curl -s "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/v1/health"
```

---

## Production Environment

> Production has its own independent Pulumi stack (deployed). Resources are separate from staging.
> Frontend is served as **React SPA** (Vite build) from object storage via CDN — `frontend_web` (Python SSR) is no longer used in production.
> Full migration report: [REACT_SPA_MIGRATION_REPORT.md](REACT_SPA_MIGRATION_REPORT.md)

### Production Status Summary (2026-02-23)

| Cloud     | CDN Landing (`/`)                 | SNS App (`/sns/`) | API                                                                      |
| --------- | --------------------------------- | ----------------- | ------------------------------------------------------------------------ |
| **AWS**   | ✅ HTTP 200, 4737 bytes (Ashnova) | ✅ React SPA      | ✅ `/health` ok, `/limits` ok, `/posts` ok                               |
| **Azure** | ✅ HTTP 200, 4608 bytes (Ashnova) | ✅ React SPA      | ✅ `/api/health` ok, `/api/limits` ok, `/api/posts` ok (修復 2026-02-24) |
| **GCP**   | ✅ HTTP 200, 4737 bytes (Ashnova) | ✅ React SPA      | ✅ `/health` ok, `/limits` ok (修復 2026-02-24, revision 00013-big)      |

**Landing page test (2026-02-23)**: `test-landing-pages.sh --env production` → **37/37 PASS (100%)** ✅

### Production Endpoints

| Cloud     | CDN / Endpoint                                            | API Endpoint                                                                                     | Distribution ID        |
| --------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------- |
| **AWS**   | `d1qob7569mn5nw.cloudfront.net` / `www.aws.ashnova.jp`    | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`                                    | E214XONKTXJEJD         |
| **Azure** | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | `https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net` | mcad-production-diev0w |
| **GCP**   | `www.gcp.ashnova.jp`                                      | `https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app`                          | -                      |

**AWS Production SNS App** (`https://www.aws.ashnova.jp/sns/`):

| Item             | Value                                                                      |
| ---------------- | -------------------------------------------------------------------------- |
| Frontend         | React SPA — S3 `multicloud-auto-deploy-production-frontend/sns/`           |
| CF Function      | `spa-sns-rewrite-production` (LIVE) — rewrites `/sns/` → `/sns/index.html` |
| Lambda (API)     | `multicloud-auto-deploy-production-api`                                    |
| API_BASE_URL     | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`              |
| Cognito Pool     | `ap-northeast-1_50La963P2`                                                 |
| Cognito Client   | `4h3b285v1a9746sqhukk5k3a7i`                                               |
| Cognito Redirect | `https://www.aws.ashnova.jp/sns/auth/callback`                             |
| DynamoDB         | `multicloud-auto-deploy-production-posts`                                  |

### Custom Domain Status (ashnova.jp) — 2026-02-21

| Cloud     | URL                          | Status                                                                                                                                                   |
| --------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AWS**   | https://www.aws.ashnova.jp   | ✅ **Fully operational** (HTTP/2 200, ACM cert `914b86b1` + CloudFront alias set directly — details: [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)) |
| **Azure** | https://www.azure.ashnova.jp | ✅ **Fully operational** (HTTPS 200, DigiCert/GeoTrust managed cert, AFD route active)                                                                   |
| **GCP**   | https://www.gcp.ashnova.jp   | ✅ **Fully operational** (HTTPS 200, TLS cert `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` — Pulumi管理, ACTIVE)                                |

#### Completed Work (2026-02-21)

| Cloud | Work                                                                                | Result                                                                                                                                                                                                  |
| ----- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS   | ACM certificate verification                                                        | ✅ Confirmed cert `914b86b1` for `www.aws.ashnova.jp` (expires 2027-03-12) ISSUED                                                                                                                       |
| AWS   | Set alias + ACM cert directly via `aws cloudfront update-distribution` (2026-02-21) | ✅ Set alias `www.aws.ashnova.jp` + cert `914b86b1` on Distribution `E214XONKTXJEJD` → resolved `NET::ERR_CERT_COMMON_NAME_INVALID` → HTTP/2 200 operational                                            |
| AWS   | Fix Production `frontend-web` Lambda environment variables (2026-02-21)             | ✅ Fixed `API_BASE_URL` empty→`localhost:8000` fallback (cause: `deploy-frontend-web-aws.yml` depended on secrets; production secrets not set) → updated CI/CD to use Pulumi outputs (commit `fd1f422`) |
| Azure | `az afd custom-domain create` + route attach                                        | ✅ DNS Approved → Managed Cert Succeeded (GeoTrust, 2026-02-21 – 2026-08-21)                                                                                                                            |
| Azure | AFD route disable→enable toggle                                                     | ✅ Triggered deployment to edge nodes → HTTPS 200 operational                                                                                                                                           |
| Azure | `az afd custom-domain update` (cert edge deploy)                                    | ✅ `CN=www.azure.ashnova.jp` cert distributed to AFD POP                                                                                                                                                |
| Azure | Set `frontend-web` Function App environment variables                               | ✅ API_BASE_URL, AUTH_PROVIDER, AZURE_TENANT_ID, AZURE_CLIENT_ID, etc. configured                                                                                                                       |
| Azure | Add Azure AD app redirect URI                                                       | ✅ Added `https://www.azure.ashnova.jp/sns/auth/callback`                                                                                                                                               |
| GCP   | `pulumi up --stack production` (SSL cert creation)                                  | ✅ cert `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` PROVISIONING                                                                                                                              |
| GCP   | Add ACTIVE cert `ashnova-production-cert-c41311`                                    | ✅ Added to HTTPS proxy → `https://www.gcp.ashnova.jp` HTTPS operational immediately                                                                                                                    |
| GCP   | Update Firebase authorized domains                                                  | ✅ Added `www.gcp.ashnova.jp` to Firebase Auth authorized domains                                                                                                                                       |

#### Remaining Work

- **GCP**: ✅ `ashnova-production-cert-c41311` を HTTPS プロキシから切り離し・削除済み (2026-02-24)。`multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` のみ使用中。

---

### ✅ Production Issues — 全件解決済み (2026-02-24 v5)

#### ✅ 6. Azure プロフィール画面 CORS エラー — RESOLVED 2026-02-24

**症状**: `https://www.azure.ashnova.jp/sns/profile` でプロフィール取得時に CORS エラー発生。

**根本原因**:

1. Azure Function App は Kestrel がプラットフォームレベル CORS 判定を FastAPI `CORSMiddleware` の手前に行う
2. `deploy-azure.yml` が `AZURE_CUSTOM_DOMAIN` シークレット (`staging.azure.ashnova.jp`) を使用してアプリ設定と platform CORS を構築
3. その結果 `CORS_ORIGINS` アプリ設定とプラットフォーム CORS allowedOrigins の両方に `https://www.azure.ashnova.jp` が欠落
4. OPTIONS プリフライトが 204 で返るが `Access-Control-Allow-Origin` ヘッダーなし → ブラウザが CORS エラーを報告

**確認 (GCP)**: GCP は `CORS_ORIGINS` に `https://www.gcp.ashnova.jp` が含まれており問題なし ✅

**即時修正**:

- `az functionapp config appsettings set ... CORS_ORIGINS=https://mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net,https://www.azure.ashnova.jp,http://localhost:5173` ✅
- `az functionapp cors add --allowed-origins "https://www.azure.ashnova.jp"` ✅
- 確認: OPTIONS `/api/profile` → `Access-Control-Allow-Origin: https://www.azure.ashnova.jp` ✅

**根本修正 (v1.17.15)**:

- `infrastructure/pulumi/azure/Pulumi.production.yaml`: `customDomain: www.azure.ashnova.jp` を追加
- `deploy-azure.yml` CORS 構築: シークレットではなく `Pulumi.${STACK_NAME}.yaml` から `customDomain` を読み取るよう変更
- `deploy-azure.yml`: "Ensure Azure CORS Origins" 安全ネットステップを追加 (AWS パターンと同様)

#### ✅ 7. Azure ログイン後に staging SNS に遷移 — RESOLVED 2026-02-24

**症状**: `https://www.azure.ashnova.jp/sns/` でログインすると `staging.azure.ashnova.jp/sns/` にリダイレクトされる。

**根本原因**:

1. フロントエンドバンドル `index-D7IfXIdg.js` が `VITE_AZURE_REDIRECT_URI=https://staging.azure.ashnova.jp/sns/auth/callback` でビルドされていた
2. "Build and Deploy Frontend" ステップが `AZURE_CUSTOM_DOMAIN="${{ secrets.AZURE_CUSTOM_DOMAIN }}"` (= `staging.azure.ashnova.jp`) を使用
3. 同様に Azure AD アプリの redirect URIs にも `www.azure.ashnova.jp` がなく `staging.azure.ashnova.jp` のみだった

**即時修正**:

- `az ad app update --id "0b926ff6-fc03-4c9c-a359-96964ef15941" --web-redirect-uris` で `www.azure.ashnova.jp` を追加 ✅
- フロントエンドを `VITE_AZURE_REDIRECT_URI=https://www.azure.ashnova.jp/sns/auth/callback` で再ビルド → `index-CPcQQsCR.js` ✅
- Blob Storage `mcadwebdiev0w/$web/sns/` にアップロード ✅
- 確認: `curl www.azure.ashnova.jp/sns/` → `index-CPcQQsCR.js` を配信 ✅

**根本修正 (v1.17.16)**:

- `deploy-azure.yml`: "Build and Deploy Frontend"、"Update Azure AD App Redirect URIs"、"Link Custom Domain to Front Door Route"、"Blob Storage CORS" の全4箇所の `${{ secrets.AZURE_CUSTOM_DOMAIN }}` を stack 名マッピング (`production`→`www.azure.ashnova.jp`) に変更

---

#### ✅ 1. Azure Function App — 0 registered functions (API 404) — RESOLVED 2026-02-24

**症状**: `https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api/HttpTrigger/health` → HTTP 404

**確認事項**:

- Host状態: Running ✅ (`v4.1046.100`, uptime: 805719ms)
- Admin `/admin/functions` → `[]` (0件) ❌ → 関数コードが読み込まれていない
- `AzureWebJobsStorage` → `AccountName=mcadfuncdiev0w` ✅ (修正済み)
- `DEPLOYMENT_STORAGE_CONNECTION_STRING` → `AccountName=mcadfuncdiev0w` ✅ (修正済み)

**根本原因 (推定)**:

- 過去に非存在ストレージ `multicloudautodeploa148` が設定されていた
- Kudu RemoteBuild モードでは validation check として blob upload を試みる → NXDOMAIN で失敗
- デプロイが繰り返し失敗したため、wwwroot に有効なコードが存在しない
- Deploy Function App ステップで `az webapp restart` 後も古いコード（または無コード）状態が継続

**修正済み内容**:

- `deploy-azure.yml` へ "Storage fix before zip deploy" ステップを追加 (v1.17.6)
  - `az storage account show-connection-string` で `mcadfuncdiev0w` の接続文字列を取得
  - zip deploy 前に `AzureWebJobsStorage` と `DEPLOYMENT_STORAGE_CONNECTION_STRING` を更新
- 最新デプロイ (run 22310372431) では "Deploy Function App" が ✅ 成功
- しかし "Verify Deployment" (health check 180秒) が ❌ タイムアウト → 関数がロードされていない

**解決経緯 (2026-02-24 セッション v3):**

多層的な根本原因を特定・修正:

1. **Layer 1** (v1.17.6で修正済み): `AzureWebJobsStorage` / `DEPLOYMENT_STORAGE_CONNECTION_STRING` が非存在ストレージ `multicloudautodeploa148` を指していた
2. **Layer 2** (セッションv2で修正): `functionAppConfig.deployment.storage.value` が `multicloudautodeploa148.blob.core.windows.net/app-package-...a4038fa` を指していた → Kudu ValidationStep `StorageAccessibleCheck` が NXDOMAIN で失敗 → Python urllib で PATCH して `mcadfuncdiev0w.blob.core.windows.net/app-package-...a4038fa` に修正
3. **Layer 3 (根本原因)**: `functionAppConfig.runtime.version = "3.12"` (Python 3.12) だが、デプロイ試行に使用していた `function-app-amd64.zip` は Python 3.11 (`cpython-311-x86_64`) でビルドされたパッケージを使用 → Python バージョン不一致でモジュールロード失敗 → `admin/functions = []`
4. **Layer 4**: コンテナ名不一致: `app-package-multicloudautodeployproductionfr-8540439`（実際の active コンテナ、旧 frontend_web コードを保持）と `functionAppConfig.deployment.storage.value` が指す `app-package-...a4038fa`（空）が別コンテナ

**最終修正 (2026-02-24)**:

```bash
# Python 3.13 / linux/amd64 でパッケージをビルド
docker run --rm --platform linux/amd64 -v "$(pwd):/work" python:3.13-slim \
  pip install --target /work/.deployment-py313 --no-cache-dir -q -r /work/requirements-azure.txt
# アプリコードをコピーしてzip作成
cd .deployment-py313 && zip -r9 -q ../function-app-py313.zip .
# デプロイ
az functionapp deployment source config-zip \
  --resource-group multicloud-auto-deploy-production-rg \
  --name multicloud-auto-deploy-production-func \
  --src services/api/function-app-py313.zip \
  --build-remote false --timeout 180
```

**修復後の状態**:

- `admin/functions` → `[{"name":"HttpTrigger",...}]` ✅
- `/api/health` → `{"status":"ok","provider":"azure","version":"3.0.0"}` HTTP 200 ✅
- `/api/limits` → `{"maxImagesPerPost":10}` HTTP 200 ✅
- `/api/posts` → `{"items":[],...}` HTTP 200, Cosmos DB 接続 OK ✅

**✅ CI/CD 解決済み**: `deploy-azure.yml` の Build ステップを `python:3.13-slim` に更新。`functionAppConfig.runtime.version = "3.13"` と一致。Python 3.13 に統一完了。

#### ✅ 3. GCP Production API — `/limits` エンドポイント 404 — RESOLVED 2026-02-24

**解決**: セッションv2で修復。GCP production API を再デプロイ (revision `00013-big`)。`gcp-production-source.zip` を `gs://ashnova-multicloud-auto-deploy-production-function-source/function-source.zip` にアップロードして `gcloud functions deploy` 実行。CORS_ORIGINS に `https://www.gcp.ashnova.jp` を追加。

**確認済み**: `GET /limits` → `{"maxImagesPerPost":10}` HTTP 200 ✅

#### ✅ 4. AWS Production CloudFront — セキュリティヘッダーポリシー未設定 — RESOLVED 2026-02-24

**解決**: セッションv2で修復。既存ポリシー `multicloud-auto-deploy-production-security-headers` (ID: `aaad020f-c94c-4143-ba2c-4b7921a1a6de`) を DefaultCacheBehavior と `/sns*` CacheBehavior の両方に適用。ETag `E3P5ROKL5A1OLE` → 更新後 `E3JWKAKR8XB7XF`。

**確認済み**: CloudFront Distribution `E214XONKTXJEJD` に HSTS/CSP/X-Content-Type-Options/X-Frame-Options/Referrer-Policy/XSS-Protection ポリシー適用 ✅

#### ✅ 5. AWS Production SNS — Network Error (CI/CD customDomain 上書き) — RESOLVED 2026-02-24

**症状**: `https://www.aws.ashnova.jp/sns/` の SNS アプリで API 呼び出し時に "Network Error" が発生。Axios が status 0 を返す。

**根本原因チェーン**:

1. `deploy-aws.yml` "Sync Pulumi Config" ステップが `${{ secrets.AWS_CUSTOM_DOMAIN }}` (リポジトリレベルシークレット = `staging.aws.ashnova.jp`) を使用
2. `pulumi config set multicloud-auto-deploy-aws:customDomain "staging.aws.ashnova.jp"` が `Pulumi.production.yaml` を上書き
3. `pulumi stack output custom_domain` → `staging.aws.ashnova.jp` を返す (正: `www.aws.ashnova.jp`)
4. Lambda 環境変数 `CORS_ORIGINS` = `...,https://staging.aws.ashnova.jp,...` (正: `https://www.aws.ashnova.jp`)
5. FastAPI CORS ミドルウェアが `Origin: https://www.aws.ashnova.jp` を拒否 → レスポンスに `Access-Control-Allow-Origin` ヘッダーなし → ブラウザが "Network Error" を報告

**補足**:

- API Gateway CORS: `AllowOrigins: ["*"]` → gateway レベルでは通過するが FastAPI が二次レイヤーで拒否
- `auth.ts` は `window.location.origin` を実行時に使用 → Cognito リダイレクト URI は正常動作（auth 自体は壊れていなかった）
- バンドル内 `VITE_COGNITO_REDIRECT_URI` の誤値は CI/CD バグの証拠だが auth には直接影響なし

**修正内容 (コミット `3ea6a08` v1.17.10)**:

| 修正                         | 内容                                                                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `deploy-aws.yml` CI/CD 修正  | "Sync Pulumi Config" を GitHub Secrets ではなく `Pulumi.${STACK_NAME}.yaml` から読むように変更。シークレットはフォールバックのみ |
| React SPA 再ビルド・デプロイ | `www.aws.ashnova.jp` を持つ新バンドル `index-Ch-ro-3Y.js` を S3 デプロイ。旧バンドル `index-BDZFhT4n.js` 削除                    |
| CloudFront キャッシュ無効化  | Invalidation `I1P7ASR5TSVXJUGPQ56A6M6K09` (`/sns/*`) 完了                                                                        |
| Lambda CORS_ORIGINS 即時修正 | `staging.aws.ashnova.jp` 削除: `https://d1qob7569mn5nw.cloudfront.net,https://www.aws.ashnova.jp,http://localhost:5173`          |
| Cognito implicit フロー削除  | `AllowedOAuthFlows: ["code", "implicit"]` → `["code"]` のみ                                                                      |

**確認済み**: Lambda `CORS_ORIGINS` から `staging.aws.ashnova.jp` 削除 ✅ / 次回 CI デプロイでも `Pulumi.production.yaml` から正しい値を読み込む ✅

---

#### 2. GCP Pulumi state drift (非ブロッキング)

**症状**: `pulumi up` が `ManagedSslCertificate` Error 400 (in use) + `URLMap` Error 412 (invalid fingerprint) で失敗

**影響**: GCP production は完全に動作中 ✅。CI/CD の GCP deploy ワークフローが失敗するだけ

**解決方法**:

```bash
cd infrastructure/pulumi/gcp
pulumi stack select production
pulumi refresh --yes  # Pulumiの状態をGCPの実際の状態に同期
pulumi up --yes       # 差分を適用
```

#### ✅ 3. develop ブランチが main から遅延 — RESOLVED 2026-02-24

**現状**: `develop` v1.18.1 / `main` v1.17.10 — ✅ 同期済み (コミット `7efca78`、pre-commit フックにより develop が patch バンプ済み)

---

```
test-cloud-env.sh production → PASS: 14, FAIL: 0, WARN: 3 (all POST 401 = expected auth guard)
test-azure-sns.sh            → PASS: 10, FAIL: 0 (www.azure.ashnova.jp dedicated tests)
test-gcp-sns.sh              → PASS: 10, FAIL: 0 (www.gcp.ashnova.jp dedicated tests)
```

#### React SPA Migration Test Results (2026-02-21)

```
AWS API Health:   ✅  HTTP 200  status=ok  provider=aws
AWS API CRUD:     ✅  POST→GET(7 msgs)→DELETE 200
AWS React SPA:    ✅  HTTP 200  vite.svg, /sns/assets/index-CNhWHZ0v.js

Azure API Health: ✅  HTTP 200  status=ok  provider=azure
Azure API CRUD:   ✅  POST→GET(3 msgs)→DELETE 200
Azure React SPA:  ✅  HTTP 200  vite.svg, /sns/assets/index-D99WuiGj.js

GCP API Health:   ✅  HTTP 200  status=ok  provider=gcp
GCP API CRUD:     ✅  POST→GET(20 msgs)→DELETE 200
GCP React SPA:    ✅  HTTP 200  vite.svg, /sns/assets/index-eZZwVqtD.js

Result: 9/9 passed 🎉
```

---

## AWS Management Console Links

- [API Gateway](https://ap-northeast-1.console.aws.amazon.com/apigateway)
- [Lambda](https://ap-northeast-1.console.aws.amazon.com/lambda)
- [S3 Bucket](https://s3.console.aws.amazon.com/s3/buckets/multicloud-auto-deploy-staging-frontend)
- [CloudFront](https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1TBH4R432SZBZ)

## Azure Portal Links

- [Resource Group](https://portal.azure.com/#@/resource/subscriptions/29031d24-d41a-4f97-8362-46b40129a7e8/resourceGroups/multicloud-auto-deploy-staging-rg)
- [Function Apps](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Web%2Fsites)
- [Front Door](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Cdn%2Fprofiles)

## GCP Console Links

- [Cloud Run](https://console.cloud.google.com/run?project=ashnova)
- [Cloud Storage](https://console.cloud.google.com/storage/browser?project=ashnova)
- [Firestore](https://console.cloud.google.com/firestore/data?project=ashnova)

---

## FinOps — GCP Unused Static IP Address Audit (2026-02-21)

> Audit performed in response to GCP FinOps findings. All static IP addresses in project `ashnova` were reviewed.

### All IP Addresses

```bash
gcloud compute addresses list --project=ashnova \
  --format="table(name,address,status,addressType,users.list())"
```

| Name                                       | IP Address     | Status          | Created    | Used by                             |
| ------------------------------------------ | -------------- | --------------- | ---------- | ----------------------------------- |
| `multicloud-auto-deploy-production-cdn-ip` | 34.8.38.222    | ✅ IN_USE       | —          | Production CDN (Forwarding Rule ×2) |
| `multicloud-auto-deploy-staging-cdn-ip`    | 34.117.111.182 | ✅ IN_USE       | —          | Staging CDN (Forwarding Rule ×2)    |
| `ashnova-production-ip-c41311`             | 34.54.250.208  | ⚠️ **RESERVED** | 2026-02-11 | None                                |
| `multicloud-frontend-ip`                   | 34.120.43.83   | ⚠️ **RESERVED** | 2026-02-14 | None                                |
| `simple-sns-frontend-ip`                   | 34.149.225.173 | ⚠️ **RESERVED** | 2026-01-30 | None                                |

### Background on Unused IPs

| Name                           | Estimated History                                                                                                                                                             |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `simple-sns-frontend-ip`       | Created in early project days (when the project was named `simple-sns`, 2026-01-30). Not referenced in Pulumi code or any Forwarding Rule.                                    |
| `ashnova-production-ip-c41311` | Created for Production CDN (as indicated by the Pulumi suffix `c41311`, 2026-02-11), but later replaced by `multicloud-auto-deploy-production-cdn-ip` and became unnecessary. |
| `multicloud-frontend-ip`       | Created 2026-02-14. No references found anywhere in the codebase or documentation. Assumed to have been reserved experimentally and abandoned.                                |

> **Note**: All three are unlinked from any Pulumi code or Forwarding Rule and can be released immediately.

### Release Commands

```bash
gcloud compute addresses delete ashnova-production-ip-c41311 --global --project=ashnova --quiet
gcloud compute addresses delete multicloud-frontend-ip          --global --project=ashnova --quiet
gcloud compute addresses delete simple-sns-frontend-ip          --global --project=ashnova --quiet
```

> ⚠️ Deletion is irreversible. Confirm each IP has no associated resources via `gcloud compute addresses describe <name> --global` before executing.

---

## FinOps — GCP Unused Cloud Storage Bucket Audit (2026-02-21)

> Conducted as a follow-up to the static IP audit. Legacy Terraform-era buckets and a broken Cloud Function were identified.

### All Buckets (Project: ashnova)

| Bucket Name                                                              | Size      | Verdict       | Notes                                                                           |
| ------------------------------------------------------------------------ | --------- | ------------- | ------------------------------------------------------------------------------- |
| `ashnova-multicloud-auto-deploy-production-frontend`                     | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-production-function-source`              | 5 MB      | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-production-uploads`                      | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-frontend`                        | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-function-source`                 | 5 MB      | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-landing`                         | 8 KB      | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova-multicloud-auto-deploy-staging-uploads`                         | —         | ✅ Active     | Managed by Pulumi                                                               |
| `ashnova.firebasestorage.app`                                            | —         | ✅ Keep       | Firebase system-managed                                                         |
| `ashnova_cloudbuild`                                                     | —         | ✅ Keep       | Cloud Build system-managed                                                      |
| `gcf-v2-sources-899621454670-asia-northeast1`                            | 433 MB    | ✅ Keep       | Source for active Cloud Function v2                                             |
| `gcf-v2-uploads-899621454670.asia-northeast1.cloudfunctions.appspot.com` | —         | ✅ Keep       | Cloud Functions upload staging                                                  |
| `ashnova-staging-frontend`                                               | **empty** | 🗑️ **Delete** | Terraform legacy. Replaced by `ashnova-multicloud-auto-deploy-staging-frontend` |
| `ashnova-staging-function-source`                                        | **65 MB** | 🗑️ **Delete** | Terraform legacy. Contains old zip from 2026-02-14                              |
| `multicloud-auto-deploy-tfstate`                                         | **empty** | 🗑️ **Delete** | Old Terraform state bucket. Empty.                                              |
| `multicloud-auto-deploy-tfstate-gcp`                                     | **6 KB**  | 🗑️ **Delete** | Holds only the Terraform state for the two buckets above                        |

### Background on Deletable Buckets

| Bucket Name                          | Estimated History                                                                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ashnova-staging-frontend`           | Frontend bucket from the old Terraform config (`ashnova-staging-*` naming). Fully migrated to `ashnova-multicloud-auto-deploy-staging-frontend` (Pulumi-managed). Empty.              |
| `ashnova-staging-function-source`    | Cloud Function source bucket from the same Terraform config. Contains a stale 65 MB zip from 2026-02-14. Replaced by `ashnova-multicloud-auto-deploy-staging-function-source` (5 MB). |
| `multicloud-auto-deploy-tfstate`     | Created as a candidate for AWS Terraform state bucket, never used. Empty.                                                                                                             |
| `multicloud-auto-deploy-tfstate-gcp` | Holds the Terraform state for the `ashnova-staging-*` two buckets. No `.tf` files exist in the codebase. Delete all four as a set.                                                    |

### Bonus: Broken Cloud Function (related resource)

| Resource                               | State      | Details                                                                                                                                                           |
| -------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mcad-staging-api` (Cloud Function v2) | **FAILED** | `Cloud Run service not found` error. The Cloud Run service was deleted but the Function definition remains. No references in Pulumi/current code. Safe to delete. |

### Delete Commands

```bash
# Delete 4 buckets (including contents) — delete tfstate-gcp last
gcloud storage rm --recursive gs://ashnova-staging-frontend           --project=ashnova
gcloud storage rm --recursive gs://ashnova-staging-function-source    --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate     --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate-gcp --project=ashnova

# Also delete the broken Cloud Function
gcloud functions delete mcad-staging-api \
  --region=asia-northeast1 --project=ashnova --v2 --quiet
```

> ⚠️ `multicloud-auto-deploy-tfstate-gcp` contains the Terraform state for `ashnova-staging-frontend` and `ashnova-staging-function-source`. Delete all four buckets as a set.

---

---

## E2E テストスクリプト (2026-02-24)

> commit `73af560` — `scripts/` 配下の4ファイルを改良

### `test-sns-all.sh` (新規)

3クラウド統合ラッパー。すべてのクラウドを一括でテストし、最後にサマリーテーブルを表示する。

```bash
# 基本使用 (read-only, production)
bash scripts/test-sns-all.sh --env production

# 特定クラウドのみ
bash scripts/test-sns-all.sh --env production --only azure

# 書き込みテスト有効 (AWS: Cognito 自動認証)
bash scripts/test-sns-all.sh --env production --write \
  --aws-username user@example.com --aws-password *** --aws-client-id 4h3b285v1a9746sqhukk5k3a7i

# 書き込みテスト有効 (GCP: gcloud 自動認証)
bash scripts/test-sns-all.sh --env production --write --gcp-auto-token
```

**サマリー出力例** (production read-only, 2026-02-24):

```
  Cloud       PASS    FAIL    SKIP  Status
  ────────  ──────  ──────  ──────  ──────────
  aws            9       0       4  ✅ PASS
  azure         17       0       2  ✅ PASS
  gcp           13       0       4  ✅ PASS
  ────────  ──────  ──────  ──────  ──────────
  TOTAL         39       0      10
```

### 各スクリプトの改良内容

| スクリプト                  | 追加機能                                                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/test-sns-aws.sh`   | `--username`/`--password`/`--client-id` で Cognito 自動認証、X-Amz-Signature 検証、binary PUT to S3、imageUrl HTTP 200 確認     |
| `scripts/test-sns-gcp.sh`   | `--auto-token` で `gcloud auth print-identity-token` 自動認証、X-Goog-Signature 検証、binary PUT to GCS、imageUrl HTTP 200 確認 |
| `scripts/test-sns-azure.sh` | `x-ms-blob-type: BlockBlob` で binary PUT to Azure Blob (HTTP 201)、SAS read URL HTTP 200 確認                                  |

### テスト一覧 (write モード時の追加項目)

| #   | テスト                | 概要                                                                                       |
| --- | --------------------- | ------------------------------------------------------------------------------------------ |
| 5-2 | 署名URL検証           | presigned URL に `X-Amz-Signature=` / `X-Goog-Signature=` / SAS token が含まれることを確認 |
| 5-3 | binary PUT            | 1×1 PNG を実際に presigned URL へ PUT し HTTP 200/201 を確認                               |
| 5-4 | imageUrl アクセス確認 | PUT したキーで POST /posts → GET /posts/:id → imageUrls[0] に GET → HTTP 200 を確認        |

---

## Cost Monitoring Tools

マルチクラウド + GitHub の費用を一元管理するツールが `scripts/` 配下に実装済みです。

### CLI レポート (`scripts/cost_report.py`)

```bash
python3 scripts/cost_report.py                 # デフォルト: 過去3ヶ月
python3 scripts/cost_report.py --months 6      # 過去6ヶ月
python3 scripts/cost_report.py --json          # JSON 出力
python3 scripts/cost_report.py --aws-only      # AWS のみ
python3 scripts/cost_report.py --azure-only    # Azure のみ
```

### macOS メニューバーウィジェット (`scripts/mac-widget/`)

[xbar](https://xbarapp.com) を使った 1 時間ごと自動更新ウィジェット。

```bash
brew install --cask xbar
bash scripts/mac-widget/install.sh
open -e scripts/mac-widget/.env    # 認証情報を設定
```

### 通貨処理

| Provider | 方式                                                                                                                   |
| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| AWS      | Cost Explorer は USD 固定 → [open.er-api.com](https://open.er-api.com) で リアルタイム USD/JPY 変換 (失敗時 ¥150 固定) |
| Azure    | Cost Management API の `rows[n][2]` から通貨コードを直接取得 (JPY)                                                     |
| GCP      | Billing API — サービスアカウント or `gcloud auth`                                                                      |
| GitHub   | Billing API 廃止 (HTTP 410) → `actions/cache/usage` + runs 件数で代替                                                  |

### .env 設定ファイル

`scripts/mac-widget/.env` (git 管理外) に認証情報を記載します。
テンプレート: `scripts/mac-widget/cost-monitor.env.sample`

| 変数                    | 用途                                      |
| ----------------------- | ----------------------------------------- |
| `AZURE_SUBSCRIPTION_ID` | Azure Cost Management                     |
| `GCP_BILLING_ACCOUNT`   | GCP Billing (`01XXXX-XXXXXX-XXXXXX` 形式) |
| `GCP_PROJECT_ID`        | GCP プロジェクト ID                       |
| `GITHUB_TOKEN`          | GitHub Actions 使用量取得                 |
| `GH_REPO`               | `owner/repo` 形式 (個人リポジトリ用)      |

AWS は `~/.aws/credentials` の default プロファイルを使用（追加設定不要）。

---

## Next Section

→ [07 — Runbooks](AI_AGENT_07_RUNBOOKS.md)
