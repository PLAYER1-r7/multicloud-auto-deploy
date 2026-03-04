# 10 — カスタムドメイン・テスト

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## カスタムドメインステータス (全て確認済み 2026-02-21)

| クラウド  | カスタムドメイン       | CDN ターゲット                                            | DNS タイプ | ステータス      |
| --------- | ---------------------- | --------------------------------------------------------- | ---------- | --------------- |
| **AWS**   | `www.aws.ashnova.jp`   | `d1qob7569mn5nw.cloudfront.net`                           | CNAME      | ✅ HTTPS active |
| **Azure** | `www.azure.ashnova.jp` | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | CNAME      | ✅ HTTPS active |
| **GCP**   | `www.gcp.ashnova.jp`   | `34.8.38.222` (A レコード)                                | A          | ✅ HTTPS active |

### ステージング CDN エンドポイント (カスタムドメインなし)

| クラウド  | CDN / Front Door URL                                   | Distribution ID     |
| --------- | ------------------------------------------------------ | ------------------- |
| **AWS**   | `d1tf3uumcm4bo1.cloudfront.net`                        | E1TBH4R432SZBZ      |
| **Azure** | `mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` | mcad-staging-d45ihd |
| **GCP**   | `34.117.111.182` (IP)                                  | —                   |

---

## ⚠️ 重要: 再実行前の Pulumi 設定

本番 AWS の `pulumi up` をこれらの設定値なしで実行すると、CloudFront がデフォルト証明書に戻り **HTTPS が壊れます**:

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 --stack production
```

ACM 証明書有効期限: **2027-03-12**

---

## DNS レコード (確認済み)

### AWS

```
CNAME  www.aws.ashnova.jp  →  d1qob7569mn5nw.cloudfront.net
CNAME  _<id>.www.aws.ashnova.jp  →  _<id>.acm-validations.aws.  (ACM 検証)
```

### Azure

```
CNAME  www.azure.ashnova.jp  →  mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net
TXT    _dnsauth.www.azure.ashnova.jp  →  <validationToken>  (AFD 検証)
```

### GCP

```
A  www.gcp.ashnova.jp  →  34.8.38.222  (production)
A  staging.gcp.ashnova.jp  →  34.117.111.182  (staging)
```

---

## 再セットアップ手順 (ドメイン再構成が必要な場合)

### AWS

```bash
# 1. ACM 証明書確認 / リクエスト (us-east-1 のみ)
aws acm list-certificates --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='www.aws.ashnova.jp'].CertificateArn" \
  --output text

# 2. Pulumi 設定を設定
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn <CERT_ARN> --stack production
pulumi up --stack production
```

### Azure

```bash
RESOURCE_GROUP="multicloud-auto-deploy-production-rg"
PROFILE_NAME="multicloud-auto-deploy-production-fd"

# カスタムドメインを作成 (べき等)
az afd custom-domain create \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name azure-ashnova-jp \
  --host-name www.azure.ashnova.jp \
  --certificate-type ManagedCertificate

# 検証ステータスを確認
az afd custom-domain show \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name azure-ashnova-jp \
  --query "{provisioningState,domainValidationState}"
```

### GCP

```bash
cd infrastructure/pulumi/gcp
pulumi config set customDomain www.gcp.ashnova.jp --stack production
pulumi up --stack production
# 注意: マネージド SSL 証明書のプロビジョニングは DNS 伝播後、最大 60 分かかる場合があります
```

---

## ドメイン変更後の CORS

ドメイン変更時は常に CORS を更新してください:

```bash
# AWS
cd infrastructure/pulumi/aws
pulumi config set allowedOrigins "https://www.aws.ashnova.jp,http://localhost:5173" --stack production
pulumi up --stack production

# GCP
cd infrastructure/pulumi/gcp
pulumi config set allowedOrigins "https://www.gcp.ashnova.jp,http://localhost:5173" --stack production
pulumi up --stack production

# Azure — Azure Function App CORS は CLI 経由で設定 (Pulumi 経由不可)
az functionapp cors add \
  --resource-group multicloud-auto-deploy-production-rg \
  --name multicloud-auto-deploy-production-func \
  --allowed-origins "https://www.azure.ashnova.jp"
```

---

## 検証

```bash
# HTTPS チェック
curl -sI https://www.aws.ashnova.jp   | head -3
curl -sI https://www.azure.ashnova.jp | head -3
curl -sI https://www.gcp.ashnova.jp   | head -3

# API ヘルスチェック
curl -s https://www.aws.ashnova.jp/health
curl -s https://www.gcp.ashnova.jp/health

# DNS 解決
dig www.aws.ashnova.jp
dig www.azure.ashnova.jp
dig www.gcp.ashnova.jp
```

---

## 全環境のテスト

### クイック接続確認 (~30秒、認証不要)

```bash
./scripts/test-sns-all.sh --quick
```

クラウドごとのチェック: ランディングページ `/` → 200、SNS アプリ `/sns/` → 200、API `/health` → 200。

### 全認証テスト (全3クラウド)

```bash
./scripts/test-sns-all.sh \
  --aws-token   "$AWS_TOKEN" \
  --azure-token "$AZURE_TOKEN" \
  --gcp-token   "$GCP_TOKEN"
```

### 認証トークンの取得

#### AWS — Cognito

```bash
AWS_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=YOUR_EMAIL,PASSWORD=YOUR_PASSWORD \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' \
  --output text)
```

#### GCP — Firebase

```bash
GCP_TOKEN=$(gcloud auth print-identity-token)
```

#### Azure — Azure AD (ブラウザのみ)

```
1. https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/sns/ を開く
2. Microsoft アカウントでログイン
3. DevTools → Application → Local Storage → origin → id_token
AZURE_TOKEN="<id_token をここに貼り付け>"
```

### クラウドごとのテストスクリプト

| スクリプト                      | 目的                                     |
| ------------------------------- | ---------------------------------------- |
| `scripts/test-sns-all.sh`       | ⭐ 全3クラウドを統合管理                 |
| `scripts/test-landing-pages.sh` | ランディングページテストのみ             |
| `scripts/test-sns-aws.sh`       | AWS 全体スイート (認証あり)              |
| `scripts/test-sns-azure.sh`     | Azure 全体スイート (認証あり)            |
| `scripts/test-sns-gcp.sh`       | GCP 全体スイート (認証あり)              |
| `scripts/test-sns-all.sh`       | バイナリ PUT + imageUrl チェック付き E2E |
| `scripts/test-e2e.sh`           | 軽量マルチクラウドスモークテスト         |

### pytest 統合テスト (unit/integration、モック)

```bash
# 全テスト
cd services/api && pytest tests/

# クラウドバックエンド別
pytest tests/ -m aws
pytest tests/ -m gcp
pytest tests/ -m azure

# シェルスクリプト経由
./scripts/run-integration-tests.sh        # 標準
./scripts/run-integration-tests.sh -v     # verbose
./scripts/run-integration-tests.sh --coverage  # カバレッジレポート付き
```

テストカバレッジには、全3バックエンドの CRUD 操作、権限チェック、ページネーション、タグフィルタリング、プロフィール更新が含まれます。

---

## 次のセクション

→ [00 — Critical Rules](AI_AGENT_00_CRITICAL_RULES.md) (循環) | [07 — Runbooks](AI_AGENT_07_RUNBOOKS.md)
