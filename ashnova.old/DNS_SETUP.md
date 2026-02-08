# DNS設定手順 - ashnova.jp

このドキュメントでは、ashnova.jpドメインで各クラウドプロバイダーのウェブサイトにアクセスできるようにするためのDNS設定手順を説明します。

## 概要

各サブドメインとクラウドプロバイダーの対応：

- `www.aws.ashnova.jp` → AWS CloudFront
- `www.azure.ashnova.jp` → Azure Front Door
- `www.gcp.ashnova.jp` → Google Cloud Load Balancer

## 前提条件

1. OpenTofuで各クラウドのインフラストラクチャをデプロイ済み
2. ashnova.jpドメインのDNS設定を管理できる権限がある

## 設定手順

### 1. AWS (www.aws.ashnova.jp)

#### 1.1 インフラストラクチャのデプロイ

```bash
cd aws/terraform
tofu apply
```

デプロイ後、以下のコマンドでDNS設定に必要な情報を取得します：

```bash
tofu output acm_certificate_validation_records
tofu output cloudfront_domain_name
```

#### 1.2 ACM証明書の検証レコードを追加

ACM証明書の検証のため、以下のDNSレコードを追加します：

**レコードタイプ**: CNAME  
**名前**: `tofu output`で表示されたvalidation recordのname  
**値**: `tofu output`で表示されたvalidation recordのvalue

例：

```
名前: _abc123.www.aws.ashnova.jp
タイプ: CNAME
値: _xyz456.acm-validations.aws.
```

#### 1.3 証明書の検証完了を待つ

DNSレコード追加後、ACMが証明書を自動的に検証します（通常5〜30分）。

検証状況の確認：

```bash
aws acm describe-certificate \
  --certificate-arn $(cd aws/terraform && tofu output -raw acm_certificate_arn) \
  --region us-east-1 \
  --profile satoshi
```

#### 1.4 CNAMEレコードを追加

証明書の検証が完了したら、以下のCNAMEレコードを追加します：

**レコードタイプ**: CNAME  
**名前**: `www.aws.ashnova.jp`  
**値**: CloudFrontドメイン名（例：d2w2fmi85qbw24.cloudfront.net）

```bash
# CloudFrontドメイン名の確認
cd aws/terraform
tofu output -raw cloudfront_domain_name
```

---

### 2. Azure (www.azure.ashnova.jp)

#### 2.1 インフラストラクチャのデプロイ

```bash
cd azure/terraform
tofu apply
```

デプロイ後、以下のコマンドでDNS設定に必要な情報を取得します：

```bash
tofu output custom_domain_validation_record
tofu output custom_domain_cname
```

#### 2.2 TXT検証レコードを追加

カスタムドメインの検証のため、以下のDNSレコードを追加します：

**レコードタイプ**: TXT  
**名前**: `_dnsauth.www.azure.ashnova.jp`  
**値**: `tofu output`で表示されたvalidation token

例：

```
名前: _dnsauth.www.azure.ashnova.jp
タイプ: TXT
値: abc123def456...
```

#### 2.3 CNAMEレコードを追加

同時に、以下のCNAMEレコードも追加します：

**レコードタイプ**: CNAME  
**名前**: `www.azure.ashnova.jp`  
**値**: Front Doorエンドポイント（例：fde-ashnova-sc86onhz-dzgubugxfafkanaq.z01.azurefd.net）

```bash
# Front Doorエンドポイントの確認
cd azure/terraform
tofu output -raw frontdoor_endpoint_host
```

#### 2.4 証明書のプロビジョニング完了を待つ

DNSレコード追加後、Azureが自動的にマネージド証明書をプロビジョニングします（通常5〜30分）。

検証状況の確認：

```bash
cd azure/terraform
az afd custom-domain show \
  --resource-group $(tofu output -raw resource_group_name) \
  --profile-name $(az afd profile list -g $(tofu output -raw resource_group_name) --query "[0].name" -o tsv) \
  --custom-domain-name $(echo "www.azure.ashnova.jp" | tr '.' '-') \
  --query "{domainValidationState:domainValidationState, validationProperties:validationProperties}" \
  -o json
```

---

