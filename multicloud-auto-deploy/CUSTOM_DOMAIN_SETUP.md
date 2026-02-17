# カスタムドメイン設定ガイド

各クラウドで異なるドメインを使用する際のカスタムドメイン設定手順です。

## 📋 現在のエンドポイント

### Staging環境

| クラウド | 種類 | 現在のエンドポイント | Distribution ID |
|---------|------|---------------------|-----------------|
| **AWS** | CloudFront | `d1tf3uumcm4bo1.cloudfront.net` | E1TBH4R432SZBZ |
| **Azure** | Front Door | `mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` | mcad-staging-d45ihd |
| **GCP** | Cloud CDN | `34.117.111.182` (IP address) | - |

### Production環境

| クラウド | 種類 | 現在のエンドポイント | Distribution ID |
|---------|------|---------------------|-----------------|
| **AWS** | CloudFront | `d1qob7569mn5nw.cloudfront.net` | E214XONKTXJEJD |
| **Azure** | Front Door | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | mcad-production-diev0w |
| **GCP** | Cloud CDN | `34.8.38.222` (IP address) | - |

---

## 🌐 ドメイン例

各クラウドで異なるドメインを使用する場合の例：

- **AWS**: `aws.yourdomain.com`
- **Azure**: `azure.yourdomain.com`
- **GCP**: `gcp.yourdomain.com`

または：

- **AWS**: `app-aws.example.com`
- **Azure**: `app-azure.example.com`
- **GCP**: `app-gcp.example.com`

---

## 1️⃣ AWS CloudFront カスタムドメイン設定

### 前提条件
- ドメイン所有権の確認
- AWS Route 53（推奨）または外部DNSプロバイダー

### 手順

#### ステップ1: ACM証明書の作成（us-east-1リージョン必須）

```bash
# ACM証明書をリクエスト
aws acm request-certificate \
  --domain-name aws.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# 証明書ARNを取得
CERT_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='aws.yourdomain.com'].CertificateArn" \
  --output text)

echo "Certificate ARN: $CERT_ARN"
```

#### ステップ2: DNS検証レコードの追加

```bash
# 検証レコード情報を取得
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# 出力例:
# {
#   "Name": "_abc123.aws.yourdomain.com",
#   "Type": "CNAME",
#   "Value": "_xyz456.acm-validations.aws."
# }
```

**DNSプロバイダーで設定**:
- レコードタイプ: `CNAME`
- 名前: `_abc123.aws.yourdomain.com`
- 値: `_xyz456.acm-validations.aws.`

#### ステップ3: Pulumi設定の更新

`infrastructure/pulumi/aws/__main__.py` の CloudFront Distribution部分を修正：

```python
# 証明書ARNを設定
cert_arn = config.get("acmCertificateArn")  # Pulumi configから取得
custom_domain = config.get("customDomain")  # 例: aws.yourdomain.com

cloudfront_kwargs = {
    # ... 既存の設定 ...
    "aliases": [custom_domain] if custom_domain else [],
    "viewer_certificate": aws.cloudfront.DistributionViewerCertificateArgs(
        acm_certificate_arn=cert_arn,
        ssl_support_method="sni-only",
        minimum_protocol_version="TLSv1.2_2021",
    ) if cert_arn else aws.cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True,
    ),
    # ... 残りの設定 ...
}
```

#### ステップ4: Pulumi設定を追加

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain aws.yourdomain.com
pulumi config set acmCertificateArn arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID
pulumi up
```

#### ステップ5: DNSにCNAMEレコードを追加

**Pulumi環境（production/staging）のCloudFrontドメインを確認**:
```bash
cd infrastructure/pulumi/aws
pulumi stack select production  # または staging
CLOUDFRONT_DOMAIN=$(pulumi stack output cloudfront_domain)
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
```

**Route 53の場合**:
```bash
# production環境の例
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "aws.yourdomain.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "d1qob7569mn5nw.cloudfront.net"}]
      }
    }]
  }'
```

**外部DNSプロバイダーの場合**:
- レコードタイプ: `CNAME`
- 名前: `aws.yourdomain.com`
- 値: 
  - Production: `d1qob7569mn5nw.cloudfront.net`
  - Staging: `d1tf3uumcm4bo1.cloudfront.net`

---

## 2️⃣ Azure Front Door カスタムドメイン設定

### 前提条件
- ドメイン所有権の確認
- Azure DNS（推奨）または外部DNSプロバイダー

### 手順

#### ステップ1: カスタムドメインの追加

**環境のリソース情報を取得**:
```bash
# Pulumi outputsから確認
cd infrastructure/pulumi/azure
pulumi stack select production  # または staging
FRONTDOOR_HOSTNAME=$(pulumi stack output frontdoor_hostname)
FRONTDOOR_PROFILE=$(pulumi stack output frontdoor_profile_name)
FRONTDOOR_ENDPOINT=$(pulumi stack output frontdoor_endpoint_name)
RESOURCE_GROUP=$(pulumi stack output resource_group_name)

