# エンドポイント一覧

## 🌐 本番環境エンドポイント（手動構築）

### AWS (ap-northeast-1)

| 項目 | 値 |
|-----|-----|
| **API Endpoint** | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com` |
| **Frontend CDN** | `https://d1tf3uumcm4bo1.cloudfront.net` ✅ |
| **Frontend Storage** | `http://multicloud-auto-deploy-staging-frontend.s3-website-ap-northeast-1.amazonaws.com` |
| **Region** | ap-northeast-1 (東京) |
| **API Gateway ID** | z42qmqdqac (HTTP API) |
| **CloudFront ID** | E2GDU7Y7UGDV3S |
| **S3 Bucket** | multicloud-auto-deploy-staging-frontend |
| **Lambda Function** | multicloud-auto-deploy-staging-api |
| **Runtime** | Python 3.12 |

**テスト**:
```bash
# API
curl https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/

# Frontend (CDN)
curl -I https://dx3l4mbwg1ade.cloudfront.net/

# Frontend (Direct S3)
curl -I http://multicloud-auto-deploy-staging-frontend.s3-website-ap-northeast-1.amazonaws.com/
```

---

### Azure (japaneast)

| 項目 | 値 |
|-----|-----|
| **API Endpoint** | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger` |
| **Frontend CDN** | `https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net` 🆕 |
| **Frontend Storage** | `https://mcadwebd45ihd.z11.web.core.windows.net` |
| **Region** | japaneast (東日本) |
| **Resource Group** | multicloud-auto-deploy-staging-rg |
| **Function App** | multicloud-auto-deploy-staging-func |
| **Storage Account** | mcadwebd45ihd ($web container) |
| **Front Door** | multicloud-frontend (Profile: multicloud-frontend-afd) |
| **Runtime** | Python 3.12 |

**テスト**:
```bash
# API
curl https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/

# Frontend (CDN)
curl -I https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net/

# Frontend (Direct Storage)
curl -I https://mcadwebd45ihd.z11.web.core.windows.net/
```

---

### GCP (asia-northeast1)

| 項目 | 値 |
|-----|-----|
| **API Endpoint** | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app` |
| **Frontend CDN** | `http://34.117.111.182` 🆕 |
| **Frontend Storage** | `https://storage.googleapis.com/ashnova-multicloud-auto-deploy-staging-frontend/index.html` |
| **Region** | asia-northeast1 (東京) |
| **Project ID** | ashnova |
| **Cloud Function** | multicloud-auto-deploy-staging-api |
| **Storage Bucket** | ashnova-multicloud-auto-deploy-staging-frontend |
| **Global IP Address** | 34.117.111.182 (multicloud-frontend-ip) |
| **Backend Bucket** | multicloud-frontend-backend |
| **Firestore Database** | (default) - messages, posts collections |

**テスト**:
```bash
# API
curl https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/

# Frontend (CDN)
curl -I http://34.117.111.182/

# Frontend (Direct Storage)
curl -I https://storage.googleapis.com/ashnova-multicloud-auto-deploy-staging-frontend/index.html
```

---

## 🎉 Pulumi管理環境

Infrastructure as Codeで管理されているCDNエンドポイント

### AWS CloudFront (Pulumi)

| 項目 | 値 |
|-----|-----|
| **CloudFront URL** | `https://d1tf3uumcm4bo1.cloudfront.net` |
| **Distribution ID** | E1TBH4R432SZBZ |
| **Origin** | multicloud-auto-deploy-staging-frontend.s3.ap-northeast-1.amazonaws.com |
| **管理方法** | Pulumi (`infrastructure/pulumi/aws/`) |
| **Status** | Deployed ✅ |

**Pulumi管理**:
```bash
cd infrastructure/pulumi/aws
pulumi stack output cloudfront_url
pulumi stack output cloudfront_distribution_id
```

**テスト**:
```bash
curl -I https://d1tf3uumcm4bo1.cloudfront.net/
```

---

### Azure Front Door (Pulumi)

