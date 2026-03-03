# 02 — アーキテクチャ

> 第II部 — アーキテクチャ・設計 | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## システム概要

```
ユーザー
  │
  ├─ [AWS]   CloudFront ──► S3（React SPA：ランディング + SNSページ）  ← 静的
  │         API Gateway v2 ──▶ Lambda（Python 3.13）──▶ DynamoDB
  │
  ├─ [Azure] Front Door ─┬─ /sns/* ──► Blob Storage $web/sns/（React SPA ← 静的）
  │                       └─ /*     ──► Blob Storage $web（ランディング ← 静的）
  │         Azure Functions func ──► Cosmos DB（Serverless）
  │
  └─ [GCP]   Cloud CDN ─┬─ /sns/* ──► GCS バケット /sns/（React SPA ← 静的）
                        └─ /*     ──► GCS（ランディング ← 静的）
             Cloud Run api ──► Firestore
```

> **フロントエンドアーキテクチャ**：3つのクラウドすべてが SNS アプリを **静的 React SPA** として提供
> オブジェクトストレージ（S3 / Blob Storage / GCS）にデプロイされ、CDN 経由で配信される。
> Python `services/frontend_web` SSR サービスは **スーパーセッドされた** もので、CDN パスに含まれていない。
> React SPA ワークフロー：`deploy-frontend-web-{aws,azure,gcp}.yml`
> SPA ルーミング（`/sns/*` → `/sns/index.html` にリライト）：
>
> - AWS：CloudFront Function `spa-sns-rewrite-{stack}`
> - Azure：AFD RuleSet `SpaRuleSet` + URL Rewrite アクション
> - GCP：CDN バックエンドバケットが GCS をサーブ；`/sns/*` パスルール URL マップから削除（GCS にフォールスルー）

---

## ストレージパス構造

```
bucket-root/
├── index.html          ← ランディングページ
├── error.html
├── aws/
├── azure/
├── gcp/
└── sns/               ← React SNS アプリ（AWS のみ — Vite ビルド、base="/sns/"）
    ├── index.html
    └── assets/
        ├── index-*.js
        └── index-*.css
```

**CI デプロイ先**：

| コンテンツ         | AWS                             | Azure                    | GCP                             |
| ------------------ | ------------------------------- | ------------------------ | ------------------------------- |
| ランディングページ | `s3://bucket/`                  | `$web/`                  | `gs://bucket/`                  |
| SNSページ          | `s3://bucket/sns/`（React SPA） | `$web/sns/`（React SPA） | `gs://bucket/sns/`（React SPA） |

3つのクラウドすべてが SNS アプリを静的 React SPA として提供。CDN が SPA ルーティングを処理：

- **AWS**：CloudFront Function が `/sns` および `/sns/` → `/sns/index.html` にリライト
- **Azure**：AFD `SpaRuleSet` URL Rewrite が `/sns/*`（非アセット）→ `/sns/index.html` にリライト
- **GCP**：GCS が `sns/index.html` をデフォルトとして配信；ディープリンクには CDN レベルの処理が必要（SPA ルーティングはブラウザー History API で部分的に処理）

---

## AWS アーキテクチャ詳細