echo "Front Door Hostname: $FRONTDOOR_HOSTNAME"
echo "Profile Name: $FRONTDOOR_PROFILE"
```

**カスタムドメインを作成**:
```bash
# Environment: production または staging
ENVIRONMENT="production"
RESOURCE_GROUP="multicloud-auto-deploy-${ENVIRONMENT}-rg"
PROFILE_NAME="multicloud-auto-deploy-${ENVIRONMENT}-fd"
CUSTOM_DOMAIN_NAME="azure-yourdomain"
HOSTNAME="azure.yourdomain.com"

# カスタムドメインを作成
az afd custom-domain create \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name $CUSTOM_DOMAIN_NAME \
  --host-name $HOSTNAME \
  --certificate-type ManagedCertificate
```

#### ステップ2: DNS検証レコードの追加

```bash
# 検証レコード情報を取得
az afd custom-domain show \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name $CUSTOM_DOMAIN_NAME \
  --query "validationProperties"

# 出力例:
# {
#   "validationToken": "abc123def456",
#   "expirationDate": "2026-02-24T..."
# }
```

**DNSプロバイダーで設定**:
- レコードタイプ: `TXT`
- 名前: `_dnsauth.azure.yourdomain.com`
- 値: `abc123def456` (validationToken)

#### ステップ3: エンドポイントへの関連付け

```bash
# Endpoint名を取得（production/stagingで異なる）
ENDPOINT_NAME=$(pulumi stack output frontdoor_endpoint_name)
echo "Endpoint Name: $ENDPOINT_NAME"

# カスタムドメインをエンドポイントに関連付け
az afd route create \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --endpoint-name $ENDPOINT_NAME \
  --route-name custom-domain-route \
  --origin-group-name default-origin-group \
  --supported-protocols Https \
  --custom-domains $CUSTOM_DOMAIN_NAME \
  --forwarding-protocol HttpsOnly \
  --https-redirect Enabled
```

#### ステップ4: DNSにCNAMEレコードを追加

**Front Door Hostnameを確認**:
```bash
cd infrastructure/pulumi/azure
pulumi stack select production  # または staging
FRONTDOOR_HOSTNAME=$(pulumi stack output frontdoor_hostname)
echo "Front Door Hostname: $FRONTDOOR_HOSTNAME"
```

**Azure DNSの場合**:
```bash
az network dns record-set cname set-record \
  --resource-group YOUR_DNS_RG \
  --zone-name yourdomain.com \
  --record-set-name azure \
  --cname $FRONTDOOR_HOSTNAME
```

**外部DNSプロバイダーの場合**:
- レコードタイプ: `CNAME`
- 名前: `azure.yourdomain.com`
- 値: 
  - Production: `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net`
  - Staging: `mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net`

#### ステップ5: HTTPSの有効化を確認

```bash
# カスタムドメインの状態を確認
az afd custom-domain show \
  --resource-group $RESOURCE_GROUP \
  --profile-name $PROFILE_NAME \
  --custom-domain-name $CUSTOM_DOMAIN_NAME \
  --query "{provisioningState, domainValidationState, deploymentStatus}"
```

---

## 3️⃣ GCP Cloud CDN カスタムドメイン設定

### 前提条件
- ドメイン所有権の確認
- Google Cloud DNS（推奨）または外部DNSプロバイダー

### 手順

#### ステップ1: Managed SSL証明書の更新

`infrastructure/pulumi/gcp/__main__.py` の SSL証明書部分を修正：

```python
# カスタムドメインを設定
custom_domain = config.get("customDomain")  # 例: gcp.yourdomain.com

managed_ssl_cert = gcp.compute.ManagedSslCertificate(
    f"{project_name}-{stack}-ssl-cert",
    managed=gcp.compute.ManagedSslCertificateManagedArgs(
        domains=[custom_domain] if custom_domain else ["example.com"],
    ),
    opts=pulumi.ResourceOptions(
        delete_before_replace=True,
    ),
)
```

#### ステップ2: Pulumi設定を更新してデプロイ

```bash
cd infrastructure/pulumi/gcp
pulumi config set customDomain gcp.yourdomain.com
pulumi up
```

**注意**: Managed SSL証明書のプロビジョニングには最大60分かかります。

#### ステップ3: DNSにAレコードを追加

**CDN IPアドレスを確認**:
```bash
cd infrastructure/pulumi/gcp
pulumi stack select production  # または staging
CDN_IP=$(pulumi stack output cdn_ip_address)
echo "CDN IP Address: $CDN_IP"
```

**Google Cloud DNSの場合**:
```bash
gcloud dns record-sets create gcp.yourdomain.com. \
  --zone=YOUR_ZONE_NAME \
  --type=A \
  --ttl=300 \
  --rrdatas=$CDN_IP