| 項目 | 値 |
|-----|-----|
| **Front Door URL** | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` |
| **Endpoint Name** | mcad-staging-d45ihd |
| **Profile Name** | multicloud-auto-deploy-staging-fd |
| **Origin** | mcadwebd45ihd.z11.web.core.windows.net |
| **管理方法** | Pulumi (`infrastructure/pulumi/azure/`) |
| **Status** | Deployed ✅ |

**Pulumi管理**:
```bash
cd infrastructure/pulumi/azure
pulumi stack output frontdoor_url
pulumi stack output frontdoor_hostname
```

**テスト**:
```bash
curl -I https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/
```

---

### GCP Cloud CDN (Pulumi)

| 項目 | 値 |
|-----|-----|
| **CDN URL** | `http://34.117.111.182` |
| **Global IP** | 34.117.111.182 |
| **Backend Bucket** | multicloud-auto-deploy-staging-cdn-backend |
| **Origin Bucket** | ashnova-multicloud-auto-deploy-staging-frontend |
| **管理方法** | Pulumi (`infrastructure/pulumi/gcp/`) |
| **Status** | Deployed ✅ |

**Pulumi管理**:
```bash
cd infrastructure/pulumi/gcp
pulumi stack output cdn_url
pulumi stack output cdn_ip_address
```

**テスト**:
```bash
curl -I http://34.117.111.182/
```

**GCP リソース確認**:
```bash
# Backend Bucket
gcloud compute backend-buckets describe multicloud-auto-deploy-staging-cdn-backend

# Forwarding Rule
gcloud compute forwarding-rules describe multicloud-auto-deploy-staging-cdn-lb --global

# Global Address
gcloud compute addresses describe multicloud-auto-deploy-staging-cdn-ip --global
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
- **Function Apps**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Web%2Fsites
- **Storage Account**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Storage%2FStorageAccounts
- **Front Door**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Cdn%2Fprofiles
- **Cosmos DB**: https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.DocumentDB%2FdatabaseAccounts

### GCP
- **Cloud Functions**: https://console.cloud.google.com/functions/list?project=ashnova
- **Cloud Storage**: https://console.cloud.google.com/storage/browser?project=ashnova
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
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/ | jq
curl -I https://d1tf3uumcm4bo1.cloudfront.net/ 2>&1 | grep HTTP

echo -e "\n=== Testing Azure ==="
curl -s https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/ | jq
curl -I https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net/ 2>&1 | grep HTTP

echo -e "\n=== Testing GCP ==="
curl -s https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/ | jq
curl -I http://34.117.111.182/ 2>&1 | grep HTTP
```

### メッセージ送信テスト

```bash
#!/bin/bash

# AWS
curl -X POST https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/api/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content":"Test from AWS"}'

# Azure
curl -X POST https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/api/messages/ \
  -H "Content-Type: application/json" \
  -d '{"content":"Test from Azure"}'

# GCP
curl -X POST https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/api/messages/ \
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
| 2026-02-15 | **大型更新**: 全エンドポイント情報を実際の値に更新 |
| 2026-02-15 | CDN情報追加 - CloudFront, Front Door, Cloud CDN |
| 2026-02-15 | Azure: Container Apps → Functionsに変更 |
| 2026-02-15 | GCP: Cloud Functions APIエンドポイント更新 |
| 2026-02-15 | **Pulumi管理環境追加** - 全3クラウドでInfrastructure as Code導入 🎉 |
| 2026-02-15 | **全環境デプロイ成功** - AWS/GCP/Azure統合完了、エンドポイント最新化 |

---

## 📌 重要な注意事項
2. **API Keyや認証トークンは環境変数で管理**
3. **クロスオリジン（CORS）設定を確認**
4. **レート制限に注意**（特にAWS API Gateway、Azure Front Door）

---

## 🔒 セキュリティ

- すべてのAPIはHTTPS経由で通信
- フロントエンドはCDN経由で配信（DDoS対策）
- データベースはプライベートネットワーク内に配置
- 認証・認可機能は今後実装予定
