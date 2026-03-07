# 08 — Security

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Current Security Configuration Status

> Last updated: 2026-02-24 (Defender for Cloud セキュアスコア分析・新規タスク追加)

| Feature                   | AWS                      | Azure                          | GCP                          | Notes                                                                                                        |
| ------------------------- | ------------------------ | ------------------------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| HTTPS enforced            | ✅                       | ✅                             | ✅ Pulumi済 (要 pulumi up)   | GCP: HTTP→HTTPS リダイレクト用 URLMap を分離。ポート80は301 redirect のみ                                    |
| WAF                       | ✅ WebACL (CloudFront)   | ❌                             | ✅ Cloud Armor               | Azure: Front Door Standard SKU では WAF Policy 未設定 (Premium SKU is prohibited; use standalone WAF Policy) |
| Rate limiting             | ❌                       | ❌                             | ✅ 100req/min/IP             |                                                                                                              |
| SQLi / XSS protection     | ❌                       | ❌                             | ✅                           |                                                                                                              |
| Data encryption (at rest) | ✅ SSE-S3                | ✅ Azure SSE                   | ✅ Google-managed            |                                                                                                              |
| Versioning                | ✅                       | ✅                             | ✅                           |                                                                                                              |
| Access logs (CDN)         | ✅ CloudFront            | ✅ Front Door → Log Analytics  | ✅ Cloud CDN                 | Azure: DiagnosticSetting 追加 (2026-02-24, 要 pulumi up)                                                     |
| Security headers          | ✅ CloudFront RHP        | ❌                             | ❌                           | HSTS/CSP/X-Frame/X-Content/Referrer/XSS (AWS のみ, 2026-02-23)                                               |
| Soft delete / retention   | ❌                       | ✅ 7 days                      | ❌                           |                                                                                                              |
| CORS config               | ✅ 実ドメイン (Pulumi済) | ✅ 実ドメイン (Pulumi済)       | ✅ 実ドメイン (Pulumi済)     | production `*` → 実ドメイン絞り込み完了 (2026-02-24, 要 pulumi up)                                           |
| Audit logging             | ✅ CloudTrail (Pulumi済) | ✅ Log Analytics (Pulumi済)    | ✅ IAMAuditConfig (Pulumi済) | 全項目 Pulumi コード実装済み。各クラウドで `pulumi up` により有効化される                                    |
| Managed Identity          | N/A                      | ❌ 未設定 (staging/production) | N/A (Cloud Run SA)           | Azure Function App にシステム割り当てマネージドIDが未設定 (Defender 指摘 2026-02-24)                         |
| Key Vault 消去保護        | N/A                      | ❌ 未設定                      | N/A                          | `enable_purge_protection=True` を Pulumi に追加が必要 (Defender 指摘 2026-02-24)                             |
| Key Vault 診断ログ        | N/A                      | ❌ 未設定                      | N/A                          | DiagnosticSetting → Log Analytics Workspace への転送が未設定 (Defender 指摘 2026-02-24)                      |

---

## Authentication Configuration

### AWS — Amazon Cognito

```
Auto-created by Pulumi:
  - Cognito User Pool
  - User Pool Client (allowed_oauth_flows=["code"] のみ — implicit 廃止)
  - User Pool Domain

Lambda environment variables:
  AUTH_PROVIDER=cognito
  COGNITO_USER_POOL_ID=<Pulumi output>
  COGNITO_CLIENT_ID=<Pulumi output>
  AWS_REGION=ap-northeast-1
```

**OAuth フロー: PKCE (Proof Key for Code Exchange)** — 2026-02-23 実装

| 項目            | 内容                                                   |
| --------------- | ------------------------------------------------------ |
| フロー          | Authorization Code + PKCE (S256)                       |
| `response_type` | `code` (implicit `token` は廃止)                       |
| code_verifier   | 256-bit ランダム、sessionStorage に保存                |
| code_challenge  | SHA-256(verifier) → Base64URL                          |
| トークン交換    | ブラウザから `POST /oauth2/token` (code_verifier 付き) |
| 利点            | URLフラグメントへのトークン漏洩が完全に排除される      |

