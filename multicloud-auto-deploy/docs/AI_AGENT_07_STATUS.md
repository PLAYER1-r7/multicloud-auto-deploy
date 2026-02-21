# 07 — Environment Status

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last verified: 2026-02-21 (GCP API fix deployed — /posts 500 error resolved)

---

## Staging Environment Summary

| Cloud     | Landing (`/`) | SNS App (`/sns/`) | API                                |
| --------- | ------------- | ----------------- | ---------------------------------- |
| **GCP**   | ✅            | ✅                | ✅ Cloud Run (fix deployed 2026-02-21) |
| **AWS**   | ✅            | ✅                | ✅ Lambda (fully operational)      |
| **Azure** | ✅            | ✅                | ✅ Azure Functions                 |

---

## AWS (ap-northeast-1)

```
CDN URL  : https://d1tf3uumcm4bo1.cloudfront.net
API URL  : https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
```

| Resource              | Name / ID                                                             | Status |
| --------------------- | --------------------------------------------------------------------- | ------ |
| CloudFront            | `E1TBH4R432SZBZ`                                                      | ✅     |
| S3 (frontend)         | `multicloud-auto-deploy-staging-frontend`                             | ✅     |
| S3 (images)           | `multicloud-auto-deploy-staging-images` (CORS: \*)                    | ✅     |
| Lambda (API)          | `multicloud-auto-deploy-staging-api` (Python 3.12, 512MB)             | ✅     |
| Lambda (frontend-web) | `multicloud-auto-deploy-staging-frontend-web` (512MB, 30s)            | ✅     |
| API Gateway           | `z42qmqdqac` (HTTP API v2)                                            | ✅     |
| DynamoDB              | `multicloud-auto-deploy-staging-posts` (PAY_PER_REQUEST)              | ✅     |
| Cognito               | Pool `ap-northeast-1_AoDxOvCib` / Client `1k41lqkds4oah55ns8iod30dv2` | ✅     |
| WAF                   | WebACL attached to CloudFront                                         | ✅     |

**Confirmed working (verified 2026-02-20)**:

- Cognito login → `/sns/auth/callback` → session cookie set ✅
- Post feed, create/edit/delete post ✅
- Profile page (nickname, avatar, bio) ✅
- Image upload: S3 presigned URLs, up to 16 files per post ✅
- Logout → Cognito-hosted logout → redirect back to `/sns/` ✅
- CI/CD pipeline: env vars set correctly on every push ✅

**Known limitations**:

- Production stack shares staging resources (independent prod stack not yet deployed).
- WAF rule set not tuned.

---

## Azure (japaneast)

```
CDN URL  : https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net
API URL  : https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger
```

| Resource        | Name                                                                  | Status |
| --------------- | --------------------------------------------------------------------- | ------ |
| Front Door      | `multicloud-auto-deploy-staging-fd` / endpoint: `mcad-staging-d45ihd` | ✅     |
| Storage Account | `mcadwebd45ihd`                                                       | ✅     |
| Function App    | `multicloud-auto-deploy-staging-func` (Python 3.12)                   | ✅     |
| Cosmos DB       | `simple-sns-cosmos` (Serverless)                                      | ✅     |
| Resource Group  | `multicloud-auto-deploy-staging-rg`                                   | ✅     |

**Unresolved issues**:

- End-to-end verification of `PUT /posts/{id}` is incomplete.
- WAF not configured (Front Door Standard SKU).

---

## GCP (asia-northeast1)

```
CDN URL  : http://34.117.111.182
API URL  : https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app
```

| Resource       | Name / ID                                          | Status |
| -------------- | -------------------------------------------------- | ------ |
| Global IP      | `34.117.111.182`                                   | ✅     |
| GCS Bucket     | `ashnova-multicloud-auto-deploy-staging-frontend`  | ✅     |
| Cloud Run      | `multicloud-auto-deploy-staging-api` (Python 3.12) | ✅     |
| Firestore      | `(default)` — collections: messages, posts         | ✅     |
| Backend Bucket | `multicloud-auto-deploy-staging-cdn-backend`       | ✅     |

**Fixed issues (2026-02-21)**:

- `GcpBackend` が `like_post`/`unlike_post` abstract method を未実装 → `TypeError` → `/posts` が 500 エラー  
  → `like_post`/`unlike_post` スタブ実装を追加 (commit `a9bc85e`)
- `frontend-web` Cloud Run の `API_BASE_URL` が未設定 → localhost:8000 を参照  
  → `gcloud run services update` で `API_BASE_URL=https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app` を設定

**Remaining issues**:

- HTTPS not configured (HTTP only). Requires `TargetHttpsProxy` + managed SSL certificate.
- SPA deep links return HTTP 404 (works correctly in browsers).
- Firebase Auth (`GCP_CLIENT_ID`, `GCP_REDIRECT_URI`) 未設定のため認証フロー未確認。現在 `AUTH_DISABLED=true`。

---

## Quick Connectivity Check Commands

```bash
# GCP
curl -s http://34.117.111.182/ | head -3
curl -s https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/health

# AWS
curl -I https://d1tf3uumcm4bo1.cloudfront.net/
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/health

# Azure
curl -I https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/
curl -s "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/health"
```

---

## Production Environment

> Currently sharing the same resources as staging.  
> Independent production stack deployment is planned as **REMAINING_TASKS #13**.

---

## AWS Management Console Links

- [API Gateway](https://ap-northeast-1.console.aws.amazon.com/apigateway)
- [Lambda](https://ap-northeast-1.console.aws.amazon.com/lambda)
- [S3 Bucket](https://s3.console.aws.amazon.com/s3/buckets/multicloud-auto-deploy-staging-frontend)
- [CloudFront](https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1TBH4R432SZBZ)

## Azure Portal Links

- [Resource Group](https://portal.azure.com/#@/resource/subscriptions/29031d24-d41a-4f97-8362-46b40129a7e8/resourceGroups/multicloud-auto-deploy-staging-rg)
- [Function Apps](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Web%2Fsites)
- [Front Door](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Cdn%2Fprofiles)

## GCP Console Links

- [Cloud Run](https://console.cloud.google.com/run?project=ashnova)
- [Cloud Storage](https://console.cloud.google.com/storage/browser?project=ashnova)
- [Firestore](https://console.cloud.google.com/firestore/data?project=ashnova)

---

## Next Section

→ [08 — Runbooks](AI_AGENT_08_RUNBOOKS.md)
