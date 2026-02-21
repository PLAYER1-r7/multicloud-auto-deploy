# 07 — Environment Status

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)  
> Last verified: 2026-02-21 (All 3 clouds: custom domain HTTPS fully operational + SNS tests 14/14 PASS + AWS HTTPS certificate fix applied directly + AWS Production SNS localhost:8000 fixed)

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

**Unresolved issues**:

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

- `GcpBackend` had unimplemented `like_post`/`unlike_post` abstract methods → `TypeError` → `/posts` returned 500
  → Added stub implementations for `like_post`/`unlike_post` (commit `a9bc85e`)
- `frontend-web` Cloud Run `API_BASE_URL` was unset → falling back to localhost:8000
  → Set environment variable via `gcloud run services update`
- Firebase Auth not implemented → Implemented the full Google Sign-In flow (commit `3813577`)
- `x-ms-blob-type` header not registered in GCS CORS → Updated CORS + fixed uploads.js (commits `1cf53b7`, `b5b4de5`)
- GCS presigned URL generation had `content_type` hardcoded as `"image/jpeg"` → Now uses `content_types[index]` correctly (commit `148b7b5`)
- Firebase ID token expiry (401) → Auto-refresh via `onIdTokenChanged` (commit `8110d20`)
- `GCP_SERVICE_ACCOUNT` env var missing in CI/CD → Added to `deploy-gcp.yml` (commit `27b10cc`)
- CSS background SVGs used absolute path `/static/` → Changed to relative path `./` (commit `0ed0805`)
- GCS uploads bucket was private → Granted `allUsers:objectViewer` + added IAMBinding to Pulumi definition (commit `0ed0805`)

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

> Production has its own independent Pulumi stack (deployed). Resources are separate from staging.

### Production Endpoints

| Cloud     | CDN / Endpoint                                             | API Endpoint                                                  | Distribution ID        |
| --------- | ---------------------------------------------------------- | ------------------------------------------------------------- | ---------------------- |
| **AWS**   | `d1qob7569mn5nw.cloudfront.net` / `www.aws.ashnova.jp`    | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com` | E214XONKTXJEJD         |
| **Azure** | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | —                                                             | mcad-production-diev0w |
| **GCP**   | `34.8.38.222`                                              | —                                                             | -                      |

**AWS Production SNS App** (`https://www.aws.ashnova.jp/sns/`):

| Item              | Value                                                            |
| ----------------- | ---------------------------------------------------------------- |
| Lambda (API)      | `multicloud-auto-deploy-production-api`                          |
| Lambda (frontend) | `multicloud-auto-deploy-production-frontend-web`                 |
| API_BASE_URL      | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`   |
| Cognito Pool      | `ap-northeast-1_50La963P2`                                       |
| Cognito Client    | `4h3b285v1a9746sqhukk5k3a7i`                                     |
| Cognito Redirect  | `https://www.aws.ashnova.jp/sns/auth/callback`                   |
| DynamoDB          | `multicloud-auto-deploy-production-posts`                        |

### Custom Domain Status (ashnova.jp) — 2026-02-21

| Cloud     | URL                          | Status                                                                                        |
| --------- | ---------------------------- | --------------------------------------------------------------------------------------------- |
| **AWS**   | https://www.aws.ashnova.jp   | ✅ **Fully operational** (HTTP/2 200, ACM cert `914b86b1` + CloudFront alias set directly — details: [AWS_HTTPS_FIX_REPORT.md](AWS_HTTPS_FIX_REPORT.md)) |
| **Azure** | https://www.azure.ashnova.jp | ✅ **Fully operational** (HTTPS 200, DigiCert/GeoTrust managed cert, AFD route active)                 |
| **GCP**   | https://www.gcp.ashnova.jp   | ✅ **Fully operational** (HTTPS 200, TLS cert active via ACTIVE cert `ashnova-production-cert-c41311`) |

#### 完了した作業 (2026-02-21)