> **注意**: `implicit` フローは Cognito UserPoolClient の `allowed_oauth_flows` から削除済み。
> 古い implicit フロー URL (`response_type=token`) でアクセスすると Cognito がエラーを返す。

### Azure — Azure AD

```
Auto-created by Pulumi:
  - Azure AD Application (pulumi-azuread)
  - Service Principal
  - OAuth2 Permission Scope (API.Access)
  - Redirect URIs

Functions environment variables:
  AUTH_PROVIDER=azure
  AZURE_TENANT_ID=<Pulumi output "azure_ad_tenant_id">
  AZURE_CLIENT_ID=<Pulumi output "azure_ad_client_id">
```

### GCP — Firebase Auth

```
Auto-created by Pulumi:
  - Firebase Auth project configuration
  - Firebase Auth Google Sign-In provider enabled

Cloud Run (API) environment variables:
  AUTH_PROVIDER=firebase
  GCP_PROJECT_ID=ashnova
  GCP_SERVICE_ACCOUNT=899621454670-compute@developer.gserviceaccount.com
  (uses impersonated_credentials to generate GCS presigned URLs via IAM signBlob API)

Cloud Run (frontend-web) environment variables:
  AUTH_PROVIDER=firebase
  AUTH_DISABLED=false
  FIREBASE_API_KEY=<GitHub Secret: FIREBASE_API_KEY>
  FIREBASE_AUTH_DOMAIN=<GitHub Secret: FIREBASE_AUTH_DOMAIN>
  FIREBASE_PROJECT_ID=ashnova
  FIREBASE_APP_ID=<GitHub Secret: FIREBASE_APP_ID>

Firebase authorized domain:
  multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app

Token refresh:
  `onIdTokenChanged` in home.html auto-refreshes the token (and re-issues the session cookie)
```

---

## IAM Least-Privilege Policies

