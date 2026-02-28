# 04 — インフラストラクチャ（Pulumi）

> 第II部 — アーキテクチャ・設計 | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## Pulumi 概要

| フィールド | 値                                                  |
| ---------- | --------------------------------------------------- |
| IaC ツール | Pulumi Python SDK 3.x                               |
| 状態       | Pulumi Cloud（リモート状態）                        |
| スタック   | `staging` / `production`                            |
| 言語       | Python                                              |
| コードパス | `infrastructure/pulumi/{aws,azure,gcp}/__main__.py` |

---

## 一般的な操作

```bash
# スタック一覧表示
pulumi stack ls

# デプロイ
pulumi up --stack staging

# 出力を表示
pulumi stack output

# 変更内容をプレビュー（ドライラン）
pulumi preview --stack staging

# リソースを削除（注意が必要）
pulumi destroy --stack staging
```

---

## AWS Pulumi スタック

**ディレクトリ**：`infrastructure/pulumi/aws/`

### リソース一覧

| Pulumi 論理名             | AWS リソース                     | 名前パターン                         |
| ------------------------- | -------------------------------- | ------------------------------------ |
| `lambda-role`             | IAM Role                         | `{project}-{stack}-lambda-role`      |
| `app-secret`              | Secrets Manager Secret           | —                                    |
| `dynamodb-table`          | DynamoDB テーブル                | `{project}-{stack}-posts`            |
| `lambda-function`         | Lambda 関数                      | `{project}-{stack}-api`              |
| `api-gateway`             | API Gateway v2                   | —                                    |
| `frontend-bucket`         | S3 バケット                      | `{project}-{stack}-frontend`         |
| `landing-bucket`          | S3 バケット                      | `{project}-{stack}-landing`          |
| `cloudfront-distribution` | CloudFront（PriceClass_200）     | —                                    |
| `security-headers-policy` | CloudFront ResponseHeadersPolicy | `{project}-{stack}-security-headers` |
| `cognito-user-pool`       | Cognito ユーザープール           | —                                    |
| `sns-topic`               | SNS トピック（アラート）         | —                                    |
| CloudWatch Alarms（複数） | CloudWatch                       | —                                    |

### 主要な設定キー

```bash
pulumi config set aws:region ap-northeast-1
pulumi config set allowedOrigins "https://example.com"
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "aws.example.com"         # カスタムドメイン（オプション）
pulumi config set staticSiteAcmCertificateArn "arn:..."      # ACM 証明書（オプション）
```

> ⚠️ **本番環境スタック向け重要事項**：`pulumi up --stack production` を実行する前に、必ず
> `customDomain` と `acmCertificateArn` を設定する。設定がないと、CloudFront はデフォルト証明書に戻り、
> すべての HTTPS ビジターに対して破断する。
>
> ```bash
> pulumi config set customDomain www.aws.ashnova.jp --stack production
> pulumi config set acmCertificateArn \
>   arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 \
>   --stack production
> ```
>
> ACM 証明書は `us-east-1` に存在する必要があります（CloudFront に必須）。現在の証明書は 2027-03-12 に失効します。

### 主要な出力

```bash
pulumi stack output api_url                      # API Gateway URL
pulumi stack output cloudfront_url               # CloudFront URL
pulumi stack output cloudfront_distribution_id   # CloudFront Distribution ID
pulumi stack output frontend_bucket_name         # S3 バケット名
pulumi stack output lambda_function_name         # Lambda 関数名
pulumi stack output cognito_user_pool_id
pulumi stack output cognito_client_id
```

---

## Azure Pulumi スタック

**ディレクトリ**：`infrastructure/pulumi/azure/`

### リソース一覧

| Pulumi 論理名          | Azure リソース            | 名前パターン             |
| ---------------------- | ------------------------- | ------------------------ |
| `resource-group`       | リソースグループ          | `{project}-{stack}-rg`   |
| `functions-storage`    | ストレージアカウント      | `mcadfunc{suffix}`       |
| `frontend-storage`     | ストレージアカウント      | `mcadweb{suffix}`        |
| `landing-storage`      | ストレージアカウント      | `mcadlanding{suffix}`    |
| `function-app`         | Azure Functions           | `{project}-{stack}-func` |
| `cosmos-account`       | Cosmos DB アカウント      | —                        |
| `frontdoor-profile`    | Front Door プロファイル   | `{project}-{stack}-fd`   |
| `azure-ad-app`         | Azure AD アプリケーション | —                        |
| `spa-rule-set`         | AFD RuleSet               | `SpaRuleSet`             |
| `spa-rewrite-rule`     | AFD ルール                | `SpaIndexHtmlRewrite`    |
| Action Groups + Alerts | Azure Monitor             | —                        |

> **SPA ルーティング**：`SpaRuleSet` はすべての非静的な `/sns/*` リクエストを `/sns/index.html` にリライトして、
> React クライアント側ルーティングが直接 URL アクセスとページリロード時に機能するようにします。
> RuleSet 名は **英数字のみ**（ハイフンなし）である必要があります。条件あたり最大 10 個の match_values。

### 主要な設定キー

```bash
pulumi config set azure-native:location japaneast
pulumi config set environment staging
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "azure.example.com"  # オプション
```

### 主要な出力