| Cloud | 作業                                                                              | 結果                                                                                                                                        |
| ----- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS   | ACM 証明書確認                                                                    | ✅ `www.aws.ashnova.jp` 向け証明書 `914b86b1` (有効期限 2027-03-12) ISSUED 確認                                                             |
| AWS   | `aws cloudfront update-distribution` で alias + ACM 証明書を直接設定（2026-02-21）| ✅ Distribution `E214XONKTXJEJD` へ alias `www.aws.ashnova.jp` + cert `914b86b1` 設定 → `NET::ERR_CERT_COMMON_NAME_INVALID` 解消 → HTTP/2 200 稼働 |
| AWS   | Production `frontend-web` Lambda 環境変数修正 (2026-02-21)                        | ✅ `API_BASE_URL` が空→`localhost:8000` フォールバックを修正（原因: `deploy-frontend-web-aws.yml` が secrets 依存；production secrets 未設定）→ Pulumi outputs を使うよう CI/CD 修正（commit `fd1f422`） |
| Azure | `az afd custom-domain create` + route attach          | ✅ DNS Approved → Managed Cert Succeeded (GeoTrust, 2026-02-21 〜 2026-08-21)                 |
| Azure | AFD route disable→enable トグル                       | ✅ edge nodes への deployment トリガー → HTTPS 200 稼働                                       |
| Azure | `az afd custom-domain update` (cert edge deploy)      | ✅ `CN=www.azure.ashnova.jp` cert が AFD POP に配布済み                                       |
| Azure | `frontend-web` Function App 環境変数設定              | ✅ API_BASE_URL, AUTH_PROVIDER, AZURE_TENANT_ID, AZURE_CLIENT_ID など設定済み                 |
| Azure | Azure AD app redirect URI 追加                        | ✅ `https://www.azure.ashnova.jp/sns/auth/callback` 追加済み                                  |
| GCP   | `pulumi up --stack production` (SSL cert作成)         | ✅ cert `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` PROVISIONING中                  |
| GCP   | ACTIVE cert `ashnova-production-cert-c41311` 追加     | ✅ HTTPS プロキシに追加 → `https://www.gcp.ashnova.jp` HTTPS 即時稼働                         |
| GCP   | Firebase authorized domains 更新                      | ✅ `www.gcp.ashnova.jp` を Firebase Auth authorized domains に追加                            |

#### Remaining Work

- **GCP**: Once `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` becomes ACTIVE, `ashnova-production-cert-c41311` can be removed from the proxy

```bash
# Check GCP SSL cert status
gcloud compute ssl-certificates describe multicloud-auto-deploy-production-ssl-cert-3ee2c3ce \
  --global --format="value(managed.status)"
# Once ACTIVE:
gcloud compute target-https-proxies update multicloud-auto-deploy-production-cdn-https-proxy \
  --global \
  --ssl-certificates=multicloud-auto-deploy-production-ssl-cert-3ee2c3ce
```

#### All-Cloud Test Results (final check 2026-02-21)

```
test-cloud-env.sh production → PASS: 14, FAIL: 0, WARN: 3 (all POST 401 = expected auth guard)
test-azure-sns.sh            → PASS: 10, FAIL: 0 (www.azure.ashnova.jp dedicated tests)
test-gcp-sns.sh              → PASS: 10, FAIL: 0 (www.gcp.ashnova.jp dedicated tests)
```

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

## FinOps — GCP 未使用静的IPアドレス調査 (2026-02-21)

> GCP FinOps の指摘を受けて調査を実施。プロジェクト `ashnova` 全静的IPアドレスを確認した結果、以下の通り。

### 全IPアドレス一覧

```bash
gcloud compute addresses list --project=ashnova \
  --format="table(name,address,status,addressType,users.list())"
```

| 名前                                       | IPアドレス     | ステータス      | 作成日     | 使用先                              |
| ------------------------------------------ | -------------- | --------------- | ---------- | ----------------------------------- |
| `multicloud-auto-deploy-production-cdn-ip` | 34.8.38.222    | ✅ IN_USE       | —          | Production CDN (Forwarding Rule ×2) |
| `multicloud-auto-deploy-staging-cdn-ip`    | 34.117.111.182 | ✅ IN_USE       | —          | Staging CDN (Forwarding Rule ×2)    |
| `ashnova-production-ip-c41311`             | 34.54.250.208  | ⚠️ **RESERVED** | 2026-02-11 | なし                                |
| `multicloud-frontend-ip`                   | 34.120.43.83   | ⚠️ **RESERVED** | 2026-02-14 | なし                                |
| `simple-sns-frontend-ip`                   | 34.149.225.173 | ⚠️ **RESERVED** | 2026-01-30 | なし                                |

### 未使用IPの経緯

| 名前                           | 推定経緯                                                                                                                                                          |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `simple-sns-frontend-ip`       | プロジェクト初期（旧名 `simple-sns` 時代、2026-01-30）に作成。Pulumi コードにも Forwarding Rule にも参照なし。                                                    |
| `ashnova-production-ip-c41311` | Pulumi サフィックス `c41311` が示す通り Production CDN 用として作成（2026-02-11）されたが、後に `multicloud-auto-deploy-production-cdn-ip` に置き換えられ不要に。 |
| `multicloud-frontend-ip`       | 2026-02-14 に作成。コードベース・ドキュメント全体に参照なし。試験的に予約されたまま放棄されたと推定。                                                             |

> **注**: 3つとも Pulumi コード・Forwarding Rule いずれにも紐づいておらず、即時解放可能。

### 解放コマンド