```

**外部DNSプロバイダーの場合**:
- レコードタイプ: `A`
- 名前: `gcp.yourdomain.com`
- 値: 
  - Production: `34.8.38.222`
  - Staging: `34.117.111.182`

#### ステップ4: SSL証明書のプロビジョニング確認

```bash
# 証明書の状態を確認（ACTIVEになるまで待つ）
gcloud compute ssl-certificates describe multicloud-auto-deploy-staging-ssl-cert \
  --global \
  --format="value(managed.status)"

# Expected: ACTIVE
```

**プロビジョニングに時間がかかる場合**:
- DNSレコードが正しく設定されているか確認
- DNS伝播を待つ（最大48時間、通常は数分～数時間）
- `dig gcp.yourdomain.com` でDNS解決を確認

---

## 🔄 CORS設定の更新

カスタムドメイン設定後、各クラウドのCORS設定を更新する必要があります。

### AWS

```bash
cd infrastructure/pulumi/aws
pulumi config set allowedOrigins "https://aws.yourdomain.com,http://localhost:5173"
pulumi up
```

### Azure

```bash
cd infrastructure/pulumi/azure
pulumi config set allowedOrigins "https://azure.yourdomain.com,http://localhost:5173"
# Azure Function Appの環境変数は手動更新が必要
```

### GCP

```bash
cd infrastructure/pulumi/gcp
pulumi config set allowedOrigins "https://gcp.yourdomain.com,http://localhost:5173"
# Cloud Functionの環境変数はgcloudで更新
```

---

## ✅ 動作確認

### 1. DNS解決の確認

```bash
# AWS
dig aws.yourdomain.com
nslookup aws.yourdomain.com

# Azure
dig azure.yourdomain.com
nslookup azure.yourdomain.com

# GCP
dig gcp.yourdomain.com
nslookup gcp.yourdomain.com
```

### 2. SSL証明書の確認

```bash
# SSL証明書の有効性をチェック
curl -vI https://aws.yourdomain.com
curl -vI https://azure.yourdomain.com
curl -vI https://gcp.yourdomain.com

# または
openssl s_client -connect aws.yourdomain.com:443 -servername aws.yourdomain.com < /dev/null
```

### 3. アプリケーションの確認

```bash
# フロントエンドへのアクセス
curl https://aws.yourdomain.com
curl https://azure.yourdomain.com
curl https://gcp.yourdomain.com

# APIへのアクセス（ヘルスチェック）
curl https://aws.yourdomain.com/health
curl https://azure.yourdomain.com/api/health
curl https://gcp.yourdomain.com/health
```

---

## 🔍 トラブルシューティング

### 証明書エラー

**問題**: SSL証明書エラーが発生する

**解決策**:
1. 証明書のステータスを確認
2. ドメインのaliasesが正しく設定されているか確認
3. CloudFront/Front Door/Cloud CDNで証明書が関連付けられているか確認

### DNS解決失敗

**問題**: ドメインが解決されない

**解決策**:
1. DNSレコードが正しく設定されているか確認
2. DNS伝播を待つ（最大48時間）
3. `dig @8.8.8.8 yourdomain.com` でGoogle DNSから確認
4. TTL値を確認（変更後は古いTTLが切れるまで待つ）

### GCP Managed SSL証明書がACTIVEにならない

**問題**: 証明書が長時間PROVISIONINGのまま

**解決策**:
1. DNSのAレコードが正しいIPアドレスを指しているか確認
2. ロードバランサーが正常に動作しているか確認
3. ドメインがグローバルに解決可能か確認（複数の場所から`dig`を実行）

### Azure Front Door検証失敗

**問題**: カスタムドメイン検証が失敗する

**解決策**:
1. TXTレコード（`_dnsauth`）が正しく設定されているか確認
2. validationTokenが正しいか確認
3. DNSの伝播を待つ
4. `dig TXT _dnsauth.azure.yourdomain.com` で確認

---

## 📝 各クラウドのコスト

| クラウド | 追加コスト |
|---------|-----------|
| **AWS** | ACM証明書: 無料<br>CloudFrontカスタムドメイン: 無料 |
| **Azure** | Front Door Managed Certificate: 無料<br>カスタムドメイン: 無料 |
| **GCP** | Managed SSL Certificate: 無料<br>ロードバランサーは既存 |

---

## 🎯 次のステップ

カスタムドメイン設定後に推奨される作業：

1. **監視アラートの更新**: 新しいドメインでの監視を設定
2. **CORS設定の検証**: ブラウザからアクセスして動作確認
3. **セキュリティヘッダーの追加**: HSTS、CSPなどの設定
4. **リダイレクト設定**: 旧エンドポイントから新ドメインへリダイレクト
5. **ドキュメント更新**: README.mdに新しいURLを記載

---

## 📚 参考リンク

- [AWS CloudFront - カスタムドメイン設定](https://docs.aws.amazon.com/ja_jp/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html)
- [Azure Front Door - カスタムドメイン](https://learn.microsoft.com/ja-jp/azure/frontdoor/standard-premium/how-to-add-custom-domain)
- [GCP - Managed SSL証明書](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs)
