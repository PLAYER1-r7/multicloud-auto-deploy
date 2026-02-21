# 07 — Environment Status

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last verified: 2026-02-21 (3クラウド全staging テスト実施済み — Azure AUTH_DISABLED修正)

---

## Staging Environment Summary

| Cloud     | Landing (`/`) | SNS App (`/sns/`) | API                                       |
| --------- | ------------- | ----------------- | ----------------------------------------- |
| **GCP**   | ✅            | ✅                | ✅ Cloud Run + Firebase Auth (2026-02-21) |
| **AWS**   | ✅            | ✅                | ✅ Lambda (fully operational)             |
| **Azure** | ✅            | ✅                | ✅ Azure Functions                        |

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

**Confirmed working (verified 2026-02-21)**:

- Azure AD login → `/sns/auth/callback` → session cookie set ✅
- `GET /posts`, `GET /posts?limit=5`, `GET /posts?limit=5&tag=test` ✅
- `GET /posts/nonexistent-id` → 404 ✅
- Auth guard: `POST /posts` without token → 401 ✅
- Auth guard: `POST /uploads/presigned-urls` without token → 401 ✅
- Frontend `/sns/` → 200 ✅

**Unresolved issues**:

- SPA deep links (`/sns/unknown-path` via Front Door) return 404 JSON (not SPA fallback). AWS CloudFront has this configured; Azure Front Door does not.
- End-to-end verification of `PUT /posts/{id}` is incomplete.
- WAF not configured (Front Door Standard SKU).

---

## GCP (asia-northeast1)

```
CDN URL          : http://34.117.111.182
API URL          : https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app
Frontend Web URL : https://multicloud-auto-deploy-staging-frontend-web-son5b3ml7a-an.a.run.app
```

| Resource                 | Name / ID                                                         | Status |
| ------------------------ | ----------------------------------------------------------------- | ------ |
| Global IP                | `34.117.111.182`                                                  | ✅     |
| GCS Bucket (frontend)    | `ashnova-multicloud-auto-deploy-staging-frontend`                 | ✅     |
| GCS Bucket (uploads)     | `ashnova-multicloud-auto-deploy-staging-uploads` (public read)    | ✅     |
| Cloud Run (API)          | `multicloud-auto-deploy-staging-api` (Python 3.12)                | ✅     |
| Cloud Run (frontend-web) | `multicloud-auto-deploy-staging-frontend-web` (Docker, port 8080) | ✅     |
| Firestore                | `(default)` — collections: messages, posts                        | ✅     |
| Backend Bucket           | `multicloud-auto-deploy-staging-cdn-backend`                      | ✅     |

**Confirmed working (verified 2026-02-21)**:

- Firebase Google Sign-In → `/sns/auth/callback` → httponly Cookie session ✅
- Post feed, create/edit/delete post ✅
- Image upload: GCS presigned URLs (signed via IAM `signBlob` API), up to 16 files per post ✅
- Uploaded images displayed in post feed ✅
- Firebase ID token auto-refresh (`onIdTokenChanged`) ✅
- Dark theme background SVGs (starfield, ring) rendered correctly ✅

**Fixed issues (2026-02-21)**:

- `GcpBackend` が `like_post`/`unlike_post` abstract method を未実装 → `TypeError` → `/posts` が 500 エラー  
  → `like_post`/`unlike_post` スタブ実装を追加 (commit `a9bc85e`)
- `frontend-web` Cloud Run の `API_BASE_URL` が未設定 → localhost:8000 を参照  
  → `gcloud run services update` で環境変数設定
- Firebase Auth 未実装 → Google Sign-In フロー全体を実装 (commit `3813577`)
- GCS CORS に `x-ms-blob-type` ヘッダー未登録 → CORS更新 + uploads.js修正 (commit `1cf53b7`, `b5b4de5`)
- GCS 署名URL生成で `content_type` が `"image/jpeg"` ハードコード → `content_types[index]` を正しく使用 (commit `148b7b5`)
- Firebase IDトークン期限切れ (401) → `onIdTokenChanged` で自動リフレッシュ (commit `8110d20`)
- CI/CD に `GCP_SERVICE_ACCOUNT` 環境変数未設定 → `deploy-gcp.yml` に追加 (commit `27b10cc`)
- CSS の背景SVGが絶対パス `/static/` → 相対パス `./` に修正 (commit `0ed0805`)
- GCS uploads バケットが非公開 → `allUsers:objectViewer` 付与 + Pulumi定義に追加 (commit `0ed0805`)

**Remaining issues**:

- HTTPS not configured for CDN (HTTP only). Requires `TargetHttpsProxy` + managed SSL certificate.
- SPA deep links via CDN return HTTP 404 (Cloud Run URL works correctly in browsers).

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