```bash
gcloud compute addresses delete ashnova-production-ip-c41311 --global --project=ashnova --quiet
gcloud compute addresses delete multicloud-frontend-ip          --global --project=ashnova --quiet
gcloud compute addresses delete simple-sns-frontend-ip          --global --project=ashnova --quiet
```

> ⚠️ 解放後は元に戻せないため、各IPを使っているリソースがないことを `gcloud compute addresses describe <name> --global` で最終確認してから実行すること。

---

## FinOps — GCP Cloud Storage 不要バケット調査 (2026-02-21)

> 静的IP調査に続いて Cloud Storage も調査。Terraform 時代の残骸バケットと壊れた Cloud Function が確認された。

### 全バケット一覧（プロジェクト: ashnova）

| バケット名                                                               | サイズ    | 判定          | 備考                                                                             |
| ------------------------------------------------------------------------ | --------- | ------------- | -------------------------------------------------------------------------------- |
| `ashnova-multicloud-auto-deploy-production-frontend`                     | —         | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-production-function-source`              | 5 MB      | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-production-uploads`                      | —         | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-frontend`                        | —         | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-function-source`                 | 5 MB      | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-landing`                         | 8 KB      | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-uploads`                         | —         | ✅ 現役       | Pulumi 管理                                                                      |
| `ashnova.firebasestorage.app`                                            | —         | ✅ 保持       | Firebase システム管理                                                            |
| `ashnova_cloudbuild`                                                     | —         | ✅ 保持       | Cloud Build システム管理                                                         |
| `gcf-v2-sources-899621454670-asia-northeast1`                            | 433 MB    | ✅ 保持       | Cloud Function v2 (ACTIVE) のソース                                              |
| `gcf-v2-uploads-899621454670.asia-northeast1.cloudfunctions.appspot.com` | —         | ✅ 保持       | Cloud Functions アップロードステージング                                         |
| `ashnova-staging-frontend`                                               | **空**    | 🗑️ **削除可** | Terraform 残骸。`ashnova-multicloud-auto-deploy-staging-frontend` に置き換え済み |
| `ashnova-staging-function-source`                                        | **65 MB** | 🗑️ **削除可** | Terraform 残骸。zip は 2026-02-14 版の古いもの                                   |
| `multicloud-auto-deploy-tfstate`                                         | **空**    | 🗑️ **削除可** | 旧 Terraform state バケット。空                                                  |
| `multicloud-auto-deploy-tfstate-gcp`                                     | **6 KB**  | 🗑️ **削除可** | 上2バケットを管理する Terraform state のみ保持                                   |

### 削除可能バケットの経緯

| バケット名                           | 推定経緯                                                                                                                                                                   |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ashnova-staging-frontend`           | 旧 Terraform 構成（`ashnova-staging-*` 名前体系）のフロントエンドバケット。現行 Pulumi 管理の `ashnova-multicloud-auto-deploy-staging-frontend` に完全移行済み。中身は空。 |
| `ashnova-staging-function-source`    | 同 Terraform 構成の Cloud Function ソースバケット。65 MB の古い zip が残存。現行の `ashnova-multicloud-auto-deploy-staging-function-source`（5 MB）に置き換え済み。        |
| `multicloud-auto-deploy-tfstate`     | AWS 側の旧 Terraform state バケット候補として作成されたが未使用のまま放棄。空。                                                                                            |
| `multicloud-auto-deploy-tfstate-gcp` | 上記 `ashnova-staging-*` 2バケットを管理する Terraform state を保持。コードベースに `.tf` ファイルは存在しない。4件はセットで削除。                                        |

### おまけ：壊れた Cloud Function（関連リソース）

| リソース                               | 状態       | 内容                                                                                                                            |
| -------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `mcad-staging-api` (Cloud Function v2) | **FAILED** | `Cloud Run service not found` エラー。Cloud Run が削除済みなのに Function 定義のみ残存。Pulumi/現行コードに参照なし。削除可能。 |

### 削除コマンド

```bash
# バケット 4件（中身ごと削除）— tfstate-gcp を最後に削除
gcloud storage rm --recursive gs://ashnova-staging-frontend           --project=ashnova
gcloud storage rm --recursive gs://ashnova-staging-function-source    --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate     --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate-gcp --project=ashnova

# 壊れた Cloud Function も削除
gcloud functions delete mcad-staging-api \
  --region=asia-northeast1 --project=ashnova --v2 --quiet
```

> ⚠️ `multicloud-auto-deploy-tfstate-gcp` には `ashnova-staging-frontend` と `ashnova-staging-function-source` の Terraform state が入っているため、この4件はセットで削除すること。

---

## Next Section

→ [08 — Runbooks](AI_AGENT_08_RUNBOOKS.md)
