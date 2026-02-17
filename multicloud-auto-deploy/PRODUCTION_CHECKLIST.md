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
- またはFront Door Premium ($330/月) へアップグレード

---

## 🌐 ドメイン・DNS設定

### 4. カスタムドメインの設定（オプション）

#### GCP: HTTPS証明書
現在プレースホルダー（`example.com`）を使用しています。実際のドメインを設定する場合：

[infrastructure/pulumi/gcp/__main__.py](infrastructure/pulumi/gcp/__main__.py) (L115-120付近):
```python
managed_ssl_cert = gcp.compute.ManagedSslCertificate(
    f"{project_name}-{stack}-ssl-cert",
    managed=gcp.compute.ManagedSslCertificateManagedArgs(
        domains=["yourdomain.com", "www.yourdomain.com"],  # 実際のドメインに変更
    ),
)
```

DNS設定:
```bash
# GCPのロードバランサーIPアドレスを取得
cd infrastructure/pulumi/gcp
pulumi stack output loadBalancerIP

# DNSにAレコード追加
# yourdomain.com -> [Load Balancer IP]
```

#### Azure: Front Doorカスタムドメイン
```bash
az afd custom-domain create \
  --resource-group multicloud-auto-deploy-staging-rg \
  --profile-name multicloud-auto-deploy-staging-fd \
  --custom-domain-name yourdomain \
  --host-name yourdomain.com
```

---

## 📊 監視・ログ設定

### 5. アラート設定（推奨）

まだ実装されていない項目：
- [ ] CloudWatch/Cloud Monitoring/Azure Monitorアラート
- [ ] WAFブロック数の監視
- [ ] エラー率の閾値アラート
- [ ] コスト異常検知

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