### AWS Lambda execution role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["logs:*"], "Resource": "arn:aws:logs:*" },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/simple-sns-messages*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::*uploads*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "*"
    }
  ]
}
```

### Azure Service Principal (pulumi-deploy)

- Role: `Contributor` (subscription scope)
- Storage Blob Data Contributor: `mcadweb*` Storage Account

### GCP — Service account (github-actions-deploy)

- Role: `roles/editor`
- Additional: `roles/storage.objectAdmin` (uploads bucket, for presigned URL signing)
- Additional: `roles/iam.serviceAccountTokenCreator` (to impersonate Compute Engine SA for `signBlob` API)

> **Note**: GCS uploads bucket (`ashnova-multicloud-auto-deploy-staging-uploads`) is intentionally public (`allUsers:objectViewer`) to allow direct image display in browsers. Do NOT apply this to the frontend bucket.

---

## Secret Management

| Cloud | Service         | Primary use                      |
| ----- | --------------- | -------------------------------- |
| AWS   | Secrets Manager | DB credentials, API keys         |
| Azure | Key Vault       | Connection strings, certificates |
| GCP   | Secret Manager  | Service account keys             |
| CI/CD | GitHub Secrets  | Cloud provider credentials       |

---

## Unresolved Security Issues (by priority)

1. **Apply security Pulumi changes** (high priority — next action)
   以下の変更が Pulumi コードに実装済みだが、まだ `pulumi up` で本番に適用されていない:
   - CORS `*` → 実ドメイン絞り込み (全3クラウド production)
   - AWS CloudTrail 有効化
   - GCP HTTP→HTTPS リダイレクト分離
   - GCP Cloud Audit Logs (`IAMAuditConfig`)
   - Azure Log Analytics Workspace + Front Door DiagnosticSetting

   ```bash
   cd infrastructure/pulumi/aws   && pulumi up --stack production
   cd infrastructure/pulumi/gcp   && pulumi up --stack staging && pulumi up --stack production
   cd infrastructure/pulumi/azure && pulumi up --stack staging && pulumi up --stack production
   ```

2. **Azure WAF** (high priority)
   Front Door Standard SKU では組み込み WAF が使えない。
   Repository policy prohibits Premium SKU.
   対策: Standard SKU 向け独立 WAF Policy を作成して Front Door に紐付け。

3. **Add AWS WAF managed rules** (medium priority)
   WAF WebACL は production に存在するが `AWSManagedRulesCommonRuleSet` 等のルールが未チューニング。
   `AWSManagedRulesAmazonIpReputationList` (悪意のある IP リスト) を追加することを推奨。

4. **Azure security headers** (medium priority)
   AWS CloudFront にのみ設定済み。Azure Front Door の RuleSet に
   HSTS/CSP(`upgrade-insecure-requests`)/X-Frame-Options 等のレスポンスヘッダーアクションを追加する。

5. **GCP security headers** (medium priority)
   Cloud Run の FastAPI アプリ層 (ミドルウェア) にセキュリティヘッダーを追加する。

6. **Azure Key Vault network ACLs** (medium priority — Defender 指摘, Pulumi対応可)
   現在 `default_action="Allow"` (全許可)。`network_acls.default_action="Deny"` に変更し
   `bypass="AzureServices"` を維持することで、Managed Identity 経由のアクセスは継続可能。
   **前提条件**: #8 (Function App Managed Identity 有効化) を先に完了すること。

   ```python
   network_acls=azure.keyvault.NetworkRuleSetArgs(
       bypass="AzureServices",
       default_action="Deny",  # Allow → Deny に変更
   ),
   ```

7. **GCP SSL certificate placeholder** (low priority — 既に実ドメイン設定済みの可能性あり)
   `gcp/Pulumi.staging.yaml` の `customDomain` が `staging.gcp.ashnova.jp` に設定済み。
   Managed SSL Certificate のドメインハッシュを確認し、`example.com` が残っていれば修正。

8. **Function App Managed Identity 有効化** (high priority — Defender 指摘, 即時対応可)
   staging / production 両環境の Function App にシステム割り当てマネージドIDが未設定。
   Azure CLI で即時有効化可能:

   ```bash
   az functionapp identity assign \
     --name multicloud-auto-deploy-staging-func \
     --resource-group multicloud-auto-deploy-staging-rg
   az functionapp identity assign \
     --name multicloud-auto-deploy-production-func \
     --resource-group multicloud-auto-deploy-production-rg
   ```

   有効化後は #6 (Key Vault ファイアウォール) と Storage 共有キーアクセス削除の前提となる。

9. **Azure Key Vault 消去保護 (purge protection)** (medium priority — Pulumi対応可)
   `enable_purge_protection=True` を Pulumi コードに追加して `pulumi up` するだけ。
   一度有効化すると無効に戻せないが、既存の `enable_soft_delete=True` 環境では安全。

   ```python
   enable_soft_delete=True,
   enable_purge_protection=True,  # 追加
   soft_delete_retention_in_days=7,
   ```

10. **Azure Key Vault 診断ログ** (low priority — Pulumi対応可)
    Log Analytics Workspace は既に Pulumi 実装済み。DiagnosticSetting を追加するだけ。

    ```python
    key_vault_diagnostics = azure.insights.DiagnosticSetting(
        "key-vault-diagnostics",
        resource_uri=key_vault.id,
        workspace_id=log_analytics_workspace.id,
        logs=[azure.insights.LogSettingsArgs(
            category_group="allLogs",
            enabled=True,
            retention_policy=azure.insights.RetentionPolicyArgs(days=30, enabled=True),
        )],
    )
    ```

11. **Azure セキュリティ連絡先 / 重要度高アラート通知** (low priority — CLI即時対応可)
    サブスクリプションにセキュリティ連絡先メールが未設定。Azure CLI で即時対応可能:

    ```bash
    az security contact create \
      --email "your@email.com" \
      --alert-notifications On \
      --alerts-to-admins On
    ```

12. **サブスクリプション所有者の複数設定** (high priority — Portal/CLI対応可)
    現在の所有者 (`sat0sh1kawada`) が1名のみ。Microsoft の推奨は最低2名。
    信頼できる2人目を Owner ロールに追加することで対応可能:

    ```bash
    az role assignment create \
      --assignee "second-user@email.com" \
      --role "Owner" \
      --scope "/subscriptions/29031d24-d41a-4f97-8362-46b40129a7e8"
    ```

---

### Defender for Cloud — 対応困難な項目 (現行アーキテクチャの制約)

> 下記はいずれも VNet 構築・有料プラン追加・大規模アーキテクチャ変更を伴うため、現時点では対応見送り推奨。

| 項目                                                                           | 重大度 | 対応困難な理由                                                                   |
| ------------------------------------------------------------------------------ | ------ | -------------------------------------------------------------------------------- |
| Cosmos DB ファイアウォール規則                                                 | Medium | Consumption Plan は固定IP なし。特定IP での絞り込み不可                          |
| Cosmos DB AAD 唯一認証                                                         | Medium | 接続文字列→MSI+RBAC への API 全書き直しが必要                                    |
| Cosmos DB / Key Vault プライベートリンク                                       | Medium | VNet 新規構築が前提                                                              |
| Cosmos DB パブリックネットワークアクセス無効化                                 | Medium | VNet 統合なしでは API が完全停止                                                 |
| Storage プライベートリンク / VNet 規則 (mcadweb/mcadfunc)                      | Medium | 静的ウェブサイト用途では不可。Premium SKU は使用禁止のため、別アーキテクチャ前提 |
| Storage パブリックアクセス禁止 (mcadweb)                                       | Medium | 静的ウェブサイトホスティングには公開アクセスが必須                               |
| Microsoft Defender CSPM / App Service / Key Vault / Resource Manager / Storage | High   | 有料プラン。追加費用が発生するため要予算判断                                     |

---

## Security Headers (AWS CloudFront — 確認済み 2026-02-23)

> Pulumi リソース: `aws.cloudfront.ResponseHeadersPolicy` (`multicloud-auto-deploy-{stack}-security-headers`)
> `default_cache_behavior` + `/sns*` ordered_cache_behavior 両方に適用。

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: upgrade-insecure-requests
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

**`upgrade-insecure-requests` の効果**:

- ブラウザが `http://` サブリソース (画像・スクリプト・CSS) を自動的に `https://` にアップグレード
- Mixed Content による「保護されていない通信」警告を防止
- HSTS と合わせて二重の HTTPS 強制を実現

