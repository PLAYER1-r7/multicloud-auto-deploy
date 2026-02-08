# Ashnova Static Website - Google Cloud Deployment

このプロジェクトは、OpenTofuを使用してGoogle Cloud上に静的ウェブサイトをデプロイします。

## 📋 前提条件

- OpenTofu がインストールされていること
- Google Cloud SDK (gcloud) がインストールされ、ログイン済みであること
- GCPプロジェクトが作成されていること
- 適切なGCP権限（Storage、Compute Engineの作成権限）

## 🚀 デプロイ手順

### 1. Google Cloud CLIでログイン

```bash
# 認証情報の設定
gcloud auth application-default login

# プロジェクトの設定
gcloud config set project YOUR_PROJECT_ID

# 確認
gcloud config list
```

### 2. 必要なAPIの有効化

```bash
# Compute Engine API（Load BalancerとCDN用）
gcloud services enable compute.googleapis.com

# Cloud Storage API
gcloud services enable storage.googleapis.com
```

### 3. OpenTofuの初期化と設定

```bash
cd gcp/terraform

# プロジェクトIDを設定
cat > terraform.tfvars <<EOF
gcp_project_id = "YOUR_PROJECT_ID"
EOF

# 初期化
tofu init
```

### 4. 実行プランの確認

```bash
tofu plan
```

### 5. リソースのデプロイ

```bash
tofu apply
```

### 6. ウェブサイトファイルのアップロード

デプロイ完了後、出力されるバケット名を使用してファイルをアップロードします：

```bash
# バケット名を取得
BUCKET_NAME=$(tofu output -raw bucket_name)

# ウェブサイトファイルをアップロード
gcloud storage cp --recursive ../aws/website/* gs://$BUCKET_NAME/

# コンテンツタイプを設定
gcloud storage objects update gs://$BUCKET_NAME/index.html --content-type="text/html"
gcloud storage objects update gs://$BUCKET_NAME/error.html --content-type="text/html"
```

### 7. ウェブサイトにアクセス

```bash
# ウェブサイトのURLを取得
tofu output website_url
```

## 🎯 簡単デプロイ

自動デプロイスクリプトを使用：

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/gcp
./deploy.sh
```

## 📁 ディレクトリ構造

```
gcp/
├── terraform/          # OpenTofu設定ファイル
│   ├── provider.tf    # プロバイダー設定
│   ├── variables.tf   # 変数定義
│   ├── main.tf        # メインリソース定義
│   ├── outputs.tf     # 出力値
│   └── terraform.tfvars  # プロジェクトID設定（自動生成）
└── deploy.sh          # デプロイスクリプト
```

## 🔧 リソース構成

### 基本構成

- **Cloud Storage Bucket**: 静的ウェブサイトホスティング
- **IAM Policy**: パブリック読み取りアクセス

### CDN有効時（enable_cdn = true）

- **Global Load Balancer**: HTTPSエンドポイント
- **Backend Bucket**: Cloud Storageへのバックエンド
- **Cloud CDN**: グローバルコンテンツ配信
- **Global IP Address**: 固定IPアドレス

### カスタムドメイン設定時

- **Managed SSL Certificate**: 自動SSL証明書
- **HTTPS Proxy**: HTTPSトラフィック処理

## 💰 コスト最適化

### Storage

- **Location**: ASIA（マルチリージョン）または asia-northeast1（単一リージョン）
- **Storage Class**: Standard（デフォルト）

### Cloud CDN

- **Cache Mode**: CACHE_ALL_STATIC（静的コンテンツのみ）
- **TTL**: 3600秒（1時間）
- CDNを無効にする: `enable_cdn = false`

### コスト見積もり

- Cloud Storage: 数円/月（データ量による）
- Cloud CDN: トラフィック量とキャッシュヒット率に応じて課金
- Load Balancer: 使用時間とトラフィックで課金
- 無料枠: 月5GBストレージ、1GB北米エグレス

## 🗑️ リソースの削除

```bash
cd gcp/terraform
tofu destroy
```

⚠️ **注意**: バケット内のファイルも削除されます（force_destroy = true）。

## 🌐 カスタムドメインの設定

### 1. DNSレコードの追加

カスタムドメインのDNS設定で、Aレコードを追加：

```bash
# Load BalancerのIPアドレスを取得
tofu output load_balancer_ip

# DNSレコード例
# Type: A
# Name: @ または www
# Value: <load_balancer_ip>
```

### 2. OpenTofuで設定

`terraform.tfvars`に追加：

```hcl
custom_domain = "www.example.com"
```

### 3. 再デプロイ

```bash
tofu apply
```

SSL証明書のプロビジョニングには最大15分かかる場合があります。

## 🔒 セキュリティ

- **パブリックアクセス**: バケットは匿名読み取りを許可（静的サイト用）
- **HTTPS**: カスタムドメイン使用時に自動有効化
- **Managed Certificate**: Google管理のSSL証明書
- **Uniform Bucket-level Access**: バケットレベルのIAM制御

## 📊 監視とログ

### ストレージメトリクスの確認

```bash
# バケットの詳細を確認
gcloud storage buckets describe gs://$BUCKET_NAME

# オブジェクト一覧
gcloud storage ls gs://$BUCKET_NAME
```

### Load Balancerのログ

```bash
# Cloud Loggingでログを確認
gcloud logging read "resource.type=http_load_balancer" --limit 50
```

### CDNキャッシュ統計

GCPコンソール > ネットワークサービス > Cloud CDN で確認

## ⚙️ 高度な設定

### カスタムキャッシュ設定

`main.tf`の`cdn_policy`ブロックで調整：

```hcl
cdn_policy {
  cache_mode        = "CACHE_ALL_STATIC"
  client_ttl        = 3600    # クライアント側キャッシュ
  default_ttl       = 3600    # デフォルトキャッシュ
  max_ttl           = 86400   # 最大キャッシュ
  negative_caching  = true    # 404などもキャッシュ
  serve_while_stale = 86400   # 古いキャッシュ提供時間
}
```

### バケットのライフサイクル管理

古いバージョンの自動削除などを設定可能。

## 🆚 クラウドプロバイダー比較

| 機能       | AWS        | Azure            | GCP              |
| ---------- | ---------- | ---------------- | ---------------- |
| ストレージ | S3         | Storage Account  | Cloud Storage    |
| CDN        | CloudFront | Front Door       | Cloud CDN        |
| 認証       | OAC        | Public           | IAM              |
| HTTPS      | ACM        | マネージド証明書 | マネージド証明書 |
| LB         | CloudFront | Front Door       | Global LB        |
| 価格       | 従量課金   | 従量課金         | 従量課金         |

## 🔧 トラブルシューティング

### 権限エラー

必要な権限：

- `storage.buckets.create`
- `storage.buckets.get`
- `storage.objects.create`
- `compute.globalAddresses.create`
- `compute.backendBuckets.create`

### DNS設定の確認

```bash
# DNSレコードの確認
nslookup www.example.com

# SSL証明書の状態確認
gcloud compute ssl-certificates describe <certificate-name>
```

### CDNキャッシュのクリア

```bash
# 手動でキャッシュを無効化（GCPコンソールから）
# ネットワークサービス > Cloud CDN > キャッシュの無効化
```

## 📚 参考リンク

- [Cloud Storage 静的ウェブサイトホスティング](https://cloud.google.com/storage/docs/hosting-static-website)
- [Cloud CDN ドキュメント](https://cloud.google.com/cdn/docs)
- [Managed SSL Certificates](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs)
