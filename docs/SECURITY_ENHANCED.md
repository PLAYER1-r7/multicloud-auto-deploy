# セキュリティ強化ガイド

## 実装済みのセキュリティ機能

### 1. WAF/DDoS保護

#### AWS
- **AWS WAF v2** をCloudFrontに統合
- マネージドルールセット:
  - AWS Core Rule Set (CRS) - 一般的な脆弱性の保護
  - Known Bad Inputs Rule Set - 既知の不正入力のブロック
- レート制限: 5分間あたり2,000リクエスト/IP
- コスト: $5/月（Web ACL） + $2/月（2ルール） + $0.60/100万リクエスト

#### GCP
- **Cloud Armor** セキュリティポリシーをバックエンドバケットに適用
- レート制限: 1分間あたり1,000リクエスト/IP
- 違反時の措置: 10分間のBANクエスト
- Layer 7 DDoS防御を有効化
- コスト: $6/月（ポリシー） + $0.75/100万リクエスト

#### Azure
- **Azure Front Door Standard**（WAFなし）
- 基本的なCDN機能とHTTPS強制
- HTTPS→HTTPSリダイレクト
- コスト: $35/月
- ⚠️ 注意: StandardはWAF機能をサポートしていません。より高度なセキュリティが必要な場合は、Azure Application GatewayまたはPremiumへのアップグレードを検討してください。

### 2. HTTPS完全対応

#### AWS
- ✅ CloudFront: `viewer_protocol_policy="redirect-to-https"`
- ✅ マネージドSSL証明書（CloudFront default）
- ✅ TLS 1.2以上

#### GCP
- ✅ HTTPS Load Balancer with TargetHttpsProxy
- ✅ Managed SSL Certificate（カスタムドメイン用）
- ✅ HTTP→HTTPSリダイレクト（ポート80→443）
- ⚠️ 注意: カスタムドメインが必要（現在は`example.com`を使用）

#### Azure
- ✅ Azure Front Door: `forwarding_protocol="HttpsOnly"`
- ✅ `https_redirect="Enabled"`
- ✅ ストレージアカウント: `minimum_tls_version="TLS1_2"`

### 3. シークレット管理の統一

#### AWS Secrets Manager
```python
# シークレットの作成
aws.secretsmanager.Secret("app-secret",
    name="multicloud-auto-deploy/staging/app-config"
)

# Lambda環境変数
environment={
    "variables": {
        "SECRET_NAME": "multicloud-auto-deploy/staging/app-config"
    }
}
```

アクセス方法:
```python
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId=os.environ['SECRET_NAME'])
```

コスト: $0.40/月（シークレット） + $0.05/10,000 API呼び出し

#### GCP Secret Manager
```python
# シークレットの作成
gcp.secretmanager.Secret("app-secret",
    secret_id="multicloud-auto-deploy-staging-app-config"
)
```

アクセス方法:
```python
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
response = client.access_secret_version(request={"name": name})
```

コスト: $0.06/月（シークレット） + $0.03/10,000アクセス

#### Azure Key Vault
```python
# Key Vaultの作成
azure.keyvault.Vault("key-vault",
    vault_name="mcad-kv-{suffix}",
    properties=VaultPropertiesArgs(
        enable_rbac_authorization=True,
        enable_soft_delete=True
    )
)
```

アクセス方法:
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

client = SecretClient(vault_url=vault_uri, credential=DefaultAzureCredential())
secret = client.get_secret("app-config")
```

コスト: $0.03/10,000操作（シークレット自体は無料）

### 4. CORS設定の厳格化

デフォルトでは`*`（すべてのオリジン）を許可していますが、本番環境では実際のドメインに制限してください。

#### 設定方法

**Pulumi.staging.yaml**（または `Pulumi.production.yaml`）:
```yaml
config:
  multicloud-auto-deploy:allowedOrigins: "https://example.com,https://www.example.com"
