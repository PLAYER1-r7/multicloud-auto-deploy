# エンドポイント一覧

## 🌐 本番環境エンドポイント

### AWS (ap-northeast-1)

| 項目 | 値 |
|-----|-----|
| **API Endpoint** | `https://52z731x570.execute-api.ap-northeast-1.amazonaws.com` |
| **Frontend URL** | `https://dx3l4mbwg1ade.cloudfront.net` |
| **Region** | ap-northeast-1 (東京) |
| **API Gateway ID** | 52z731x570 |
| **CloudFront ID** | E2GDU7Y7UGDV3S |
| **S3 Bucket** | multicloud-auto-deploy-staging-frontend |
| **Lambda Function** | multicloud-auto-deploy-staging-api |

**テスト**:
```bash
# API
curl https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/

# Frontend
curl -I https://dx3l4mbwg1ade.cloudfront.net/
```

---

### Azure (japaneast)

| 項目 | 値 |
|-----|-----|
| **API Endpoint** | `https://mcad-staging-api--0000004.livelycoast-fa9d3350.japaneast.azurecontainerapps.io` |
| **Frontend URL** | `https://multicloud-auto-deploy-staging-endpoint-deezaegrhyfzgsav.z01.azurefd.net` |
| **Region** | japaneast (東日本) |
| **Resource Group** | multicloud-auto-deploy-staging-rg |
| **Container App** | mcad-staging-api |
| **Storage Account** | mcadstagingfrontendXXXX |
| **Container Registry** | mcadstagingacr |
| **Front Door** | multicloud-auto-deploy-staging-frontdoor |

**テスト**:
```bash
# API
curl https://mcad-staging-api--0000004.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/

# Frontend
curl -I https://multicloud-auto-deploy-staging-endpoint-deezaegrhyfzgsav.z01.azurefd.net/
```

---

### GCP (asia-northeast1)

| 項目 | 値 |
|-----|-----|
| **API Endpoint** | `https://mcad-staging-api-son5b3ml7a-an.a.run.app` |
| **Frontend URL** | `http://34.117.111.182` |
| **Region** | asia-northeast1 (東京) |
| **Project ID** | ashnova |
| **Cloud Run Service** | mcad-staging-api |
| **Storage Bucket** | mcad-staging-frontend |
| **Global IP Address** | 34.117.111.182 (mcad-staging-frontend-ip) |
| **Artifact Registry** | mcad-staging-repo |
| **Firestore Database** | (default) |

**テスト**:
```bash
# API
curl https://mcad-staging-api-son5b3ml7a-an.a.run.app/

# Frontend
curl -I http://34.117.111.182/
```

---

## 🔧 管理コンソール

### AWS
- **API Gateway**: https://ap-northeast-1.console.aws.amazon.com/apigateway
- **Lambda**: https://ap-northeast-1.console.aws.amazon.com/lambda
- **S3**: https://s3.console.aws.amazon.com/s3/buckets/multicloud-auto-deploy-staging-frontend
- **CloudFront**: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E2GDU7Y7UGDV3S

### Azure
- **Resource Group**: https://portal.azure.com/#@/resource/subscriptions/29031d24-d41a-4f97-8362-46b40129a7e8/resourceGroups/multicloud-auto-deploy-staging-rg
- **Container Apps**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.App%2FcontainerApps
- **Storage Account**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Storage%2FStorageAccounts

### GCP
- **Cloud Run**: https://console.cloud.google.com/run?project=ashnova
- **Cloud Storage**: https://console.cloud.google.com/storage/browser?project=ashnova
- **Artifact Registry**: https://console.cloud.google.com/artifacts?project=ashnova
- **Firestore**: https://console.cloud.google.com/firestore/data?project=ashnova

---

## 📊 APIエンドポイント仕様

### GET /

**説明**: ヘルスチェック / ステータス確認

**レスポンス例**:
```json
{
  "message": "Multi-Cloud Auto Deploy API",
  "cloud": "AWS|Azure|GCP",
  "status": "running"
}
```

### GET /api/messages

**説明**: メッセージ一覧取得

**レスポンス例**:
```json
{
  "messages": [
    {
      "id": "msg123",
      "content": "Hello World",
      "timestamp": "2026-02-14T10:00:00Z",
      "cloud": "AWS"
    }
  ]
}
```

### POST /api/messages

**説明**: メッセージ送信

**リクエスト**:
```json
{
  "content": "Hello World"
}
```

**レスポンス**:
```json
{
  "id": "msg123",
  "content": "Hello World",
  "timestamp": "2026-02-14T10:00:00Z",
  "cloud": "AWS"
}
```

---

## 🧪 動作確認スクリプト

### すべてのエンドポイントをテスト

```bash
#!/bin/bash

echo "=== Testing AWS ==="
curl -s https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/ | jq
curl -I https://dx3l4mbwg1ade.cloudfront.net/ 2>&1 | grep HTTP

echo -e "\n=== Testing Azure ==="
curl -s https://mcad-staging-api--0000004.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/ | jq
curl -I https://multicloud-auto-deploy-staging-endpoint-deezaegrhyfzgsav.z01.azurefd.net/ 2>&1 | grep HTTP

echo -e "\n=== Testing GCP ==="
curl -s https://mcad-staging-api-son5b3ml7a-an.a.run.app/ | jq
curl -I http://34.117.111.182/ 2>&1 | grep HTTP
```

### メッセージ送信テスト

```bash
#!/bin/bash

# AWS
curl -X POST https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/api/messages \
  -H "Content-Type: application/json" \
  -d '{"content":"Test from AWS"}'

# Azure
curl -X POST https://mcad-staging-api--0000004.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/api/messages \
  -H "Content-Type: application/json" \
  -d '{"content":"Test from Azure"}'

# GCP
curl -X POST https://mcad-staging-api-son5b3ml7a-an.a.run.app/api/messages \
  -H "Content-Type: application/json" \
  -d '{"content":"Test from GCP"}'
```

---

## 📝 更新履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-02-14 | 初版作成 - AWS/Azure/GCP全環境のエンドポイント確定 |
| 2026-02-14 | Azure Frontend URL 修正（API URL問題解決後） |
| 2026-02-14 | AWS Frontend URL 修正（リージョン修正後） |

---

## ⚠️ 注意事項

1. **本番環境への適用前に必ずステージング環境でテスト**
2. **API Keyや認証トークンは環境変数で管理**
3. **クロスオリジン（CORS）設定を確認**
4. **レート制限に注意**（特にAWS API Gateway、Azure Front Door）

---

## 🔒 セキュリティ

- すべてのAPIはHTTPS経由で通信
- フロントエンドはCDN経由で配信（DDoS対策）
- データベースはプライベートネットワーク内に配置
- 認証・認可機能は今後実装予定
