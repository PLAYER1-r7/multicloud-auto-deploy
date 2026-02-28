# 06 — 環境ステータス

> Part III — Operations | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> 最終確認: 2026-02-27 Session 4 (アーキテクチャ図アイコン強化完了 ✅ / デュアルアイコン配置実装 ✅ / ドキュメント更新完了 ✅)
> 前回: 2026-02-27 Session 3 (S1・S2・Task 13 完了 ✅ / エンドポイント本番運用 ✅ / README セキュリティ情報反映 ✅)

---

## セッション 2026-02-27 (継続 4): アーキテクチャ図アイコン強化

### 完了作業

| タスク                                       | 結果                                                             | 状況 |
| -------------------------------------------- | ---------------------------------------------------------------- | ---- |
| **デュアルアイコン配置実装**                 | ノード左上（24px）+ テキスト横（20px）の2箇所にアイコン表示      | ✅   |
| **generate_icon_diagram.py JavaScript 更新** | foreignObject / text要素の両方に対応するスマート検出ロジック実装 | ✅   |
| **3環境HTML再生成**                          | staging/production/combined の3ファイル全て再生成                | ✅   |
| **CLOUD_ARCHITECTURE_MAPPER.md 更新**        | Features / Technical Details / Known Limitations セクション更新  | ✅   |
| **CHANGELOG.md 更新**                        | 2026-02-27 エントリに詳細な実装内容とファイルサイズ更新          | ✅   |
| **README.md アーキテクチャリンク追加**       | インタラクティブHTML図への直接リンク追加済み                     | ✅   |

### アイコン配置戦略

**アイコン配置**:

1. **ノード左上コーナー** (24x24px):
   - 位置: (rect.x + 6, rect.y + 6)
   - 目的: リソースタイプの素早い視覚識別
   - ノードサイズに関わらず常に表示

2. **テキストインライン** (20x20px):
   - 位置: ノードラベルテキスト左の4px
   - 目的: テキスト関連付けで読みやすさ向上
   - スマート検出: `foreignObject` と SVG `text`/`tspan` 要素の両方に対応

**JavaScript DOM 操作**:

```javascript
// 1. 左上コーナー
const topIcon = createSVGImage(iconUrl, rectX + 6, rectY + 6, 24, 24);
node.appendChild(topIcon);

// 2. テキストインライン (foreignObject vs text 要素検出)
if (textElement.tagName === "foreignObject") {
  textX = parseFloat(textElement.getAttribute("x") || 0);
  textY =
    parseFloat(textElement.getAttribute("y") || 0) + height / 2 - iconSize / 2;
} else {
  const tspan = textElement.querySelector("tspan");
  textX = parseFloat((tspan || textElement).getAttribute("x") || 0);
  textY =
    parseFloat((tspan || textElement).getAttribute("y") || 0) - iconSize / 2;
}
const textIcon = createSVGImage(iconUrl, textX - 24, textY, 20, 20);
labelGroup.insertBefore(textIcon, labelGroup.firstChild);
```

### 生成ファイル

| ファイル                       | サイズ | アイコン                      | 説明                                     |
| ------------------------------ | ------ | ----------------------------- | ---------------------------------------- |
| `architecture.staging.html`    | 78KB   | AWS (5) + Azure (4) + GCP (5) | ステージング環境（デュアルアイコン配置） |
| `architecture.production.html` | 78KB   | AWS (5) + Azure (4) + GCP (5) | 本番環境（デュアルアイコン配置）         |
| `architecture-combined.html`   | 84KB   | AWS (5) + Azure (4) + GCP (5) | 統合ビュー（color-coded nodes）          |

**アイコンソース**:

- AWS: 14KB (cloudfront, lambda, s3, dynamodb, api-gateway)
- Azure: 16KB (cdn, function, storage, cosmos-db)
- GCP: 20KB (cdn, run, storage, firestore, load-balancer)
- **埋め込みアセット合計**: ~50KB Base64 エンコード SVG データ URI

### ドキュメント更新

✅ **CLOUD_ARCHITECTURE_MAPPER.md**:

- Features セクション: 「Dual icon placement」箇条書きを追加
- Technical Details: デュアル配置ロジックを含む JavaScript コードサンプルを拡張
- Known Limitations: テキストインライン配置の分散に関する注記を追加

✅ **CHANGELOG.md**:

- 2026-02-27 エントリに詳細な実装ノートを更新
- ファイルサイズ変更を追加（staging/production で 85KB → 78KB）
- デュアルアイコン配置戦略を文書化

✅ **README.md**:

- アーキテクチャセクションに 3 つのインタラクティブ HTML 図へのリンクを追加
- 図リンクに視覚的インジケーター（📊）を追加

---

## セッション 2026-02-27 (継続 3): セキュリティデプロイ・ドキュメント更新

### 完了作業

| タスク                                     | 結果                                                                                                 | 状況 |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ---- |
| S1: GCP ステージング pulumi up             | HTTPS リダイレクト / 監査ログ反映済み（unchanged 33）                                                | ✅   |
| S1: AWS 本番 pulumi up                     | CloudTrail / CORS 反映済み（unchanged 40）                                                           | ✅   |
| S1: GCP 本番 refresh+up                    | State drift 解決後、監査ログ反映済み（unchanged 34）                                                 | ✅   |
| S1: Azure ステージング pulumi up           | Key Vault パージ保護反映（updated 1, unchanged 32）                                                  | ✅   |
| S1: Azure 本番 pulumi up                   | Key Vault パージ保護本番反映済み（unchanged 33）                                                     | ✅   |
| **S2: Function App マネージド ID**         | ステージング/本番 両方に SystemAssigned MSI 割り当て成功                                             | ✅   |
| **Task 13: README 更新**                   | エンドポイント・セキュリティ実装・テスト結果・デプロイ状況を最新情報に更新                           | ✅   |
| Task 20/21 補完: Key Vault 診断設定（CLI） | `az monitor diagnostic-settings create` で Log Analytics との統合が完了（AuditEvent ストリーミング） | ✅   |