**検証コマンド**:

```bash
curl -sI https://staging.aws.ashnova.jp/ | grep -iE 'strict-transport|content-security|x-content|x-frame|referrer'
# 期待値:
# strict-transport-security: max-age=31536000; includeSubDomains
# content-security-policy: upgrade-insecure-requests
# x-content-type-options: nosniff
# x-frame-options: SAMEORIGIN
# referrer-policy: strict-origin-when-cross-origin
```

---

## S3 セキュリティ (AWS — フロントエンドバケット)

**設定済み (2026-02-23)**:

```python
# infrastructure/pulumi/aws/__main__.py
BucketPublicAccessBlock(
    block_public_acls=True,
    ignore_public_acls=True,
    block_public_policy=True,
    restrict_public_buckets=True,
)
```

| 項目                               | 状態                                       |
| ---------------------------------- | ------------------------------------------ |
| S3 HTTP ウェブサイトエンドポイント | 403 Forbidden (パブリックアクセス完全遮断) |
| バケットポリシー                   | OAI (`aws:SourceArn: CloudFront`) のみ許可 |
| CloudFront 経由 HTTPS              | 200 OK                                     |

**API の HTTP URL スルー防止 (`aws_backend.py`)**:

```python
# _resolve_image_urls: http:// URL はスキップして Mixed Content を防ぐ
if k.startswith("https://"):
    result.append(k)           # そのまま使用
elif k.startswith("http://"):
    logger.warning("Skipping insecure HTTP image URL")  # スキップ
else:
    result.append(self._key_to_presigned_url(k))  # S3キー → presigned HTTPS URL
```