```bash
pulumi stack output api_url
pulumi stack output frontdoor_url
pulumi stack output frontend_storage_name
pulumi stack output azure_ad_tenant_id
pulumi stack output azure_ad_client_id
```

---

## GCP Pulumi スタック

**ディレクトリ**：`infrastructure/pulumi/gcp/`

### リソース一覧

| Pulumi 論理名          | GCP リソース                 | 名前                                 |
| ---------------------- | ---------------------------- | ------------------------------------ |
| `frontend-bucket`      | GCS バケット                 | `ashnova-{project}-{stack}-frontend` |
| `uploads-bucket`       | GCS バケット                 | `ashnova-{project}-{stack}-uploads`  |
| `backend-bucket`       | Compute バックエンドバケット | `{project}-{stack}-cdn-backend`      |
| `cdn-ip-address`       | グローバル外部 IP            | `{project}-{stack}-cdn-ip`           |
| `url-map`              | URL マップ                   | —                                    |
| `cloud-run-service`    | Cloud Run                    | `{project}-{stack}-api`              |
| `firestore-db`         | Firestore                    | （デフォルト）                       |
| `managed-ssl-cert`     | SSL 証明書                   | オプション                           |
| Alert Policies（複数） | Cloud Monitoring             | —                                    |

### 主要な設定キー

```bash
pulumi config set gcp:project ashnova
pulumi config set environment staging
pulumi config set alarmEmail your@email.com
pulumi config set staticSiteDomain "gcp.example.com"  # オプション
pulumi config set monthlyBudgetUsd 50                 # 本番環境のみ
```

### 主要な出力

```bash
pulumi stack output api_url
pulumi stack output cdn_url
pulumi stack output cdn_ip_address
pulumi stack output frontend_bucket_name
```

> **GCP 固有の注記**：
>
> - `uploads-bucket`（`ashnova-{project}-{stack}-uploads`）は `allUsers:objectViewer` を持つ — パブリック。
>   `frontend-bucket` にパブリック読み込みを付与しないこと。
> - `ManagedSslCertificate` は `ignore_changes=["name", "managed"]` を使用して、名前ハッシュが変わったときに
>   Pulumi が証明書の置換を試みるのを防ぎます（証明書が HTTPS プロキシに接続されている場合、GCP は 400 を返します）。
> - `pulumi up` が URLMap の `Error 412: Invalid fingerprint` で失敗する場合、`pulumi up` 前に
>   `pulumi refresh --yes --skip-preview` ステップを追加します。
> - Firebase 認可ドメインは Identity Toolkit Admin v2 API 経由で更新する必要があります（`x-goog-user-project` ヘッダーが必須）。
>   これは `deploy-gcp.yml` で自動化されています。

### GCS リソース競合（Error 409 / Error 412）

```bash
# Error 409：バケットすでに存在（状態が同期していない）
# 修正：pulumi up 前に既存バケットを Pulumi 状態にインポート
pulumi import gcp:storage/bucket:Bucket uploads-bucket \
  ashnova-multicloud-auto-deploy-staging-uploads --stack staging

# Error 412：URLMap 上で無効なフィンガープリント（Pulumi 状態が古い）
# 修正：pulumi up 前に pulumi refresh を追加
pulumi refresh --yes --skip-preview --stack staging
pulumi up --yes --stack staging
```

### Azure CLI 認証エラー

```bash
# サービスプリンシパル認証情報を明示的に設定
export AZURE_CLIENT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.clientId')
export AZURE_CLIENT_SECRET=$(echo $AZURE_CREDENTIALS | jq -r '.clientSecret')
export AZURE_SUBSCRIPTION_ID=$(echo $AZURE_CREDENTIALS | jq -r '.subscriptionId')
export AZURE_TENANT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.tenantId')
```

### Azure Pulumi 保留中の操作

```bash
# エラー：「スタックに保留中の操作がある」
pulumi stack export | \
  python3 -c "import sys,json; d=json.load(sys.stdin); d['deployment']['pending_operations']=[]; print(json.dumps(d))" | \
  pulumi stack import --force
```

---

## Lambda Layer 設定

2つのオプション（詳細は `LAMBDA_LAYER_OPTIMIZATION.md` を参照）：

**オプション A — Klayers（デフォルト、推奨）**：
ビルド不要。パブリックなコミュニティ管理 Lambda Layers を使用。Pulumi 設定で有効化：

```bash
pulumi config set use_klayers true
```

**オプション B — カスタムレイヤー**（完全な制御、特定バージョン）：
`./scripts/build-lambda-layer.sh` でビルド（boto3 / Azure / GCP SDK を ZIP から除外）。

---

## Lambda Layer ビルドステップ

```bash
# 1. レイヤーをビルド（deps のみ；boto3 は除外）
./scripts/build-lambda-layer.sh
# → generates services/api/lambda-layer.zip

# 2. レイヤーを発行
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --zip-file fileb://services/api/lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1

# 3. アプリコードのみをパッケージ（~78 KB）
cd services/api
cp -r app .build/package/
cp index.py .build/package/
cd .build/package && zip -r ../../lambda.zip .

# 4. Lambda を更新（直接 ZIP アップロード、S3 不要）
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip
```

---

## 次のセクション

→ [05 — CI/CD パイプライン](AI_AGENT_05_CICD_JA.md)