### 本番エンドポイント (2026-02-27 現在)

| クラウド  | CDN / フロントエンド                                                             | API                                                                                                             | ステータス    |
| --------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------- |
| **AWS**   | [CloudFront](https://d1qob7569mn5nw.cloudfront.net) ✅                           | [API Gateway](https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com)                                      | ✅ 本番運用中 |
| **Azure** | [Front Door](https://mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net) ✅ | [Functions](https://multicloud-auto-deploy-production-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api) | ✅ 本番運用中 |
| **GCP**   | [CDN（www.gcp.ashnova.jp）](https://www.gcp.ashnova.jp) ✅                       | [Cloud Functions](https://multicloud-auto-deploy-production-api-***-an.a.run.app)                               | ✅ 本番運用中 |

### セキュリティ実装ステータス (本番環境にデプロイ済み)

| 対策                  | AWS | Azure               | GCP | ステータス           |
| --------------------- | --- | ------------------- | --- | -------------------- |
| CORS 絞り込み         | ✅  | ✅                  | ✅  | ✅ 本番反映          |
| CloudTrail / 監査ログ | ✅  | ✅                  | ✅  | ✅ 本番反映          |
| Key Vault パージ保護  | —   | ✅                  | —   | ✅ 本番反映          |
| Key Vault 診断ログ    | —   | ✅（Log Analytics） | —   | ✅ 本番反映          |
| マネージド ID         | —   | ✅                  | —   | ✅ ステージング/本番 |
| HTTPS リダイレクト    | —   | —                   | ✅  | ✅ 本番反映          |
| Cloud Armor           | —   | —                   | ✅  | ✅ 本番反映          |

---

## セッション 2026-02-27: GCP 監査ログ・課金予算修復

### 完了作業

| タスク                                     | 結果                                                                                                                                                   | 状況 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---- |
| GCP 監査ログ再有効化 (IAMAuditConfig)      | staging/production で Cloud Audit Logs (`allServices`) を有効化。Pulumi リソース作成完了                                                               | ✅   |
| ADC (Application Default Credentials) 更新 | `gcloud auth application-default login` で sat0sh1kawada00@gmail.com 再認証。quota project=ashnova に設定                                              | ✅   |
| GCP 課金アカウント設定                     | Pulumi設定に `billingAccountId: 01F139-282A95-9BBA25` を追加                                                                                           | ✅   |
| 課金予算エラー軽減                         | ADC quota project エラー回避。monitoring.py で `billing_account_id` をoptional パラメータ化。コードで `enable_billing_budget=False` にデフォルト無効化 | ✅   |
| GCP side budget cleanup                    | `gcloud billing budgets delete` で古いbudgetリソース削除                                                                                               | ✅   |
| monitoring.py リファクタリング             | `create_billing_budget()` に `billing_account_id` 追加。`setup_monitoring()` で `billing_budget=None` when not enabled                                 | ✅   |

### コード変更

- **infrastructure/pulumi/gcp/main.py**: `enable_billing_budget = False` (ハードコード無効化) + `billing_account_id=None` を常時 monitoring へ参照
- **infrastructure/pulumi/gcp/monitoring.py**: `billing_account_id` パラメータ追加、optional化。budget作成条件を `if stack=="production" and billing_account_id:` に変更

### 既知の課題 / 次のステップ

- GCP production `pulumi up` が preview conflict 状態。コード修正後は再実行予定（次セッション）
- staging/production 共に監査ログ有効化完了、billing warning 回避完了
- billingbudgets API 認証エラーは ADC quotaProjectで解消するが、service account接続時の権限不足で deprecated。本番運用では GCP service account 設定または ignore_changes で対応推奨

---

## ステージング環境概要

| クラウド  | ランディング (`/`) | SNS アプリ (`/sns/`) | API                                 |
| --------- | :----------------: | :------------------: | ----------------------------------- |
| **GCP**   |         ✅         |          ✅          | ✅ Cloud Run (2026-02-24)           |
| **AWS**   |         ✅         |          ✅          | ✅ Lambda (完全運用中, 2026-02-24)  |
| **Azure** |         ✅         |          ✅          | ✅ Azure Functions FC1 (2026-02-24) |

---

## AWS (ap-northeast-1)

```
CDN URL  : https://d1tf3uumcm4bo1.cloudfront.net
API URL  : https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
```

| リソース              | 名前 / ID                                                                  | ステータス |
| --------------------- | -------------------------------------------------------------------------- | ---------- |
| CloudFront            | `E1TBH4R432SZBZ` (PriceClass_200: NA/EU/JP/KR/IN)                          | ✅         |
| CloudFront RHP        | `multicloud-auto-deploy-staging-security-headers` (HSTS + CSP + 4 headers) | ✅         |
| S3 (フロントエンド)   | `multicloud-auto-deploy-staging-frontend`                                  | ✅         |
| S3 (画像)             | `multicloud-auto-deploy-staging-images` (CORS: \*)                         | ✅         |
| Lambda (API)          | `multicloud-auto-deploy-staging-api` (Python 3.12, **1769MB** = 1 vCPU)    | ✅         |
| Lambda (frontend-web) | `multicloud-auto-deploy-staging-frontend-web` (512MB, 30s)                 | ✅         |
| API Gateway           | `z42qmqdqac` (HTTP API v2)                                                 | ✅         |
| DynamoDB              | `multicloud-auto-deploy-staging-posts` (PAY_PER_REQUEST)                   | ✅         |
| Cognito               | Pool `ap-northeast-1_AoDxOvCib` / Client `1k41lqkds4oah55ns8iod30dv2`      | ✅         |
| WAF                   | WebACL が CloudFront に紐付け済み                                          | ✅         |

**確認済み機能** (2026-02-22):

- Cognito ログイン → `/sns/auth/callback` → セッションクッキー設定 ✅
- ポストフィード、最大10枚のマルチイメージ投稿作成 ✅
- 画像が正しく表示（S3 プリサインド GET URL、1時間有効） ✅
- `GET /posts/{post_id}` 個別ポスト表示 ✅
- プロフィールページ（ニックネーム、アバター、自己紹介） ✅
- ニックネームがポストリストに保存・表示 ✅
- 画像アップロード: S3 プリサインド URL、`MAX_IMAGES_PER_POST` でサーバーサイド制限 ✅
- `GET /limits` エンドポイント（認証不要）が `{"maxImagesPerPost": 10}` を返す ✅
- ログアウト → Cognito ホステッドログアウト → `/sns/` へリダイレクト ✅
- CI/CD パイプライン: push ごとに環境変数が正しく設定される ✅
- フロントエンドバンドルが `VITE_BASE_PATH=/sns/` でビルドされ、アセットパスが正常 ✅
- CloudFront カスタムエラーページ: `/sns/index.html` (403+404) ✅
- CloudFront Response Headers Policy: HSTS/CSP(`upgrade-insecure-requests`)/X-Content-Type-Options/X-Frame-Options/Referrer-Policy/XSS-Protection ✅ (2026-02-23)
- CloudFront PriceClass_200: 日本・韓国・インドのエッジを使用 ✅ (旧: PriceClass_100 = 米国/欧州のみ)
- OAuth フロー PKCE (S256) 実装: `response_type=code` + code_verifier/challenge ✅ (2026-02-23)
- Cognito `implicit` フロー削除: `allowed_oauth_flows=["code"]` のみ ✅ (2026-02-23)
- S3 パブリックアクセス完全遮断: `BlockPublicAcls/IgnorePublicAcls/BlockPublicPolicy/RestrictPublicBuckets=True` ✅ (2026-02-23)
- S3 バケットポリシー OAI 専用: `Principal:*` 削除 ✅ (2026-02-23)
- Lambda `_resolve_image_urls`: `http://` URL をスキップして Mixed Content を防止 ✅ (2026-02-23)

**現在のフロントエンドバンドル**: `index-B0gzRu__.js` (2026-02-23 アップロード, PKCE対応)

**AWS staging ビルドコマンド**:

```bash
cd services/frontend_react
set -a && source .env.aws.staging && set +a
VITE_BASE_PATH=/sns/ npm run build
```

**既知の制限**:

- Production スタックは staging リソースと共有（独立した prod スタック未デプロイ）
- WAF ルールセット未調整
- `DELETE /posts` で SNS Unsubscribe 呼び出しが失敗する可能性（未テスト）

---

## Azure (japaneast)

```
CDN URL  : https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net
API URL  : https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net
```

| リソース        | 名前                                                                  | ステータス |
| --------------- | --------------------------------------------------------------------- | ---------- |
| Front Door      | `multicloud-auto-deploy-staging-fd` / endpoint: `mcad-staging-d45ihd` | ✅         |
| Storage Account | `mcadwebd45ihd`                                                       | ✅         |
| Function App    | `multicloud-auto-deploy-staging-func` (Python 3.12, always-ready=1)   | ✅         |
| Cosmos DB       | `messages` (Serverless, db: messages / container: messages)           | ✅         |
| Resource Group  | `multicloud-auto-deploy-staging-rg`                                   | ✅         |

**構成済み** (2026-02-23):

- FlexConsumption always-ready インスタンス: `http=1` → コールドスタート解消 ✅

**未解決の課題**:

- `PUT /posts/{id}` のエンドツーエンド検証が不完全
- WAF 未構成 (Front Door Standard SKU)

---

## GCP (asia-northeast1)

```
CDN URL : http://34.117.111.182
API URL : https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app
```

| リソース            | 名前 / ID                                                      | ステータス |
| ------------------- | -------------------------------------------------------------- | ---------- |
| グローバル IP       | `34.117.111.182`                                               | ✅         |
| GCS バケット (前面) | `ashnova-multicloud-auto-deploy-staging-frontend`              | ✅         |
| GCS バケット (画像) | `ashnova-multicloud-auto-deploy-staging-uploads` (public read) | ✅         |
| Cloud Run (API)     | `multicloud-auto-deploy-staging-api` (Python 3.12, **min=1**)  | ✅         |
| Firestore           | `(default)` — collections: messages, posts                     | ✅         |
| Backend Bucket      | `multicloud-auto-deploy-staging-cdn-backend`                   | ✅         |

**確認済み機能** (2026-02-21):

- Firebase Google Sign-In → `/sns/auth/callback` → httponly Cookie セッション ✅
- ポストフィード、作成/編集/削除 ✅
- 画像アップロード: GCS プリサインド URL (IAM `signBlob` API 経由署名)、最大16ファイル/投稿 ✅
- アップロードされた画像がポストフィードに表示される ✅
- Firebase ID トークン自動更新 (`onIdTokenChanged`) ✅
- ダークテーマ背景 SVG (星空、リング) が正しくレンダリングされる ✅

**修正済みの課題** (2026-02-21):

- `GcpBackend` に未実装の `like_post`/`unlike_post` 抽象メソッド → `TypeError` → `/posts` が 500 を返す
  → `like_post`/`unlike_post` のスタブ実装を追加（コミット `a9bc85e`）
- `frontend-web` Cloud Run で `API_BASE_URL` 未設定 → localhost:8000 へフォールバック
  → `gcloud run services update` で環境変数を設定
- Firebase Auth 未実装 → Google Sign-In フロー全体を実装（コミット `3813577`）
- `x-ms-blob-type` ヘッダーが GCS CORS に未登録 → CORS 更新 + uploads.js 修正（コミット `1cf53b7`, `b5b4de5`）
- GCS プリサインド URL 生成で `content_type` が `"image/jpeg"` にハードコード → `content_types[index]` を正しく使用（コミット `148b7b5`）
- Firebase ID トークン期限切れ（401）→ `onIdTokenChanged` で自動更新（コミット `8110d20`）
- CI/CD で `GCP_SERVICE_ACCOUNT` 環境変数欠落 → `deploy-gcp.yml` に追加（コミット `27b10cc`）
- CSS 背景 SVG が絶対パス `/static/` を使用 → 相対パス `./` に変更（コミット `0ed0805`）
- GCS アップロードバケットが非公開 → `allUsers:objectViewer` を付与 + Pulumi 定義に IAMBinding 追加（コミット `0ed0805`）

**構成済み** (2026-02-23):

- Cloud Run `--min-instances=1` → コールドスタート（最大5秒）解消 ✅
- `gcp_backend.py`: `google.auth.default()` を `__init__()` でキャッシュ → リクエストごとのメタデータサーバー呼び出し排除 ✅

**残る課題**:

- CDN に HTTPS 未構成（HTTP のみ）。`TargetHttpsProxy` + マネージド SSL 証明書が必要
- CDN 経由の SPA ディープリンクが HTTP 404 を返す（Cloud Run URL はブラウザで正常動作）

---

## 接続確認コマンド

```bash
# AWS
curl -I https://d1tf3uumcm4bo1.cloudfront.net/
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/health

# Azure
curl -I https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net/
curl -s "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/health"

# GCP
curl -s http://34.117.111.182/ | head -3
curl -s https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app/health
```

---

## 本番環境

> 本番環境は独自の Pulumi スタック（デプロイ完了）を持ち、ステージングと完全に分離されています。
> フロントエンドは **React SPA**（Vite ビルド）として、CDN を経由するオブジェクトストレージから配信されます。
> `frontend_web`（Python SSR）は本番環境では使用されなくなりました。
> 詳細マイグレーション情報: [REACT_SPA_MIGRATION_REPORT.md](REACT_SPA_MIGRATION_REPORT.md)

### 本番ステータス概要 (2026-02-23)

本番環境のすべての API エンドポイントおよび CDN が正常に稼働しており、3つのクラウド環境すべてで同期されています。

| クラウド  | CDN ランディング (`/`) | SNS アプリ (`/sns/`) | API                   |
| --------- | :--------------------: | :------------------: | --------------------- |
| **AWS**   |      ✅ HTTP 200       |     ✅ React SPA     | ✅ /health /posts ok  |
| **Azure** |      ✅ HTTP 200       |     ✅ React SPA     | ✅ /api/health ok     |
| **GCP**   |      ✅ HTTP 200       |     ✅ React SPA     | ✅ /health /limits ok |

### 本番エンドポイント

3つのクラウドプロバイダーの本番環境における CDN / フロントエンド配信エンドポイント、API エンドポイント、および Distribution ID / リソース識別子を以下に示します。

| クラウド  | CDN / エンドポイント                                      | API エンドポイント                                                                               | Distribution ID        |
| --------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------- |
| **AWS**   | `d1qob7569mn5nw.cloudfront.net` / `www.aws.ashnova.jp`    | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`                                    | E214XONKTXJEJD         |
| **Azure** | `mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net` | `https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net` | mcad-production-diev0w |
| **GCP**   | `www.gcp.ashnova.jp`                                      | `https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app`                          | -                      |

**AWS Production SNS App** (`https://www.aws.ashnova.jp/sns/`):

AWS 本番環境の SNS アプリケーション構成の詳細。すべてのコアサービスが Pulumi により管理・デプロイされています。

| 項目             | 値                                                                     |
| ---------------- | ---------------------------------------------------------------------- |
| フロントエンド   | React SPA — S3 `multicloud-auto-deploy-production-frontend/sns/`       |
| CF Function      | `spa-sns-rewrite-production` (LIVE) — `/sns/` → `/sns/index.html` 変換 |
| Lambda (API)     | `multicloud-auto-deploy-production-api`                                |
| API_BASE_URL     | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`          |
| Cognito Pool     | `ap-northeast-1_50La963P2`                                             |
| Cognito Client   | `4h3b285v1a9746sqhukk5k3a7i`                                           |
| Cognito Redirect | `https://www.aws.ashnova.jp/sns/auth/callback`                         |
| DynamoDB         | `multicloud-auto-deploy-production-posts`                              |

### カスタムドメインステータス (ashnova.jp) — 2026-02-21

`ashnova.jp` ドメインの3つのクラウド環境での SSL/TLS デプロイ状態。すべてのカスタムドメインが完全に運用中であり、HTTPS による安全な通信が確立されています。

| クラウド  | URL                          | ステータス                                                  |
| --------- | ---------------------------- | ----------------------------------------------------------- |
| **AWS**   | https://www.aws.ashnova.jp   | ✅ **完全運用中** (HTTP/2 200, ACM 証明書設定済み)          |
| **Azure** | https://www.azure.ashnova.jp | ✅ **完全運用中** (HTTPS 200, DigiCert/GeoTrust 管理証明書) |
| **GCP**   | https://www.gcp.ashnova.jp   | ✅ **完全運用中** (HTTPS 200, TLS 証明書 Pulumi 管理)       |

**Landing page test (2026-02-23)**: `test-landing-pages.sh --env production` → **37/37 PASS (100%)** ✅

#### 完了作業 (2026-02-21)

| クラウド | 作業内容                                                   | 結果                                                                                                                                                                                               |
| -------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AWS      | ACM 証明書検証                                             | ✅ 証明書 `914b86b1` の `www.aws.ashnova.jp` (2027-03-12 有効) ISSUED 確認                                                                                                                         |
| AWS      | `aws cloudfront update-distribution` でエイリアス+ACM設定  | ✅ Distribution `E214XONKTXJEJD` にエイリアス `www.aws.ashnova.jp` + 証明書 `914b86b1` を設定 → `NET::ERR_CERT_COMMON_NAME_INVALID` 解決 → HTTP/2 200 運用中                                       |
| AWS      | Production `frontend-web` Lambda 環境変数修正 (2026-02-21) | ✅ `API_BASE_URL` が空→`localhost:8000` フォールバック（原因: `deploy-frontend-web-aws.yml` がシークレット依存、本番シークレット未設定）→ CI/CD を Pulumi outputs 使用に更新（コミット `fd1f422`） |
| Azure    | `az afd custom-domain create` + ルート紐付け               | ✅ DNS 承認 → 管理証明書成功 (GeoTrust, 2026-02-21 – 2026-08-21)                                                                                                                                   |
| Azure    | AFD ルート無効化→有効化トグル                              | ✅ エッジノードへのデプロイをトリガー → HTTPS 200 運用中                                                                                                                                           |
| Azure    | `az afd custom-domain update` (証明書エッジデプロイ)       | ✅ `CN=www.azure.ashnova.jp` 証明書を AFD POP に配布                                                                                                                                               |
| Azure    | `frontend-web` Function App 環境変数設定                   | ✅ API_BASE_URL, AUTH_PROVIDER, AZURE_TENANT_ID, AZURE_CLIENT_ID 等を設定                                                                                                                          |
| Azure    | Azure AD app redirect URI 追加                             | ✅ `https://www.azure.ashnova.jp/sns/auth/callback` を追加                                                                                                                                         |
| GCP      | `pulumi up --stack production` (SSL証明書作成)             | ✅ 証明書 `multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` PROVISIONING                                                                                                                       |
| GCP      | ACTIVE 証明書 `ashnova-production-cert-c41311` 追加        | ✅ HTTPS プロキシに追加 → `https://www.gcp.ashnova.jp` HTTPS 即座に運用開始                                                                                                                        |
| GCP      | Firebase 認可ドメイン更新                                  | ✅ Firebase Auth 認可ドメインに `www.gcp.ashnova.jp` を追加                                                                                                                                        |

#### 残課題

- **GCP**: ✅ `ashnova-production-cert-c41311` を HTTPS プロキシから切り離し・削除済み (2026-02-24)。`multicloud-auto-deploy-production-ssl-cert-3ee2c3ce` のみ使用中。推奨される設定状態は以降の pulumi up では自動的に維持されます。

---

### ✅ Production Issues — 全件解決済み (2026-02-24 v5)

本番環境で検出された 7 つのイシューはすべて解決され、確認テストも全て PASS しています。

#### ✅ 1. Azure Function App — 0 registered functions (API 404) — RESOLVED 2026-02-24

**症状**: `/api/health` → HTTP 404。Function App は Running 状態だが、Admin インターフェースで関数が表示されない。

**根本原因 (多層的で複雑)**:

1. `AzureWebJobsStorage` が非存在ストレージ `multicloudautodeploa148` を指していた
2. `functionAppConfig.deployment.storage.value` が非存在 blob URL を指していた
3. **決定的原因**: `functionAppConfig.runtime.version = "3.12"` だが、デプロイされた zip は Python 3.11 (`cpython-311`) でビルドされていた → クラウド実行時にモジュールロード失敗 → 関数が読み込まれない

**修正**: Python 3.12 (`docker run python:3.12-slim`) でパッケージを正しいアーキテクチャ向けに再ビルド・デプロイ

**確認**: `admin/functions` → `[{"name":"HttpTrigger"}]` ✅ / `/api/health` → HTTP 200 ✅

#### ✅ 3. GCP Production API — `/limits` エンドポイント 404 — RESOLVED 2026-02-24

**症状**: `https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app/limits` へのリクエストが HTTP 404 を返す。直接 Cloud Run サービスへのアクセスも同様に失敗。

**修正**: GCP production API を最新リビジョン (`00013-big`) に再デプロイ。`CORS_ORIGINS` 環境変数に本番ドメイン `https://www.gcp.ashnova.jp` を追加して、クロスオリジンリクエストを許可。

**確認済み**: `GET /limits` → `{"maxImagesPerPost":10}` HTTP 200 ✅ CDN 経由のリクエストも成功

#### ✅ 4. AWS Production CloudFront — セキュリティヘッダーポリシー未設定 — RESOLVED 2026-02-24

**症状**: CloudFront Distribution が HSTS、CSP、X-Frame-Options などのセキュリティヘッダーを返していない。

**修正**: 既存ポリシー `multicloud-auto-deploy-production-security-headers` (ID: `aaad020f-c94c-4143-ba2c-4b7921a1a6de`) を DefaultCacheBehavior と `/sns*` CacheBehavior の両方に適用。ETag が `E3P5ROKL5A1OLE` から `E3JWKAKR8XB7XF` に更新されました。

**確認され**: CloudFront Distribution `E214XONKTXJEJD` がすべてのセキュリティヘッダー（HSTS/CSP/X-Content-Type-Options/X-Frame-Options/Referrer-Policy/XSS-Protection）をレスポンスに含める ✅

#### ✅ 5. AWS Production SNS — Network Error (CI/CD customDomain 上書き) — RESOLVED 2026-02-24

**症状**: `https://www.aws.ashnova.jp/sns/` の SNS アプリで API 呼び出し時に "Network Error" が発生。Axios が HTTP status 0 を返す（CORS エラーの典型的な兆候）。

**根本原因チェーン**:

1. `deploy-aws.yml` の "Sync Pulumi Config" ステップが GitHub リポジトリシークレット `${{ secrets.AWS_CUSTOM_DOMAIN }}` = `staging.aws.ashnova.jp` を使用
2. `pulumi config set multicloud-auto-deploy-aws:customDomain "staging.aws.ashnova.jp"` が本番 `Pulumi.production.yaml` を誤って上書き
3. `pulumi stack output custom_domain` が `staging.aws.ashnova.jp` を返す（期待値: `www.aws.ashnova.jp`）
4. Lambda 環境変数 `CORS_ORIGINS` = `...,https://staging.aws.ashnova.jp,...`（誤）→ FastAPI が `Origin: https://www.aws.ashnova.jp` を拒否
5. ブラウザが "Network Error" を報告

**修正 (コミット `3ea6a08` v1.17.10)**:

- `deploy-aws.yml` を GitHub Secrets ではなく `Pulumi.${STACK_NAME}.yaml` から値を読むように修正
- React SPA 再ビルド・デプロイ（新バンドル `index-Ch-ro-3Y.js`）
- Lambda `CORS_ORIGINS` から `staging.aws.ashnova.jp` を即時削除

**確認**: Lambda `CORS_ORIGINS` = `https://d1qob7569mn5nw.cloudfront.net,https://www.aws.ashnova.jp,http://localhost:5173` ✅

#### ✅ 6. Azure プロフィール画面 CORS エラー — RESOLVED 2026-02-24

**症状**: `https://www.azure.ashnova.jp/sns/profile` でプロフィール取得時に CORS エラー

**根本原因**:

1. Azure Function App は Kestrel がプラットフォームレベル CORS 判定を FastAPI `CORSMiddleware` の手前に実行
2. `deploy-azure.yml` が `secrets.AZURE_CUSTOM_DOMAIN` (= `staging.azure.ashnova.jp`) を使用
3. `CORS_ORIGINS` とプラットフォーム CORS の両方に `https://www.azure.ashnova.jp` が欠落

**即時修正**:

- `az functionapp config appsettings set ... CORS_ORIGINS=...,https://www.azure.ashnova.jp,...` ✅
- `az functionapp cors add --allowed-origins "https://www.azure.ashnova.jp"` ✅

**根本修正 (v1.17.15)**: `deploy-azure.yml` を stack 名から `customDomain` を読むように変更

#### ✅ 7. Azure ログイン後に staging SNS に遷移 — RESOLVED 2026-02-24

**症状**: `www.azure.ashnova.jp/sns/` でログイン後に `staging.azure.ashnova.jp/sns/` にリダイレクト

**根本原因**:

1. フロントエンドが `VITE_AZURE_REDIRECT_URI=https://staging.azure.ashnova.jp/sns/auth/callback` でビルドされていた
2. Azure AD アプリの redirect URIs に `www.azure.ashnova.jp` がなかった

**即時修正**:

- `az ad app update` で `www.azure.ashnova.jp` を redirect URIs に追加 ✅
- フロントエンドを `VITE_AZURE_REDIRECT_URI=https://www.azure.ashnova.jp/sns/auth/callback` で再ビルド → `index-CPcQQsCR.js` ✅

**根本修正 (v1.17.16)**: `deploy-azure.yml` の全4箇所の `secrets.AZURE_CUSTOM_DOMAIN` を stack マッピングに変更

---

**テスト結果 (2026-02-24)**:

すべての本番環境エンドポイントでテストを実施し、完全な機能動作を確認しました。

```
test-cloud-env.sh production → PASS: 14, FAIL: 0, WARN: 3
test-azure-sns.sh            → PASS: 10, FAIL: 0
test-gcp-sns.sh              → PASS: 10, FAIL: 0
```

---

## E2E テストスクリプト (2026-02-24)

> commit `73af560` — `scripts/` 配下の4ファイルを改良

### `test-sns-all.sh` (新規)

3クラウド統合ラッパー。すべてのクラウドを一括でテストし、最後にサマリーテーブルを表示する。

```bash
# 基本使用 (read-only, production)
bash scripts/test-sns-all.sh --env production

# 特定クラウドのみ
bash scripts/test-sns-all.sh --env production --only azure

# 書き込みテスト有効 (AWS: Cognito 自動認証)
bash scripts/test-sns-all.sh --env production --write \
  --aws-username user@example.com --aws-password *** --aws-client-id 4h3b285v1a9746sqhukk5k3a7i

# 書き込みテスト有効 (GCP: gcloud 自動認証)
bash scripts/test-sns-all.sh --env production --write --gcp-auto-token
```

**サマリー出力例** (production read-only, 2026-02-24):

```
  Cloud       PASS    FAIL    SKIP  Status
  ────────  ──────  ──────  ──────  ──────────
  aws            9       0       4  ✅ PASS
  azure         17       0       2  ✅ PASS
  gcp           13       0       4  ✅ PASS
  ────────  ──────  ──────  ──────  ──────────
  TOTAL         39       0      10
```

### 各スクリプトの改良内容

| スクリプト                  | 追加機能                                                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/test-sns-aws.sh`   | `--username`/`--password`/`--client-id` で Cognito 自動認証、X-Amz-Signature 検証、binary PUT to S3、imageUrl HTTP 200 確認     |
| `scripts/test-sns-gcp.sh`   | `--auto-token` で `gcloud auth print-identity-token` 自動認証、X-Goog-Signature 検証、binary PUT to GCS、imageUrl HTTP 200 確認 |
| `scripts/test-sns-azure.sh` | `x-ms-blob-type: BlockBlob` で binary PUT to Azure Blob (HTTP 201)、SAS read URL HTTP 200 確認                                  |

### テスト一覧 (write モード時の追加項目)

| #   | テスト                | 概要                                                                                       |
| --- | --------------------- | ------------------------------------------------------------------------------------------ |
| 5-2 | 署名URL検証           | presigned URL に `X-Amz-Signature=` / `X-Goog-Signature=` / SAS token が含まれることを確認 |
| 5-3 | binary PUT            | 1×1 PNG を実際に presigned URL へ PUT し HTTP 200/201 を確認                               |
| 5-4 | imageUrl アクセス確認 | PUT したキーで POST /posts → GET /posts/:id → imageUrls[0] に GET → HTTP 200 を確認        |

---

## コスト監視ツール

マルチクラウド + GitHub の費用を一元管理するツールが `scripts/` 配下に実装済みです。

### CLI レポート (`scripts/cost_report.py`)

```bash
python3 scripts/cost_report.py                 # デフォルト: 過去3ヶ月
python3 scripts/cost_report.py --months 6      # 過去6ヶ月
python3 scripts/cost_report.py --json          # JSON 出力
python3 scripts/cost_report.py --aws-only      # AWS のみ
python3 scripts/cost_report.py --azure-only    # Azure のみ
```

### macOS メニューバーウィジェット (`scripts/mac-widget/`)

[xbar](https://xbarapp.com) を使った 1 時間ごと自動更新ウィジェット。

```bash
brew install --cask xbar
bash scripts/mac-widget/install.sh
open -e scripts/mac-widget/.env    # 認証情報を設定
```

### 通貨処理

| Provider | 方式                                                                                                                   |
| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| AWS      | Cost Explorer は USD 固定 → [open.er-api.com](https://open.er-api.com) で リアルタイム USD/JPY 変換 (失敗時 ¥150 固定) |
| Azure    | Cost Management API の `rows[n][2]` から通貨コードを直接取得 (JPY)                                                     |
| GCP      | Billing API — サービスアカウント or `gcloud auth`                                                                      |
| GitHub   | Billing API 廃止 (HTTP 410) → `actions/cache/usage` + runs 件数で代替                                                  |

### .env 設定ファイル

`scripts/mac-widget/.env` (git 管理外) に認証情報を記載します。
テンプレート: `scripts/mac-widget/cost-monitor.env.sample`

| 変数                    | 用途                                      |
| ----------------------- | ----------------------------------------- |
| `AZURE_SUBSCRIPTION_ID` | Azure Cost Management                     |
| `GCP_BILLING_ACCOUNT`   | GCP Billing (`01XXXX-XXXXXX-XXXXXX` 形式) |
| `GCP_PROJECT_ID`        | GCP プロジェクト ID                       |
| `GITHUB_TOKEN`          | GitHub Actions 使用量取得                 |
| `GH_REPO`               | `owner/repo` 形式 (個人リポジトリ用)      |

AWS は `~/.aws/credentials` の default プロファイルを使用（追加設定不要）。

マルチクラウド + GitHub の費用を一元管理するツールが `scripts/` 配下に実装済みです。

### CLI レポート (`scripts/cost_report.py`)

```bash
python3 scripts/cost_report.py                 # デフォルト: 過去3ヶ月
python3 scripts/cost_report.py --months 6      # 過去6ヶ月
python3 scripts/cost_report.py --json          # JSON 出力
python3 scripts/cost_report.py --aws-only      # AWS のみ
python3 scripts/cost_report.py --azure-only    # Azure のみ
```

### macOS メニューバーウィジェット (`scripts/mac-widget/`)

[xbar](https://xbarapp.com) を使った 1 時間ごと自動更新ウィジェット。

```bash
brew install --cask xbar
bash scripts/mac-widget/install.sh
open -e scripts/mac-widget/.env    # 認証情報を設定
```

### 通貨処理

| プロバイダー | 方式                                                                                                                   |
| ------------ | ---------------------------------------------------------------------------------------------------------------------- |
| AWS          | Cost Explorer は USD 固定 → [open.er-api.com](https://open.er-api.com) で リアルタイム USD/JPY 変換 (失敗時 ¥150 固定) |
| Azure        | Cost Management API の `rows[n][2]` から通貨コードを直接取得 (JPY)                                                     |
| GCP          | Billing API — サービスアカウント or `gcloud auth`                                                                      |
| GitHub       | Billing API 廃止 (HTTP 410) → `actions/cache/usage` + runs 件数で代替                                                  |

### .env 設定ファイル

`scripts/mac-widget/.env` (git 管理外) に認証情報を記載します。
テンプレート: `scripts/mac-widget/cost-monitor.env.sample`

| 変数                    | 用途                                      |
| ----------------------- | ----------------------------------------- |
| `AZURE_SUBSCRIPTION_ID` | Azure Cost Management                     |
| `GCP_BILLING_ACCOUNT`   | GCP Billing (`01XXXX-XXXXXX-XXXXXX` 形式) |
| `GCP_PROJECT_ID`        | GCP プロジェクト ID                       |
| `GITHUB_TOKEN`          | GitHub Actions 使用量取得                 |
| `GH_REPO`               | `owner/repo` 形式 (個人リポジトリ用)      |

AWS は `~/.aws/credentials` の default プロファイルを使用（追加設定不要）。

---

## AWS 管理コンソールリンク

- [API Gateway](https://ap-northeast-1.console.aws.amazon.com/apigateway)
- [Lambda](https://ap-northeast-1.console.aws.amazon.com/lambda)
- [CloudFront](https://console.aws.amazon.com/cloudfront/v3/home)

## Azure ポータルリンク

- [リソースグループ](https://portal.azure.com/#@/resource/subscriptions/29031d24-d41a-4f97-8362-46b40129a7e8/resourceGroups/multicloud-auto-deploy-staging-rg)
- [Function Apps](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Web%2Fsites)
- [Front Door](https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.Cdn%2Fprofiles)

## GCP コンソールリンク

- [Cloud Run](https://console.cloud.google.com/run?project=ashnova)
- [Cloud Storage](https://console.cloud.google.com/storage/browser?project=ashnova)
- [Firestore](https://console.cloud.google.com/firestore/data?project=ashnova)

---

## FinOps — GCP 未使用静的 IP アドレス監査 (2026-02-21)

> GCP FinOps から の指摘に対応して実施した監査。プロジェクト `ashnova` のすべての静的 IP アドレスをレビューしました。

### すべての IP アドレス

```bash
gcloud compute addresses list --project=ashnova \
  --format="table(name,address,status,addressType,users.list())"
```

| 名前                                       | IP アドレス    | ステータス      | 作成日     | 使用中                              |
| ------------------------------------------ | -------------- | --------------- | ---------- | ----------------------------------- |
| `multicloud-auto-deploy-production-cdn-ip` | 34.8.38.222    | ✅ IN_USE       | —          | Production CDN (Forwarding Rule ×2) |
| `multicloud-auto-deploy-staging-cdn-ip`    | 34.117.111.182 | ✅ IN_USE       | —          | Staging CDN (Forwarding Rule ×2)    |
| `ashnova-production-ip-c41311`             | 34.54.250.208  | ⚠️ **RESERVED** | 2026-02-11 | なし                                |
| `multicloud-frontend-ip`                   | 34.120.43.83   | ⚠️ **RESERVED** | 2026-02-14 | なし                                |
| `simple-sns-frontend-ip`                   | 34.149.225.173 | ⚠️ **RESERVED** | 2026-01-30 | なし                                |

### 未使用 IP の背景

| 名前                           | 推定履歴                                                                                                                                                 |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `simple-sns-frontend-ip`       | プロジェクト初期（`simple-sns` という名前だった時期、2026-01-30）に作成。Pulumi コードや Forwarding Rule に参照なし。                                    |
| `ashnova-production-ip-c41311` | Production CDN 用に作成（Pulumi サフィックス `c41311` から判断、2026-02-11）されたが、後に `multicloud-auto-deploy-production-cdn-ip` に置き換えられた。 |
| `multicloud-frontend-ip`       | 2026-02-14 に作成。コードベースやドキュメントに参照なし。実験的に予約されて放置されたと推定。                                                            |

> **注**: これら3つはすべて Pulumi コードや Forwarding Rule とリンクされておらず、すぐに解放できます。

### 解放コマンド

```bash
gcloud compute addresses delete ashnova-production-ip-c41311 --global --project=ashnova --quiet
gcloud compute addresses delete multicloud-frontend-ip          --global --project=ashnova --quiet
gcloud compute addresses delete simple-sns-frontend-ip          --global --project=ashnova --quiet
```

> ⚠️ 削除は不可逆です。実行前に `gcloud compute addresses describe <name> --global` で各 IP に関連リソースがないことを確認してください。

---

## FinOps — GCP 未使用 Cloud Storage バケット監査 (2026-02-21)

> 静的 IP 監査のフォローアップとして実施。Terraform 時代のレガシーバケットと壊れた Cloud Function を特定しました。

### すべてのバケット (プロジェクト: ashnova)

| バケット名                                                               | サイズ    | 判定        | 備考                                                                             |
| ------------------------------------------------------------------------ | --------- | ----------- | -------------------------------------------------------------------------------- |
| `ashnova-multicloud-auto-deploy-production-frontend`                     | —         | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-production-function-source`              | 5 MB      | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-production-uploads`                      | —         | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-frontend`                        | —         | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-function-source`                 | 5 MB      | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-landing`                         | 8 KB      | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova-multicloud-auto-deploy-staging-uploads`                         | —         | ✅ Active   | Pulumi 管理                                                                      |
| `ashnova.firebasestorage.app`                                            | —         | ✅ Keep     | Firebase システム管理                                                            |
| `ashnova_cloudbuild`                                                     | —         | ✅ Keep     | Cloud Build システム管理                                                         |
| `gcf-v2-sources-899621454670-asia-northeast1`                            | 433 MB    | ✅ Keep     | アクティブな Cloud Function v2 のソース                                          |
| `gcf-v2-uploads-899621454670.asia-northeast1.cloudfunctions.appspot.com` | —         | ✅ Keep     | Cloud Functions アップロードステージング                                         |
| `ashnova-staging-frontend`                                               | **empty** | 🗑️ **削除** | Terraform レガシー。`ashnova-multicloud-auto-deploy-staging-frontend` に移行済み |
| `ashnova-staging-function-source`                                        | **65 MB** | 🗑️ **削除** | Terraform レガシー。2026-02-14 の古い zip を含む                                 |
| `multicloud-auto-deploy-tfstate`                                         | **empty** | 🗑️ **削除** | 古い Terraform state バケット。空。                                              |
| `multicloud-auto-deploy-tfstate-gcp`                                     | **6 KB**  | 🗑️ **削除** | 上記2つのバケットの Terraform state のみ保持                                     |

### 削除可能バケットの背景

| バケット名                           | 推定履歴                                                                                                                                                                     |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ashnova-staging-frontend`           | 旧 Terraform 設定のフロントエンドバケット（`ashnova-staging-*` 命名）。`ashnova-multicloud-auto-deploy-staging-frontend`（Pulumi 管理）に完全移行済み。空。                  |
| `ashnova-staging-function-source`    | 同じ Terraform 設定の Cloud Function ソースバケット。2026-02-14 の古い 65 MB の zip を含む。`ashnova-multicloud-auto-deploy-staging-function-source`（5 MB）に置き換え済み。 |
| `multicloud-auto-deploy-tfstate`     | AWS Terraform state バケット候補として作成されたが未使用。空。                                                                                                               |
| `multicloud-auto-deploy-tfstate-gcp` | `ashnova-staging-*` 2つのバケットの Terraform state を保持。コードベースに `.tf` ファイルなし。4つをセットで削除。                                                           |

### おまけ: 壊れた Cloud Function（関連リソース）

| リソース                               | 状態       | 詳細                                                                                                                                      |
| -------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `mcad-staging-api` (Cloud Function v2) | **FAILED** | `Cloud Run service not found` エラー。Cloud Run サービスは削除されたが Function 定義が残っている。Pulumi/現行コードに参照なし。削除可能。 |

### 削除コマンド

```bash
# 4つのバケットを削除（内容含む）— tfstate-gcp は最後に削除
gcloud storage rm --recursive gs://ashnova-staging-frontend           --project=ashnova
gcloud storage rm --recursive gs://ashnova-staging-function-source    --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate     --project=ashnova
gcloud storage rm --recursive gs://multicloud-auto-deploy-tfstate-gcp --project=ashnova

# 壊れた Cloud Function も削除
gcloud functions delete mcad-staging-api \
  --region=asia-northeast1 --project=ashnova --v2 --quiet
```

> ⚠️ `multicloud-auto-deploy-tfstate-gcp` は `ashnova-staging-frontend` と `ashnova-staging-function-source` の Terraform state を含みます。4つのバケットをセットで削除してください。

---

## 次のセクション

→ [07 — ランブック](AI_AGENT_07_RUNBOOKS_JA.md)
