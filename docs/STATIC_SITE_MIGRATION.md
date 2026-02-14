# フロントエンド静的サイト化とステージング戦略

## 🎯 目的

Reflexフロントエンドを静的HTML化し、CDN経由で配信することで：
- ✅ **コスト削減**: コンテナ実行コスト → 静的ホスティングコスト
- ✅ **パフォーマンス向上**: CDNキャッシュによる高速配信
- ✅ **スケーラビリティ**: CDNによる自動スケーリング
- ✅ **統一アーキテクチャ**: AWS構成と同じ静的サイト + CDN構成

## 📊 現状と課題

### 現在の構成（コンテナベース）

```
┌─────────────────┐
│ Reflex Frontend │──► Azure Container Apps / GCP Cloud Run
└─────────────────┘   - 動的サーバーサイドレンダリング
                      - コンテナ常時実行（コスト高）
                      - CDNキャッシュ不可
```

### 課題
1. **コスト**: コンテナ実行時間に応じた課金（月額 $20-50）
2. **パフォーマンス**: サーバーサイドレンダリングによるレイテンシ
3. **CDN**: 動的コンテンツのためCDNキャッシュが効かない
4. **一貫性**: AWS（S3 + CloudFront）と構成が異なる

## 🏗️ 提案する新構成

### 静的サイト + CDN構成

```
┌─────────────────────────────────────────────────┐
│ Build時                                         │
├─────────────────────────────────────────────────┤
│ reflex export --frontend-only                   │
│   ↓                                             │
│ .web/_static/ ← HTML/CSS/JSファイル生成         │
└─────────────────────────────────────────────────┘
                    ↓ Deploy
┌─────────────────────────────────────────────────┐
│ 【AWS】                                         │
│ S3 Bucket (静的ウェブサイト)                    │
│   ↓                                             │
│ CloudFront CDN                                  │
├─────────────────────────────────────────────────┤
│ 【Azure】                                       │
│ Blob Storage (静的ウェブサイト)                 │
│   ↓                                             │
│ Azure CDN / Front Door                          │
├─────────────────────────────────────────────────┤
│ 【GCP】                                         │
│ Cloud Storage Bucket (ウェブサイト構成)         │
│   ↓                                             │
│ Cloud CDN + Load Balancer                       │
└─────────────────────────────────────────────────┘
```

### コスト比較

| 構成 | 月額コスト（目安） | スケーラビリティ |
|------|-------------------|-----------------|
| **現在**: Container Apps/Cloud Run | $20-50 | 制限あり |
| **提案**: 静的サイト + CDN | $1-5 | CDNで自動 |

## 🎭 ステージング戦略

### 環境分離

```
┌─────────────────────────────────────────────────┐
│ staging (検証環境)                               │
├─────────────────────────────────────────────────┤
│ - ドメイン: staging.multicloud-auto-deploy.com  │
│ - API: staging-api.*.run.app                    │
│ - 自動デプロイ: main ブランチへのpush時         │
└─────────────────────────────────────────────────┘
                    ↓ 承認後
┌─────────────────────────────────────────────────┐
│ production (本番環境)                            │
├─────────────────────────────────────────────────┤
│ - ドメイン: www.multicloud-auto-deploy.com      │
│ - API: prod-api.*.run.app                       │
│ - 手動承認後デプロイ: タグpush時                 │
└─────────────────────────────────────────────────┘
```

### デプロイフロー

```yaml
# 自動デプロイ（staging）
main ブランチへのpush
  ↓
GitHub Actions トリガー
  ↓
ビルド → テスト → staging環境デプロイ

# 承認デプロイ（production）
v1.0.0 などのタグpush
  ↓
GitHub Actions トリガー
  ↓
ビルド → テスト → 承認待ち → production環境デプロイ
```

## 🔧 実装手順

### Phase 1: 静的サイト生成の確認

1. **Reflexの静的エクスポート**
   ```bash
   cd services/frontend_reflex
   reflex export --frontend-only
   # または
   reflex export --no-zip
   ```

2. **出力確認**
   ```bash
   ls -la .web/_static/
   # index.html, _app/*, assets/* など
   ```

### Phase 2: Azure静的サイト構成

```hcl
# Terraform構成例
resource "azurerm_storage_account" "frontend" {
  name                     = "mcadstaging"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  static_website {
    index_document     = "index.html"
    error_404_document = "error.html"
  }
}

resource "azurerm_cdn_profile" "frontend" {
  name                = "mcad-staging-cdn"
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  sku                 = "Standard_Microsoft"
}

resource "azurerm_cdn_endpoint" "frontend" {
  name                = "mcad-staging-frontend"
  profile_name        = azurerm_cdn_profile.frontend.name
  resource_group_name = azurerm_resource_group.main.name
  location            = "global"
  
  origin {
    name      = "primary"
    host_name = azurerm_storage_account.frontend.primary_web_host
  }
}
```

### Phase 3: GCP静的サイト構成

