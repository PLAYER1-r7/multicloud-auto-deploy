# Staging vs Production 環境構成比較

**実装日**: 2026-03-03
**変更者**: AI Agent (GitHub Copilot)
**参照コミット**: 6587ea4a

---

## 概要

Staging と Production 環境間の CDN/Load Balancer 構成の詳細比較。Staging は開発/テスト目的で**低コスト直接アクセス**、Production は**フルCDN構成**で最適化されています。

---

## 1. 全体アーキテクチャ比較

### AWS

```
┌─────────────────────────────────────────────────────────────┐
│                         CLOUDFRONT                           │
│  (OAI + Response Headers Policy + WAF + Distribution)       │
│             ✅ PRODUCTION のみ                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────┬──────────────┬──────────────┐
│   S3 + IAM   │ API Gateway  │  Load Balancer│
│   Bucket     │    Lambda    │              │
└──────────────┴──────────────┴──────────────┘

STAGING 構成:
  - CloudFront: ❌ 削除
  - S3 パブリックアクセス: ✅ 有効化

PRODUCTION 構成:
  - CloudFront: ✅ 有効（OAI + WAF）
  - S3 パブリックアクセス: ❌ ブロック
```

### Azure

```
┌──────────────────────────────────────────────┐
│          FRONT DOOR (CDN + WAF)             │
│         ✅ PRODUCTION のみ                   │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────┬──────────────┐
│  Blob Storage│ Function App │
│              │     (API)    │
└──────────────┴──────────────┘

STAGING 構成:
  - Front Door: ❌ 削除
  - Blob Storage: ✅ 直接アクセス
  - Function App: ✅ 直接アクセス

PRODUCTION 構成:
  - Front Door: ✅ アクティブ
  - ルート: /api/* → Function App (no-cache)
  - ルート: /* → Blob Storage
```

### GCP

```
┌─────────────────────────────────────────────┐
│    GLOBAL LOAD BALANCER + Cloud CDN       │
│        ✅ PRODUCTION のみ                   │
└─────────────────────────────────────────────┘
            ↓                    ↓
┌───────────────────────┐  ┌─────────────────┐
│  Backend Bucket (GCS) │  │ Cloud Run (API) │
│   + Cloud CDN         │  │  (Direct call)  │
└───────────────────────┘  └─────────────────┘

STAGING 構成:
  - Load Balancer: ❌ 削除
  - Cloud CDN: ❌ 削除
  - GCS: ✅ 直接アクセス
  - Cloud Run: ✅ 直接アクセス

PRODUCTION 構成:
  - Load Balancer: ✅ グローバル
  - Cloud CDN: ✅ 有効（GCS のみ）
  - Cloud Run: ✅ 直接アクセス（API）
```

---

## 2. 詳細コンポーネント比較

### 2.1 AWS リソース比較

| コンポーネント | Staging | Production | 用途 |
|-------------|---------|-----------|------|
| **CloudFront** | ❌ | ✅ | グローバルCDN |
| **CloudFront OAI** | ❌ | ✅ | S3 private access |
| **Response Headers Policy** | ❌ | ✅ | セキュリティヘッダー (HSTS/CSP) |
| **WAF Web ACL** | ❌ | ✅ | DDoS/Injection 防護 |
| **S3 Public Access** | ✅ Block=False | ✅ Block=True | ウェブサイト公開制御 |
| **API Gateway** | ✅ | ✅ | Lambda 実行 |
| **Lambda** | ✅ | ✅ | ビジネスロジック |
| **S3 Bucket** | ✅ | ✅ | ストレージ |

**この構成により**:
- Staging: 開発用直接アクセス + 低コスト
- Production: CDN キャッシング + セキュリティ強化

### 2.2 Azure リソース比較