### 3. Google Cloud (www.gcp.ashnova.jp)

#### 3.1 インフラストラクチャのデプロイ

```bash
cd gcp/terraform
tofu apply
```

デプロイ後、以下のコマンドでDNS設定に必要な情報を取得します：

```bash
tofu output load_balancer_ip
tofu output dns_configuration
```

#### 3.2 Aレコードを追加

以下のAレコードを追加します：

**レコードタイプ**: A  
**名前**: `www.gcp.ashnova.jp`  
**値**: Load BalancerのIPアドレス

```bash
# IPアドレスの確認
cd gcp/terraform
tofu output -raw load_balancer_ip
```

例：

```
名前: www.gcp.ashnova.jp
タイプ: A
値: 34.95.112.162
```

#### 3.3 SSL証明書のプロビジョニング完了を待つ

DNSレコード追加後、Google Cloudが自動的にマネージドSSL証明書をプロビジョニングします（通常10〜60分）。

証明書の状態確認：

```bash
cd gcp/terraform
tofu output ssl_certificate_status
```

または：

```bash
gcloud compute ssl-certificates describe ashnova-production-cert \
  --global \
  --project ashnova \
  --format="value(managed.status)"
```

ステータスが `ACTIVE` になれば完了です。

---

## DNS設定例（サマリー）

ashnova.jpゾーンに以下のレコードを追加します：

### AWS検証用

```
_abc123.www.aws.ashnova.jp    CNAME    _xyz456.acm-validations.aws.
```

### AWS本番

```
www.aws.ashnova.jp            CNAME    d2w2fmi85qbw24.cloudfront.net
```

### Azure検証用

```
_dnsauth.www.azure.ashnova.jp TXT      abc123def456...
```

### Azure本番

```
www.azure.ashnova.jp          CNAME    fde-ashnova-sc86onhz-dzgubugxfafkanaq.z01.azurefd.net
```

### Google Cloud

```
www.gcp.ashnova.jp            A        34.95.112.162
```

## 検証方法

DNS設定が反映された後、以下のコマンドで動作を確認できます：

```bash
# DNS解決の確認
dig www.aws.ashnova.jp
dig www.azure.ashnova.jp
dig www.gcp.ashnova.jp

# HTTPSアクセスの確認
curl -I https://www.aws.ashnova.jp
curl -I https://www.azure.ashnova.jp
curl -I https://www.gcp.ashnova.jp
```

## トラブルシューティング

### 証明書の検証が進まない場合

1. DNSレコードが正しく設定されているか確認

   ```bash
   dig _abc123.www.aws.ashnova.jp CNAME  # AWS
   dig _dnsauth.www.azure.ashnova.jp TXT  # Azure
   dig www.gcp.ashnova.jp A               # GCP
   ```

2. DNS伝播に時間がかかる場合があります（最大48時間、通常は数分〜数時間）

3. 各クラウドプロバイダーのコンソールで証明書のステータスを確認

### HTTPS接続エラーが出る場合

- 証明書がまだプロビジョニング中の可能性があります
- 証明書のステータスをoutputコマンドで確認してください
- プロビジョニング完了まで待ってから再度アクセスしてください

### DNS伝播状況の確認

オンラインツールで世界中のDNS伝播状況を確認できます：

- https://www.whatsmydns.net/
- https://dnschecker.org/

## 注意事項

1. **DNS TTL**: DNSレコードのTTL（Time To Live）を短く設定しておくと、変更時の反映が早くなります（推奨：300秒〜3600秒）

2. **証明書の自動更新**: すべてのクラウドプロバイダーで自動更新が有効になっていますが、DNSレコードを削除しないよう注意してください

3. **コスト**: カスタムドメイン使用による追加コストはほとんどありませんが、SSL証明書とCDN利用のコストは発生します

4. **削除時の注意**: インフラを削除する前に、DNSレコードを削除または更新してください

## 参考リンク

- [AWS ACM証明書検証](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)
- [Azure Front Doorカスタムドメイン](https://learn.microsoft.com/ja-jp/azure/frontdoor/standard-premium/how-to-add-custom-domain)
- [GCPマネージドSSL証明書](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs)
