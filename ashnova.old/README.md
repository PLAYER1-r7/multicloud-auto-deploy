# Ashnova - マルチクラウド静的ウェブサイト

OpenTofuを使用して、AWS・Azure・Google Cloudに静的ウェブサイトをデプロイするプロジェクトです。

## 🌐 サポートするクラウドプロバイダー

- ✅ **AWS**: S3 + CloudFront
- ✅ **Azure**: Storage Account + Front Door
- ✅ **Google Cloud**: Cloud Storage + Cloud CDN

## 📁 プロジェクト構造

```
ashnova/
├── aws/
│   ├── terraform/      # AWS用OpenTofu設定
│   ├── website/        # 静的ウェブサイトファイル
│   ├── deploy.sh       # AWSデプロイスクリプト
│   └── README.md       # AWS詳細ドキュメント
├── azure/
│   ├── terraform/      # Azure用OpenTofu設定
│   ├── deploy.sh       # Azureデプロイスクリプト
│   └── README.md       # Azure詳細ドキュメント
└── gcp/
    ├── terraform/      # GCP用OpenTofu設定
    ├── deploy.sh       # GCPデプロイスクリプト
    └── README.md       # GCP詳細ドキュメント
```

## 🚀 クイックスタート

### AWS

```bash
cd aws
./deploy.sh
```

詳細: [AWS README](aws/README.md)

### Azure

```bash
cd azure
./deploy.sh
```

詳細: [Azure README](azure/README.md)

### Google Cloud

```bash
cd gcp
./deploy.sh
```

詳細: [GCP README](gcp/README.md)

## 📋 前提条件

### 共通

- OpenTofu >= 1.0

### AWS

- AWS CLI設定済み（プロファイル: satoshi）
- 必要な権限: S3、CloudFront、IAM

### Azure

- Azure CLI ログイン済み
- 必要な権限: Resource Group、Storage、Front Door

### Google Cloud

- Google Cloud SDK設定済み
- プロジェクトID設定済み
- 必要なAPI有効化: Compute Engine、Cloud Storage

## 🔧 各クラウドの構成

| クラウド | ストレージ      | CDN/配信       | HTTPS      | 認証   |
| -------- | --------------- | -------------- | ---------- | ------ |
| AWS      | S3              | CloudFront     | ACM        | OAC    |
| Azure    | Storage Account | Front Door     | マネージド | Public |
| GCP      | Cloud Storage   | Cloud CDN + LB | マネージド | IAM    |

## 💰 コスト比較

### 低トラフィック（月100GB転送）の概算

- **AWS**: $5-10/月（S3 + CloudFront）
- **Azure**: $5-10/月（Storage + Front Door Standard）
- **GCP**: $5-10/月（Storage + Cloud CDN）

※実際のコストは使用量、リージョン、キャッシュヒット率などで変動します。

### コスト最適化のヒント

1. CDNを無効化（各プロバイダーで`enable_cdn = false`）
2. 単一リージョンを使用
3. 適切なキャッシュTTLを設定
4. 不要時はリソースを削除（`tofu destroy`）

## 🔒 セキュリティ

### AWS

- S3バケットへの直接アクセス制限（OAC使用）
- CloudFront経由のみアクセス可能
- HTTPS強制リダイレクト

### Azure

- Storage Accountパブリックアクセス
- Front Door経由でHTTPS自動有効化
- マネージドTLS証明書

### GCP

- Cloud Storageパブリック読み取り
- カスタムドメイン時にHTTPS自動有効化
- マネージドSSL証明書

## 🌐 カスタムドメイン設定

各クラウドプロバイダーでカスタムドメインをサポートしています。

### AWS

Route 53または外部DNSでCNAMEレコードを設定

### Azure

Front Door Custom Domainを使用

### GCP

Aレコードで固定IPを設定

詳細は各プロバイダーのREADMEを参照してください。

## 🗑️ リソースのクリーンアップ

各ディレクトリで：

```bash
cd <aws|azure|gcp>/terraform
tofu destroy
```

## 📊 機能比較

| 機能             | AWS     | Azure   | GCP     |
| ---------------- | ------- | ------- | ------- |
| 自動HTTPS        | ✅      | ✅      | ✅\*    |
| カスタムドメイン | ✅      | ✅      | ✅      |
| グローバルCDN    | ✅      | ✅      | ✅      |
| 無料枠           | Limited | Limited | Limited |
| デプロイ速度     | 中      | 中      | 中      |
| 設定の複雑さ     | 中      | 低      | 高      |

\*GCPはカスタムドメイン設定時のみHTTPS

## 🛠️ 開発ワークフロー

1. ウェブサイトファイルを`aws/website/`に配置
2. 各クラウドのディレクトリで設定を確認
3. デプロイスクリプトを実行
4. 出力されたURLで動作確認

## 📚 ドキュメント

- [AWS詳細ガイド](aws/README.md)
- [Azure詳細ガイド](azure/README.md)
- [Google Cloud詳細ガイド](gcp/README.md)

## 🤝 貢献

このプロジェクトはOpenTofuを使用したマルチクラウドデプロイメントの参考実装です。

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## ⚠️ 注意事項

- デプロイ前に各クラウドの料金を確認してください
- 不要なリソースは必ず削除してください
- 本番環境では適切なセキュリティ設定を行ってください
- IAMポリシー/権限は最小権限の原則に従ってください
