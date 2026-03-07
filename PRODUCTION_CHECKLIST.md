# 本番デプロイ前チェックリスト

このチェックリストは、本番環境にデプロイする前に必ず確認すべき項目をまとめたものです。

## 🔒 セキュリティ設定

### 1. CORS設定の変更（必須）

現在、すべてのオリジンを許可する設定（`"*"`）になっています。本番環境では必ず実際のドメインに変更してください。

#### AWS

```bash
cd infrastructure/pulumi/aws
```

[Pulumi.staging.yaml](infrastructure/pulumi/aws/Pulumi.staging.yaml) を編集：

```yaml
multicloud-auto-deploy:allowedOrigins: "https://yourdomain.com,https://www.yourdomain.com"
```

#### GCP

```bash
cd infrastructure/pulumi/gcp
```

[Pulumi.staging.yaml](infrastructure/pulumi/gcp/Pulumi.staging.yaml) を編集：

```yaml
multicloud-auto-deploy:allowedOrigins: "https://yourdomain.com,https://www.yourdomain.com"
```

**注意**: カンマ区切りで複数ドメイン指定可能です。HTTPSを推奨します。

---

### 2. シークレット管理の確認

各クラウドのシークレットマネージャーに機密情報が安全に保存されているか確認：

- ✅ **AWS**: Secrets Manager (`multicloud-auto-deploy/staging/app-config`)
- ✅ **GCP**: Secret Manager (`multicloud-auto-deploy-staging-app-config`)
- ✅ **Azure**: Key Vault (`multicloud-auto-deploy-staging-kv`)

**確認コマンド**:

```bash
# AWS
aws secretsmanager describe-secret --secret-id multicloud-auto-deploy/staging/app-config

# GCP
gcloud secrets describe multicloud-auto-deploy-staging-app-config

# Azure
az keyvault secret list --vault-name multicloud-auto-deploy-staging-kv
```

---

### 3. WAF/DDoS保護の確認

- ✅ **AWS**: WAF v2有効、レート制限 2000 req/5分
- ✅ **GCP**: Cloud Armor有効、レート制限 1000 req/分
- ⚠️ **Azure**: WAFなし（Standard SKU、コスト重視）

**Azureで追加保護が必要な場合**:

- Application Gateway + WAF ($200-250/月)
- または Front Door Standard SKU に standalone WAF Policy を関連付け

---

## 🌐 ドメイン・DNS設定

### 4. カスタムドメインの設定（オプション）

各クラウドで異なるドメインを使用する場合の詳細な設定手順は、以下のガイドを参照してください：

**📕 [カスタムドメイン設定ガイド](CUSTOM_DOMAIN_SETUP.md)**

このガイドでは以下の内容を説明しています：

- **AWS CloudFront**: ACM証明書の作成、CloudFront alias設定、DNS CNAME設定
- **Azure Front Door**: カスタムドメイン追加、DNS検証、HTTPSの有効化
- **GCP Cloud CDN**: Managed SSL証明書の更新、DNS A レコード設定

#### 現在のエンドポイント

```bash
# 現在のエンドポイントを確認
cd infrastructure/pulumi/aws && pulumi stack output cloudfront_domain
cd infrastructure/pulumi/azure && pulumi stack output frontdoor_hostname
cd infrastructure/pulumi/gcp && pulumi stack output cdn_ip_address
```

#### Pulumi設定でカスタムドメインを有効化

```bash
# AWS: ACM証明書とドメインを設定
cd infrastructure/pulumi/aws
pulumi config set customDomain aws.yourdomain.com
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID
pulumi up

# GCP: ドメインを設定
cd infrastructure/pulumi/gcp
pulumi config set customDomain gcp.yourdomain.com
pulumi up

# Azure: Azure CLIで設定（詳細はガイド参照）
```

---

## 📊 監視・ログ設定

### 5. アラート設定（✅ 実装済み）

**実装状況**: 全クラウドで監視とアラート設定が完了しました。

#### AWS (9リソース)

- SNS Topic: メール通知設定
- CloudWatch Alarms:
  - Lambda関数エラー監視
  - API Gateway 4XX/5XX エラー監視
  - CloudFront エラー率監視
  - DynamoDB スロットリング監視