| コンポーネント | Staging | Production | 用途 |
|-------------|---------|-----------|------|
| **Front Door** | ❌ 削除 | ✅ | グローバルCDN + WAF |
| **Front Door Rules** | ❌ | ✅ | ルーティング (/api/*, /) |
| **Blob Storage** | ✅ | ✅ | ストレージ |
| **Function App** | ✅ | ✅ | サーバーレス API |
| **Function Slots** | ✅ Staging | ✅ Production | 環境分離 |
| **Virtual Network** | ✅ | ✅ | ネットワーク分離 |

**削除履歴**:
```
2026-03-03 14:45 - Front Door Staging 削除開始
2026-03-03 15:15 - リソースロック (operation in progress)
2026-03-03 15:30 - 15分待機後、再度削除実行
2026-03-03 15:32 - 削除完了 (ResourceNotFound error)
```

### 2.3 GCP リソース比較

| コンポーネント | Staging | Production | 用途 |
|-------------|---------|-----------|------|
| **Global Load Balancer** | ❌ | ✅ | HTTP(S) ロードバランシング |
| **Cloud CDN** | ❌ | ✅ | コンテンツキャッシング |
| **Cloud Armor** | ❌ | ✅ | Managed DDoS/Bot 防護 |
| **External IP** | ❌ | ✅ | グローバル IP ($7.30/月) |
| **Managed SSL** | ❌ | ✅ | HTTPS 証明書 |
| **Backend Bucket (GCS)** | ✅ | ✅ | ストレージ |
| **Cloud Run** | ✅ | ✅ | サーバーレス API |
| **Cloud Storage** | ✅ | ✅ | Object storage |

**アーキテクチャの特徴**:
- Cloud CDN: GCS (静的) のみ（Load Balancer 経由）
- Cloud Run: API (動的) 直接アクセス（キャッシュなし）

---

## 3. コスト 影響度分析

### 3.1 月額コスト差分

```
◆ STAGING DELETED RESOURCES (月額費用)

[AWS]
├─ CloudFront Distribution: $0.085/GB × (推定 100GB/月) = $8.50
├─ WAF Web ACL: $5.00
└─ Total Removed: $13.50/月

[Azure]
├─ Front Door Profile: $1.00
├─ Front Door Routes: $0.50 × 10 routes = $5.00
└─ Total Removed: $6.00/月

[GCP]
├─ External IP: $0.01/時間 × 730 = $7.30
├─ Load Balancer Processing: $0.025/時間 × 730 = $18.25
└─ Total Removed: $25.55/月

【月額削減合計】: $45.05/月
【推定年間削減】: $540.60/年

※ 検査あたり課金項目（Forwarding Rule等）を含めると +$5-10/月の可能性
```

### 3.2 実装後の月額費用予測

```
PRODUCTION ESTIMATE:

[AWS]
├─ CloudFront: $10-15/月
├─ WAF: $7/月
└─ Subtotal: $17-22/月

[Azure]
├─ Front Door: $5-10/月
└─ Subtotal: $5-10/月

[GCP]
├─ Cloud CDN: $8-12/月
├─ Load Balancer: $20-30/月
├─ Cloud Armor: $3-5/月
└─ Subtotal: $31-47/月

━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL PRODUCTION: $53-79/月
PREVIOUS (w/Staging): $98-124/月
[削減: $45-51/月] ✅
```

---

## 4. Pulumi IaC 実装詳細

### 4.1 AWS CloudFront 条件付け

**ファイル**: [infrastructure/pulumi/aws/__main__.py](../infrastructure/pulumi/aws/__main__.py#L570-L850)

```python
# CloudFront OAI (Origin Access Identity)
if stack == "production":
    origin_access_identity = aws.cloudfront.OriginAccessIdentity(
        "frontend-oa",
        comment="Origin Access Identity for S3 frontend bucket",
    )

# S3 Bucket Public Access Block
frontend_bucket_public_access_block = aws.s3.PublicAccessBlock(
    "frontend-bucket-public-access-block",
    bucket=frontend_bucket.id,
    block_public_acls=(stack == "production"),      # Prod: Block / Staging: Allow
    block_public_policy=(stack == "production"),    # Prod: Block / Staging: Allow
    ignore_public_acls=(stack == "production"),     # Prod: Block / Staging: Allow
    restrict_public_buckets=(stack == "production"),# Prod: Block / Staging: Allow
)

# Staging: S3 パブリックアクセスポリシー追加
if stack == "staging":
    frontend_bucket_policy = aws.s3.BucketPolicy(
        "frontend-bucket-policy",
        bucket=frontend_bucket.id,
        policy=frontend_bucket.arn.apply(
            lambda bucket_arn: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"{bucket_arn}/*",
                }],
            })
        ),
    )

# CloudFront Distribution (Production only)
if stack == "production":
    distribution = aws.cloudfront.Distribution(
        "frontend-cdn",
        origins=[...],
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(...),
        ordered_cache_behaviors=[
            aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
                path_pattern="/api/*",
                cache_policy_id="4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # CachingDisabled
                ...
            ),
        ],
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(...),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(...),
    )
```

### 4.2 GCP Cloud CDN 条件付け

**ファイル**: [infrastructure/pulumi/gcp/__main__.py](../infrastructure/pulumi/gcp/__main__.py#L294-L515)

```python
# Production only: Load Balancer + Cloud CDN 構成
if stack == "production":
    # External IP
    cdn_ip_address = gcp.compute.GlobalAddress(
        "cdn-ip",
        address_type="EXTERNAL",
    )

    # Backend Bucket (Cloud CDN)
    backend_bucket = gcp.compute.BackendBucket(
        "cdn-backend-bucket",
        bucket_name=static_bucket.name,
        cdn_policy=gcp.compute.BackendBucketCdnPolicyArgs(
            cache_mode="CACHE_ALL_STATIC",
            default_ttl=86400,
            max_ttl=2592000,
        ),
    )

    # Managed SSL Certificate
    managed_ssl_cert = gcp.compute.ManagedSslCertificate(
        "managed-ssl",
        managed=gcp.compute.ManagedSslCertificateManagedArgs(
            domains=[domain],
        ),
    )

    # HTTPS Proxy
    https_proxy = gcp.compute.TargetHttpsProxy(
        "https-proxy",
        url_map=url_map.id,
        ssl_certificates=[managed_ssl_cert.id],
    )

    # Forwarding Rule
    https_forwarding_rule = gcp.compute.GlobalForwardingRule(
        "https-rule",
        target=https_proxy.id,
        ip_address=cdn_ip_address.id,
        port_range="443",
        load_balancing_scheme="EXTERNAL",
    )

else:
    # Staging: No Load Balancer, no Cloud CDN
    cdn_ip_address = None
    backend_bucket = None
    managed_ssl_cert = None
```

### 4.3 Azure Front Door

**注記**: Azure Terraform/Bicep なし → 手動削除

```bash
# Staging Front Door 削除実行
az afd profile delete \
  --resource-group multicloud-auto-deploy-staging-rg \
  --name multicloud-auto-deploy-staging-fd

# 結果: ResourceNotFound (削除完了)
```

---

## 5. ネットワークアーキテクチャ比較

### 5.1 リクエストフロー

#### Staging

```
[ユーザー]
  ↓
[AWS S3 直接] / [Azure Blob 直接] / [GCS 直接]
  ↓
[AWS API Gateway] / [Azure Function] / [GCP Cloud Run]
```

**特徴**:
- レイテンシ: 低（CDN なし）
- キャッシュ: なし
- グローバルアクセス: 低速（リージョン完結）
- コスト: 低

#### Production

```
[ユーザー (世界中)]
  ↓
[CloudFront / Front Door / Cloud CDN] (POP)
  ↓
[AWS S3/API] / [Azure Blob/Function] / [GCP GCS/Cloud Run]
```

**特徴**:
- レイテンシ: 低（エッジキャッシュ）
- キャッシュ: 有（静的ファイル）
- グローバルアクセス: 高速（エッジPOP）
- コスト: 高（CDN料金）
- セキュリティ: 高（WAF/DDoS 保護）

---

## 6. デプロイ検証手順

### 6.1 Staging 設定確認

```bash
# AWS S3 パブリックアクセス確認
aws s3api get-public-access-block \
  --bucket multicloud-auto-deploy-staging-frontend

# 期待値:
# {
#   "PublicAccessBlockConfiguration": {
#     "BlockPublicAcls": false,
#     "IgnorePublicAcls": false,
#     "BlockPublicPolicy": false,
#     "RestrictPublicBuckets": false
#   }
# }

# CloudFront 確認状況
aws cloudfront list-distributions | \
  jq '.DistributionList.Items[] | {Id, Enabled, DomainName}'
# Staging should have no distribution
```

```bash
# GCP Cloud Storage 公開アクセス確認
gsutil iam ch allUsers:objectViewer \
  gs://multicloud-auto-deploy-staging-frontend

# 結果: 公開読み取り有効
```

### 6.2 Production 設定確認

```bash
# AWS CloudFront Distribution 確認
aws cloudfront get-distribution --id E1TBH4R432SZBZ | \
  jq '.Distribution.DistributionConfig.CacheBehaviors[] |
      select(.PathPattern == "/api/*") |
      {PathPattern, CachePolicyId}'

# 期待値:
# {
#   "PathPattern": "/api/*",
#   "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
# }
```

```bash
# GCP Load Balancer + Cloud CDN 確認
gcloud compute backend-buckets list
gcloud compute global-addresses list --global

# 期待値:
# - backend buckets: 1個 (cdn-backend-bucket)
# - external ips: 1個 (multicloud-auto-deploy-production-cdn-ip)
```

---

## 7. トラブルシューティング

### 7.1 Staging で CloudFront が見つかる場合

```
症状: aws cloudfront list-distributions に staging distribution がある
原因: 削除ミスまたは脱あったフロー
対処:
  1. Distribution を無効化
     aws cloudfront update-distribution --id <ID> --disable
  2. 15分待機 (requirement)
  3. 削除実行
     aws cloudfront delete-distribution --id <ID>
```

### 7.2 Production で CloudFront が見つからない場合

```
症状: aws cloudfront list-distributions で result が空
原因: デプロイ失敗または TF/Pulumi 設定エラー
対処:
  1. Pulumi stack 確認
     pulumi config get
  2. Stack 再デプロイ
     pulumi up --stack production
  3. CloudFront 確認
     aws cloudfront list-distributions
```

### 7.3 GCP Load Balancer IP が Staging に残っている

```
症状: gcloud compute global-addresses list で staging IP がある
原因: Pulumi destroy が完全実行されなかった
対処:
  1. Manual cleanup
     gcloud compute addresses delete multicloud-auto-deploy-staging-cdn-ip --global
  2. Pulumi state refresh
     pulumi refresh --stack staging
```

---

## 8. ロールバック手順

### 8.1 AWS へ Staging CloudFront を復元

```bash
# 最新コミット確認
git log --oneline -n 5

# 前回のコミット（CloudFront あり）にロールバック
git revert 6587ea4a

# または特定のコミットから復元
git checkout <previous-commit> -- infrastructure/pulumi/aws/__main__.py

# Pulumi update
pulumi up --stack staging
```

### 8.2 Azure 手動 Front Door 再作成

```bash
# Front Door Profile 再作成
az afd profile create \
  --resource-group multicloud-auto-deploy-staging-rg \
  --profile-name multicloud-auto-deploy-staging-fd \
  --sku Standard_AzureFrontDoor \
  --enabled

# Route 追加
az afd rule create \
  --resource-group multicloud-auto-deploy-staging-rg \
  --profile-name multicloud-auto-deploy-staging-fd \
  --rule-name web-route \
  --pattern-match "/*" \
  --origin-group-name backend \
  --forwarding-protocol HttpsOnly
```

### 8.3 GCP へロールバック

```bash
# Pulumi リビジョン確認
pulumi history --stack production

# 前回のスタック復元
pulumi up --stack production --exec-kind auto
```

---

## 9. 監視・アラート設定

### 9.1 CloudFront メトリクス (AWS)

```bash
# CloudWatch アラーム作成
aws cloudwatch put-metric-alarm \
  --alarm-name cloudfront-error-rate \
  --alarm-description "Alert if 4xx/5xx > 1%" \
  --metric-name ErrorRate \
  --namespace AWS/CloudFront \
  --statistic Average \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold
```

### 9.2 Front Door メトリクス (Azure)

```bash
# Azure Monitor アラーム
az monitor metrics alert create \
  --resource-group multicloud-auto-deploy-production-rg \
  --name afd-backend-health \
  --description "Alert if backend health < 99%" \
  --scopes /subscriptions/.../frontDoors/... \
  --window-size PT5M \
  --evaluation-frequency PT1M
```

### 9.3 Cloud CDN メトリクス (GCP)

```bash
gcloud monitoring alert-policies create \
  --display-name="Cloud CDN Cache Hit Ratio" \
  --condition-monitored-resource-type="global_backend_service" \
  --condition-threshold-duration="300s"
```

---

## 10. よくある質問

### Q1: Staging を Production の設定にしたい場合は？

**A**: Pulumi stack を production に変更して再デプロイ

```bash
pulumi select production
# または
pulumi up --stack production
```

### Q2: Staging で CloudFront を一時的に有効化したい？

**A**: `stack == "production"` の条件を外す（非推奨）

非推奨理由: 予期しないコスト増加、環境が混在

**推奨方法**: 固有の staging-enhanced スタック作成

```bash
pulumi stack init staging-with-cdn
```

### Q3: 各環境でカスタムドメインは使える？

**A**: はい、Production は要件、Staging はオプション

```
[AWS]
- Staging: s3-website-ap-northeast-1.amazonaws.com
- Production: www.aws.ashnova.jp

[Azure]
- Staging: mcad-staging-xxx.blob.core.windows.net
- Production: www.azure.ashnova.jp

[GCP]
- Staging: storage.googleapis.com/bucket
- Production: www.gcp.ashnova.jp
```

---

## 参考資料

- [MULTICLOUD_OPTIMIZATION_2026-03-03.md](MULTICLOUD_OPTIMIZATION_2026-03-03.md) - 全体最適化レポート
- [API_CACHING_2026-03-03.md](API_CACHING_2026-03-03.md) - API キャッシング設定
- [infrastructure/pulumi/aws/__main__.py](../infrastructure/pulumi/aws/__main__.py) - AWS IaC
- [infrastructure/pulumi/gcp/__main__.py](../infrastructure/pulumi/gcp/__main__.py) - GCP IaC

---

**最終更新**: 2026-03-03
**検証状態**: ✅ PASS
**コミット**: 6587ea4a