```
CloudFront（E1TBH4R432SZBZ / ステージング、E214XONKTXJEJD / 本番）
  ├── /sns/* → S3: multicloud-auto-deploy-{env}-frontend/sns/（React SPA）
  │            CloudFront Function `spa-sns-rewrite-{stack}` が /sns を /sns/index.html にリライト
  └── /*     → S3: multicloud-auto-deploy-{env}-frontend/（ランディングページ）

S3: multicloud-auto-deploy-{env}-frontend
  ├── index.html        ← React SPA エントリーポイント（Vite ビルド）
  ├── assets/           ← JS / CSS バンドル
  └── （ランディング、aws/、azure/、gcp/ ページ）

API Gateway v2 HTTP（z42qmqdqac / ステージング）
  └── $default → Lambda: multicloud-auto-deploy-{env}-api（バックエンド）
                  └── DynamoDB: multicloud-auto-deploy-{env}-posts（PAY_PER_REQUEST）
                       ← Single Table Design（PK/SK）
                       ← POSTS パーティション：投稿データ（GSI：postId / userId / createdAt）
                       ← PROFILES パーティション：ユーザープロフィール
                  └── S3: multicloud-auto-deploy-{env}-images（画像アップロード）
                       ← IMAGES_BUCKET_NAME 環境変数で参照

Lambda: multicloud-auto-deploy-{env}-frontend-web [削除済み — Python SSR は React SPA に統合]
  デッドコード削除 2026-02-22。CloudFront `/sns/*` は現在 S3 に直接ルーティング。
  参照: REFACTORING_REPORT_20260222.md § 3
```

**注意**：`frontend-web` Lambda は当初 Python で SNS 画面を SSR するために作られたが、
React + S3 へ移行済み。Lambda 自体は削除されていない場合があるが、CloudFront の
`/sns/*` 動作は現在 API Gateway（バックエンド API）を向いている。

**Lambda Layer**：`multicloud-auto-deploy-staging-dependencies`
— FastAPI / Mangum / JWT 依存関係のみを含む；boto3 は Lambda ランタイムに含まれる。
— アプリコード（~78 KB）と Layer（~8-10 MB）は別々にデプロイ。

**主要環境変数**：`POSTS_TABLE_NAME`、`IMAGES_BUCKET_NAME`、`COGNITO_USER_POOL_ID`
**可観測性**：AWS Lambda Powertools（Logger / Tracer / Metrics）— `SimpleSNS` ネームスペース

---

## Azure アーキテクチャ詳細

> ✅ **React SPA に移行**：SNS ページは現在 Blob Storage（静的ファイル）から配信される。
> Python `frontend_web` Azure Function は `deploy-frontend-web-azure.yml` に統合された。

```
Front Door（multicloud-auto-deploy-staging-fd）
  エンドポイント: mcad-staging-d45ihd
  ├── /sns/*  → オリジン：Blob Storage $web/sns/（React SPA — 静的 HTML/JS/CSS）
  │               SpaRuleSet が /sns/* → /sns/index.html にリライト（SPA ルーティング）
  └── /*      → オリジン：Blob Storage $web（ランディングページのみ）
                  mcadwebd45ihd.z11.web.core.windows.net

Azure Functions frontend-web（FC1 FlexConsumption）[レガシー — CDN パスに含まれない]
  └── デプロイ済みだが、React SPA in Blob Storage に統合された
     本番環境：multicloud-auto-deploy-production-frontend-web-v2（alwaysReady http=1）

Azure Functions：multicloud-auto-deploy-staging-func（Flex Consumption）← バックエンド API
  └── HTTP トリガー：/{*route}（関数名：HttpTrigger）
        │  ← FastAPI（Mangum なし、カスタム ASGI ブリッジ）にフォワード
        └── Cosmos DB（Serverless）
             ← DB：simple-sns / コンテナー：items
             ← 環境変数：COSMOS_DB_ENDPOINT / COSMOS_DB_KEY
             ← COSMOS_DB_DATABASE（デフォルト：simple-sns）
             ← COSMOS_DB_CONTAINER（デフォルト：items）
        └── Azure Blob Storage：images コンテナー（画像アップロード）
             ← AZURE_STORAGE_ACCOUNT_NAME / AZURE_STORAGE_ACCOUNT_KEY / AZURE_STORAGE_CONTAINER
```

**リソースグループ**：`multicloud-auto-deploy-staging-rg`（japaneast）
**WAF**：未設定（Standard SKU；Premium SKU で追加可能）

---

## GCP アーキテクチャ詳細

> ✅ **React SPA に移行**：SNS ページは現在 GCS（静的ファイル）から Cloud CDN 経由で配信される。
> Cloud Run `frontend-web` へのルーティングの `/sns/*` パスルールは URL マップから削除された。

```
グローバル IP：34.117.111.182
  └── HTTP フォワーディングルール
        └── URL マップ
              └── /*（デフォルト）→ バックエンドバケット → GCS：ashnova-multicloud-auto-deploy-staging-frontend
                               （/sns/ の React SPA + / のランディング）
              注記：/sns/* パスルール削除（2026-02-22）— GCS デフォルトにフォールスルー

Cloud Run：multicloud-auto-deploy-staging-frontend-web [レガシー — CDN パスに含まれない]
  URL：https://multicloud-auto-deploy-staging-frontend-web-899621454670.asia-northeast1.run.app
  └── デプロイ済みだが CDN はここにリクエストをルーティングしない
  CDN カスタムレスポンスヘッダー：Cross-Origin-Opener-Policy: same-origin-allow-popups

Cloud Run：multicloud-auto-deploy-staging-api（バックエンド API）
  └── Firestore（デフォルト）
       ← posts コレクション：投稿データ（GCP_POSTS_COLLECTION、デフォルト：posts）
       ← profiles コレクション：ユーザープロフィール（GCP_PROFILES_COLLECTION、デフォルト：profiles）
  └── GCS：ashnova-multicloud-auto-deploy-staging-uploads（署名付き URL アップロード/画像表示）
       ← GCP_STORAGE_BUCKET 環境変数で参照
```

**注意**：GCP はクラシック外部 LB（`EXTERNAL` スキーム）を使用。
URL マップパスベースルーティング（`/sns/*` → Cloud Run）には `EXTERNAL_MANAGED` が必要；現在は すべてのパスで GCS にフォールバックする可能性 — 検証が必要。

---

## API ルート

| ルータープレフィックス | 主なエンドポイント                | 認証       |
| ---------------------- | --------------------------------- | ---------- |
| `/posts`               | GET/POST/PUT/DELETE（投稿 CRUD）  | 必要       |
| `/uploads`             | POST（署名付き URL 発行）         | 必要       |
| `/profile`             | GET/PUT（プロフィール取得・更新） | 必要       |
| `/api/messages/`       | 旧フロントエンド互換エイリアス    | オプション |

旧フロントエンドとの後方互換のため `/api/messages/` エイリアスは維持されているが、新規実装は `/posts` を使用する。

---

## バックエンドクラウド自動検出ロジック

```python
# services/api/app/config.py
# 環境変数 CLOUD_PROVIDER で明示的に設定するか、自動検出：
AWS_EXECUTION_ENV   存在 → "aws"
WEBSITE_INSTANCE_ID 存在 → "azure"
K_SERVICE           存在 → "gcp"
それ以外                  → "local"
```

---

## 認証フロー

```
API バックエンド（services/api）：
  クライアント
    → Authorization: Bearer <JWT>
    → FastAPI auth.py（AUTH_DISABLED=false の場合）
         → jwt_verifier.py
              AWS:   Cognito JWKS エンドポイント検証
              Azure: Azure AD JWKS 検証
              GCP:   Firebase Auth JWKS 検証
         → 検証 OK → routes/*

GCP frontend-web（services/frontend_web）— 別の httponly Cookie フロー：
  ブラウザー → /sns/login
    → Firebase Google Sign-In ポップアップ（Firebase SDK v10.8.0）
    → POST /sns/session { token: <Firebase ID トークン> }
    → FastAPI がトークンを検証 → httponly セッションクッキーを設定
    → onIdTokenChanged → トークン有効期限時にセッションクッキーを自動更新
```

ステージング：`AUTH_DISABLED=false`（過去には誤って `true` に設定されていた — 現在は修正）

---

## セキュリティ設定ステータス

| 機能                 | AWS              | Azure             | GCP                    |
| -------------------- | ---------------- | ----------------- | ---------------------- |
| HTTPS 強化           | ✅ CloudFront    | ✅ Front Door     | ❌ HTTP のみ（要修正） |
| WAF                  | ❌ 未設定        | ❌ 未設定（TODO） | ✅ Cloud Armor         |
| データ暗号化         | ✅ SSE-S3        | ✅ Azure SSE      | ✅ Google 管理         |
| バージョンストレージ | ✅               | ✅                | ✅                     |
| アクセスログ         | ✅               | ❌                | ✅                     |
| セキュリティヘッダー | ✅ CloudFront RP | ❌                | ❌                     |

---

## 次のセクション

→ [03 — API とデータモデル](AI_AGENT_03_API_JA.md)