---

## Azure CORS Configuration (Critical — Read Before Touching Azure)

Azure Functions (Flex Consumption) has **two independent CORS layers** that must both be
configured correctly. Setting CORS in Python/FastAPI code has no effect.

### Layer 1 — Function App platform CORS (controls API requests)

Kestrel (.NET HTTP server) intercepts all `OPTIONS` preflight requests before the Python
runtime. Configure via Azure CLI:

```bash
# Remove wildcard first (wildcards suppress per-origin rules)
az functionapp cors remove \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins '*'

# Add specific origins
az functionapp cors add \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins "https://your.domain.com"
```

### Layer 2 — Blob Storage CORS (controls image uploads via SAS URL)

Image uploads go directly from the browser to Blob Storage via SAS PUT URL — they do NOT
pass through the Function App. Blob Storage CORS is completely independent:

```bash
az storage cors clear --account-name "$STORAGE_ACCOUNT" --services b
az storage cors add \
  --account-name "$STORAGE_ACCOUNT" \
  --services b \
  --methods GET POST PUT DELETE OPTIONS \
  --origins "https://your.domain.com" \
  --allowed-headers "*" \
  --exposed-headers "*" \
  --max-age 3600
```

### Summary

```
Browser → Function App  API calls (GET/POST/PUT/DELETE)
  ⇒ Configured via: az functionapp cors add

Browser → Blob Storage  Image uploads (SAS URL PUT)
  ⇒ Configured via: az storage cors add --services b
```

---

## Audit Logging Configuration (2026-02-24 実装)

### AWS — CloudTrail

**Pulumi リソース** (`infrastructure/pulumi/aws/__main__.py`):

- `cloudtrail_bucket`: S3 バケット (パブリックアクセス完全遮断・バージョニング有効)
- `cloudtrail_bucket_policy`: CloudTrail サービス専用バケットポリシー
- `cloudtrail`: `aws.cloudtrail.Trail`
  - `is_multi_region_trail=True` — 全リージョン対象
  - `include_global_service_events=True` — IAM / STS / Cognito を含む
  - `enable_log_file_validation=True` — SHA-256 ダイジェストによるログ改ざん検知

| 出力                     | 内容                                 |
| ------------------------ | ------------------------------------ |
| `cloudtrail_name`        | Trail 名 (`{project}-{stack}-trail`) |
| `cloudtrail_bucket_name` | ログ保存先 S3 バケット               |

### GCP — Cloud Audit Logs

**Pulumi リソース** (`infrastructure/pulumi/gcp/__main__.py`):

- `audit_config`: `gcp.projects.IAMAuditConfig(service="allServices")`
  - `ADMIN_READ` — 管理者操作 (無料)
  - `DATA_READ` — Firestore / GCS データ読み取り
  - `DATA_WRITE` — Firestore / GCS データ書き込み

Cloud Logging のログエクスプローラ (`https://console.cloud.google.com/logs`) で確認可能。

### Azure — Log Analytics Workspace

**Pulumi リソース** (`infrastructure/pulumi/azure/__main__.py`):

- `log_analytics_workspace`: `azure.operationalinsights.Workspace`
  - SKU: `PerGB2018` (月 5 GB 無料枠)
  - 保存期間: 30 日
- `app_insights`: `ingestion_mode="LogAnalytics"` に変更 (旧: `ApplicationInsights`)
- `frontdoor_diagnostics`: `azure.insights.DiagnosticSetting`
  - Front Door の `allLogs` カテゴリを Log Analytics に転送

| 出力                           | 内容                                |
| ------------------------------ | ----------------------------------- |
| `log_analytics_workspace_name` | Workspace 名 (`mcad-logs-{suffix}`) |
| `log_analytics_workspace_id`   | ARM リソース ID                     |

---

## Next Section

→ [09 — Remaining Tasks](AI_AGENT_09_TASKS.md)