```

複数のドメインをカンマ区切りで指定できます。

#### 適用される箇所
- AWS Lambda Function URL
- AWS API Gateway
- GCP Cloud Storage バケット

## 本番環境へのデプロイ前チェックリスト

### 必須対応

- [ ] **CORS設定**: `allowedOrigins`を実際のドメインに変更
  ```yaml
  multicloud-auto-deploy:allowedOrigins: "https://yourdomain.com"
  ```

- [ ] **GCP SSL証明書**: `example.com`を実際のドメインに変更
  ```python
  managed=gcp.compute.ManagedSslCertificateManagedArgs(
      domains=["your-actual-domain.com"],
  )
  ```

- [ ] **シークレット値の更新**:
  ```bash
  # AWS
  aws secretsmanager update-secret --secret-id multicloud-auto-deploy/production/app-config \
    --secret-string '{"database_url":"actual_value","api_key":"actual_value"}'
  
  # GCP
  echo -n '{"database_url":"actual_value"}' | \
    gcloud secrets versions add multicloud-auto-deploy-production-app-config --data-file=-
  
  # Azure
  az keyvault secret set --vault-name mcad-kv-prod \
    --name app-config --value '{"database_url":"actual_value"}'
  ```

- [ ] **Azure Key Vault**: ネットワークACLを厳格化
  ```python
  network_acls=NetworkRuleSetArgs(
      bypass="AzureServices",
      default_action="Deny",  # 本番環境では拒否
      ip_rules=[IpRuleArgs(value="YOUR_IP_ADDRESS")]
  )
  ```

### 推奨対応

- [ ] **AWS CloudWatch Alarms**: WAFメトリクスの監視
- [ ] **GCP Monitoring**: Cloud Armorのアラート設定
- [ ] **Azure Monitor**: Front Door WAFアラート設定
- [ ] **ログ集約**: すべてのWAFログを中央集約
- [ ] **定期的なセキュリティ監査**: 月次でルールを見直し

## コスト見積もり

### 月間コスト（低トラフィック想定）

| クラウド | 基本料金 | WAF | Secret管理 | 合計 |
|---------|---------|-----|-----------|------|
| AWS | $2-5 | $8-10 | $0.50 | **$10-20** |
| GCP | $10-15 | $7-10 | $0.10 | **$15-25** |
| Azure | $2-5 | - | $0.10 | **$35-50** |

⚠️ **注意**: Azure Front Door StandardはWAF機能をサポートしていません。より高度なセキュリティが必要な場合は、以下の選択肢を検討してください：
- **Azure Application Gateway** + WAF: $200-250/月（リージョナル）
- **Azure Front Door Premium**: $330/月（グローバル、フルWAF）
- **サードパーティWAF**: Cloudflare、Akamai等

## トラブルシューティング

### AWS WAF作成エラー
```
Error: WAF must be created in us-east-1 for CloudFront
```

**解決策**: コード内で`us-east-1`プロバイダーを使用（実装済み）

### GCP SSL証明書プロビジョニング失敗
```
Error: Certificate provisioning failed - domain verification
```

**解決策**: 
1. 実際のドメインを所有していることを確認
2. DNS A/AAAAレコードがLoad BalancerのIPを指していることを確認
3. プロビジョニングには最大30分かかる場合があります

### Azure Key Vault アクセス拒否
```
Error: Forbidden - Caller does not have permission
```

**解決策**: 
1. RBACロールを付与:
   ```bash
   az role assignment create --role "Key Vault Secrets Officer" \
     --assignee <user-or-service-principal-id> \
     --scope <key-vault-id>
   ```
2. または、アクセスポリシーモードに切り替え（`enable_rbac_authorization=False`）

## 次のステップ

1. **認証・認可の実装**: Cognito/Firebase Auth/Azure AD B2C
2. **監視・アラート**: すべてのWAFメトリクスを監視
3. **ログ分析**: セキュリティイベントの自動分析
4. **ペネトレーションテスト**: 定期的なセキュリティ評価

---

**更新日**: 2026年2月15日
**バージョン**: 1.0.0