**アラート先**: `sat0sh1kawada@spa.nifty.com`

#### Azure (5リソース)

- Action Group: メール通知設定
- Metric Alerts:
  - Function App エラー監視
  - Front Door 4XX/5XX エラー監視
  - Cosmos DB RU消費監視

**アラート先**: `sat0sh1kawada@spa.nifty.com`

#### GCP (7リソース)

- Notification Channel: メール通知設定
- Alert Policies:
  - Cloud Function エラー監視
  - Load Balancer レイテンシ監視
  - Firestore 書き込み監視

**アラート先**: `sat0sh1kawada@spa.nifty.com`

**確認方法**:

```bash
# 各クラウドの監視リソースを確認
cd infrastructure/pulumi/aws && pulumi stack output | grep alarm
cd infrastructure/pulumi/azure && pulumi stack output | grep alert
cd infrastructure/pulumi/gcp && pulumi stack output | grep alert
```

---

## 🔐 認証・認可

### 6. 認証システムの実装（推奨）

現在、認証は実装されていません。本番環境では推奨：

- [ ] AWS Cognito
- [ ] GCP Firebase Authentication
- [ ] Azure AD B2C

---

## 💰 コスト確認

### 7. 予算アラートの設定

現在の月次推定コスト:

- AWS: $10-20/月
- GCP: $15-25/月
- Azure: $35-50/月
- **合計**: $60-95/月

**予算アラート設定**:

```bash
# AWS
aws budgets create-budget --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json

# GCP
gcloud billing budgets create --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="Multicloud Budget" --budget-amount=100

# Azure
az consumption budget create --budget-name multicloud-budget \
  --amount 100 --time-grain Monthly
```

---

## 🧪 動作確認

### 8. デプロイ後の動作テスト

各API エンドポイントの確認:

```bash
# AWS
curl https://[CloudFront-URL]/api/test

# GCP
curl https://[Load-Balancer-IP]/api/test

# Azure
curl https://[Function-App-URL]/api/HttpTrigger
```

Frontendの確認:

- AWS: CloudFront URL
- GCP: Load Balancer URL
- Azure: Front Door URL

---

## 📝 ドキュメント更新

### 9. 本番環境用ドキュメントの作成

- [ ]APIエンドポイント一覧
- [ ] 認証トークン取得方法
- [ ] エラーコード一覧
- [ ] 障害時の連絡先
- [ ] バックアップ・復旧手順

---

## ✅ デプロイ前最終確認

本番デプロイを実行する前に、以下を再確認してください：

- [ ] **CORS設定を実際のドメインに変更した**（最重要！）
- [ ] シークレットが安全に管理されている
- [ ] WAF/DDoS保護が有効（AWS/GCP）
- [ ] カスタムドメインとDNS設定が完了している（必要な場合）
- [ ] 監視・アラートを設定した（推奨）
- [ ] 認証システムを実装した（推奨）
- [ ] 予算アラートを設定した
- [ ] 動作テストが成功した
- [ ] 本番環境用ドキュメントを作成した

---

## 🚀 本番デプロイコマンド

すべてのチェック項目を確認後、以下のコマンドで本番デプロイを実行：

### AWS

```bash
cd infrastructure/pulumi/aws
pulumi stack select production  # 本番スタック作成・選択
pulumi up  # 変更内容を確認してデプロイ
```

### GCP

```bash
cd infrastructure/pulumi/gcp
pulumi stack select production
pulumi up
```

### Azure

```bash
cd infrastructure/pulumi/azure
pulumi stack select production
pulumi up
```

または GitHub Actions経由:

```bash
gh workflow run "Deploy to AWS" -f environment=production
gh workflow run "Deploy to GCP" -f environment=production
gh workflow run "Deploy to Azure" -f environment=production
```

---

## 📞 サポート

問題が発生した場合:

1. [SECURITY_ENHANCED.md](docs/SECURITY_ENHANCED.md) - セキュリティ設定詳細
2. [AZURE_DEPLOYMENT_FIX.md](docs/AZURE_DEPLOYMENT_FIX.md) - Azureデプロイトラブルシューティング
3. [ARCHITECTURE.md](docs/ARCHITECTURE.md) - アーキテクチャ全体図

---

**最終更新**: 2026-02-15