```hcl
# Terraform構成例
resource "google_storage_bucket" "frontend" {
  name     = "mcad-staging-frontend"
  location = "ASIA"
  
  website {
    main_page_suffix = "index.html"
    not_found_page   = "error.html"
  }
  
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "public" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_compute_backend_bucket" "frontend" {
  name        = "mcad-staging-frontend"
  bucket_name = google_storage_bucket.frontend.name
  enable_cdn  = true
}

resource "google_compute_url_map" "frontend" {
  name            = "mcad-staging-frontend"
  default_service = google_compute_backend_bucket.frontend.id
}

resource "google_compute_target_https_proxy" "frontend" {
  name    = "mcad-staging-frontend"
  url_map = google_compute_url_map.frontend.id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend.id]
}

resource "google_compute_global_forwarding_rule" "frontend" {
  name       = "mcad-staging-frontend"
  target     = google_compute_target_https_proxy.frontend.id
  port_range = "443"
  ip_address = google_compute_global_address.frontend.address
}
```

### Phase 4: CI/CDワークフロー更新

```yaml
# .github/workflows/deploy-static-frontend.yml
name: Deploy Static Frontend

on:
  push:
    branches: [main]
    paths:
      - 'services/frontend_reflex/**'
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options:
          - staging
          - production

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd services/frontend_reflex
          pip install -r requirements.txt
      
      - name: Build static site
        run: |
          cd services/frontend_reflex
          reflex export --frontend-only --no-zip
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-static
          path: services/frontend_reflex/.web/_static/
  
  deploy-azure:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: frontend-static
      
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy to Blob Storage
        run: |
          az storage blob upload-batch \
            --account-name ${{ secrets.AZURE_STORAGE_ACCOUNT }} \
            --destination '$web' \
            --source . \
            --overwrite
      
      - name: Purge CDN
        run: |
          az cdn endpoint purge \
            --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }} \
            --profile-name ${{ secrets.AZURE_CDN_PROFILE }} \
            --name ${{ secrets.AZURE_CDN_ENDPOINT }} \
            --content-paths '/*'
  
  deploy-gcp:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: frontend-static
      
      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS }}
      
      - name: Deploy to Cloud Storage
        run: |
          gsutil -m rsync -r -d . gs://${{ secrets.GCP_FRONTEND_BUCKET }}
      
      - name: Set cache control
        run: |
          gsutil -m setmeta -h "Cache-Control:public, max-age=3600" \
            gs://${{ secrets.GCP_FRONTEND_BUCKET }}/**.html
          gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" \
            gs://${{ secrets.GCP_FRONTEND_BUCKET }}/**/*.js
          gsutil -m setmeta -h "Cache-Control:public, max-age=31536000" \
            gs://${{ secrets.GCP_FRONTEND_BUCKET }}/**/*.css
```

## 🔐 必要なGitHub Secrets（追加分）

### Azure
- `AZURE_STORAGE_ACCOUNT`: Blob Storageアカウント名
- `AZURE_CDN_PROFILE`: CDNプロファイル名
- `AZURE_CDN_ENDPOINT`: CDNエンドポイント名

### GCP
- `GCP_FRONTEND_BUCKET`: Cloud Storageバケット名
- `GCP_LOAD_BALANCER`: Load Balancer名（オプション）

## 📈 移行ロードマップ

### Week 1: 準備と検証
- [ ] Reflex静的エクスポートのテスト
- [ ] 静的サイトのローカル確認
- [ ] API接続の動作確認

### Week 2: インフラ構築
- [ ] Azure Blob Storage + CDN作成
- [ ] GCP Cloud Storage + CDN作成
- [ ] DNS設定（staging環境）

### Week 3: CI/CD実装
- [ ] 静的サイトデプロイワークフロー作成
- [ ] staging環境への自動デプロイ設定
- [ ] production環境への承認デプロイ設定

### Week 4: テストと本番移行
- [ ] staging環境でのE2Eテスト
- [ ] パフォーマンステスト
- [ ] production環境への移行
- [ ] 旧コンテナ環境の削除

## 🎯 期待される効果

### コスト削減
- **現在**: Container Apps/Cloud Run: ~$30/月
- **移行後**: Blob Storage + CDN: ~$2/月
- **削減率**: 約93%

### パフォーマンス向上
- **TTFB**: 500ms → 50ms（CDNキャッシュ時）
- **可用性**: 99.9% → 99.99%（CDNによる）
- **スケーラビリティ**: 手動スケール → CDN自動スケール

### 運用改善
- **デプロイ時間**: 5分 → 30秒
- **ロールバック**: コンテナ再デプロイ → ストレージバージョン切り替え
- **監視**: コンテナメトリクス → CDNメトリクス

## 🔄 ロールバック戦略

```bash
# Azure: Blob Storageスナップショット
az storage blob snapshot --account-name $STORAGE_ACCOUNT \
  --container-name '$web' --name index.html

# GCP: Cloud Storageバージョニング
gsutil versioning set on gs://$BUCKET_NAME
gsutil ls -a gs://$BUCKET_NAME/index.html  # バージョン一覧
```

## 📚 参考資料

- [Reflex Export Doc](https://reflex.dev/docs/hosting/self-hosting/#exporting-a-static-site)
- [Azure Static Website](https://learn.microsoft.com/azure/storage/blobs/storage-blob-static-website)
- [GCS Static Website](https://cloud.google.com/storage/docs/hosting-static-website)
- [Azure CDN](https://learn.microsoft.com/azure/cdn/)
- [Cloud CDN](https://cloud.google.com/cdn/docs)
