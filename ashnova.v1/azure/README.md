# Ashnova Static Website - Azure Deployment

このプロジェクトは、OpenTofuを使用してAzure上に静的ウェブサイトをデプロイします。

## 📋 前提条件

- OpenTofu がインストールされていること
- Azure CLI がインストールされ、ログイン済みであること
- 適切なAzure権限（Resource Group、Storage Account、CDNの作成権限）

## 🚀 デプロイ手順

### 1. Azure CLIでログイン

```bash
az login

# サブスクリプションの確認
az account list --output table

# 使用するサブスクリプションを設定（複数ある場合）
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### 2. OpenTofuの初期化

```bash
cd azure/terraform
tofu init
```

### 3. 設定の確認

`variables.tf`で設定を確認・変更できます：

- `azure_location`: Azureリージョン（デフォルト: japaneast）
- `project_name`: プロジェクト名
- `environment`: 環境名
- `enable_cdn`: Azure CDNの有効/無効

### 4. 実行プランの確認

```bash
tofu plan
```

### 5. リソースのデプロイ

```bash
tofu apply
```

### 6. ウェブサイトファイルのアップロード

デプロイ完了後、出力されるStorage Account名を使用してファイルをアップロードします：

```bash
# Storage Account名を取得
STORAGE_ACCOUNT=$(tofu output -raw storage_account_name)

# ウェブサイトファイルをアップロード
az storage blob upload-batch \
  --account-name $STORAGE_ACCOUNT \
  --destination '$web' \
  --source ../aws/website \
  --overwrite

# CDNのキャッシュをパージ（CDNを使用している場合）
RESOURCE_GROUP=$(tofu output -raw resource_group_name)
az cdn endpoint purge \
  --resource-group $RESOURCE_GROUP \
  --profile-name $(az cdn profile list -g $RESOURCE_GROUP --query "[0].name" -o tsv) \
  --name $(az cdn endpoint list -g $RESOURCE_GROUP --profile-name $(az cdn profile list -g $RESOURCE_GROUP --query "[0].name" -o tsv) --query "[0].name" -o tsv) \
  --content-paths "/*"
```

### 7. ウェブサイトにアクセス

```bash
# ウェブサイトのURLを取得
tofu output website_url
```

## 🎯 簡単デプロイ

自動デプロイスクリプトを使用：

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/azure
./deploy.sh
```

## 📁 ディレクトリ構造

```
azure/
├── terraform/          # OpenTofu設定ファイル
│   ├── provider.tf    # プロバイダー設定
│   ├── variables.tf   # 変数定義
│   ├── main.tf        # メインリソース定義
│   └── outputs.tf     # 出力値
└── deploy.sh          # デプロイスクリプト
```

ウェブサイトファイルは`../aws/website/`を共有使用します。

## 🔧 リソース構成

- **Resource Group**: リソースのコンテナ
- **Storage Account**: 静的ウェブサイトホスティング（$webコンテナ）
- **CDN Profile & Endpoint**: グローバルCDN（オプション）

## 💰 コスト最適化

### Storage Account

- **account_tier**: Standard（低コスト）
- **account_replication_type**: LRS（ローカル冗長）

### CDN

- **SKU**: Standard_Microsoft（基本的な機能で十分）
- CDNを無効にする: `enable_cdn = false`

### コスト見積もり

- Storage Account: 数円/月（データ量による）
- CDN: トラフィック量に応じて課金
- 無料枠: Storage Accountには無料枠あり

## 🗑️ リソースの削除

```bash
cd azure/terraform
tofu destroy
```

⚠️ **注意**: リソースグループ内のすべてのリソースが削除されます。

## 🔒 セキュリティ

- **HTTPS**: CDN経由で自動的にHTTPSが有効
- **アクセス制御**: Storage Accountは匿名読み取りアクセスを許可（静的サイト用）
- **CDN**: HTTP to HTTPSリダイレクトを自動設定

## 🌐 カスタムドメインの設定

### 1. DNSレコードの追加

カスタムドメインのDNS設定で、以下のCNAMEレコードを追加：

```
CNAME: www -> <cdn-endpoint-fqdn>
```

### 2. OpenTofuで設定

`variables.tf`または`terraform.tfvars`で：

```hcl
custom_domain = "www.example.com"
enable_https  = true
```

### 3. HTTPSの有効化

```bash
az cdn custom-domain enable-https \
  --resource-group <resource-group> \
  --profile-name <cdn-profile> \
  --endpoint-name <cdn-endpoint> \
  --name <custom-domain-name>
```

## 📊 監視とログ

### ストレージメトリクスの確認

```bash
az monitor metrics list \
  --resource $STORAGE_ACCOUNT \
  --resource-type Microsoft.Storage/storageAccounts \
  --metric "Transactions"
```

### CDNログの有効化

```bash
az cdn endpoint update \
  --resource-group $RESOURCE_GROUP \
  --profile-name $CDN_PROFILE \
  --name $CDN_ENDPOINT \
  --enable-logging true
```

## ⚙️ 高度な設定

### CDN ルールエンジン

カスタムキャッシュルールやリダイレクトを`main.tf`の`delivery_rule`ブロックで設定できます。

### Storage Account設定

- 静的ウェブサイトのエラードキュメント設定
- CORS設定
- カスタムドメイン設定

## 🆚 AWS vs Azure 比較

| 機能       | AWS        | Azure              |
| ---------- | ---------- | ------------------ |
| ストレージ | S3         | Storage Account    |
| CDN        | CloudFront | Azure CDN          |
| 認証       | OAC        | パブリックアクセス |
| HTTPS      | ACM証明書  | CDN管理証明書      |
| 価格       | 従量課金   | 従量課金           |
