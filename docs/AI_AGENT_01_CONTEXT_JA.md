# 01 — コンテキスト：概要とリポジトリレイアウト

> 第I部 — オリエンテーション | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## このプロジェクトは何か

**multicloud-auto-deploy** は、**同一のフルスタックアプリケーション**（SNSスタイルのメッセージングアプリ）を
**AWS、Azure、GCP** に完全に自動化された CI/CD パイプライン経由で同時にデプロイするプラットフォームである。

- フロントエンド: React 19 + Vite + TypeScript + Tailwind CSS
- バックエンド: FastAPI（Python 3.13）— Lambda / Azure Functions / Cloud Run
- データベース: DynamoDB / Cosmos DB / Firestore（共有論理スキーマ）
- IaC: Pulumi Python SDK
- CI/CD: GitHub Actions

---

## ライブエンドポイント（ステージング）

### AWS (ap-northeast-1)

| 目的              | URL                                                           |
| ----------------- | ------------------------------------------------------------- |
| CDN (CloudFront)  | `https://d1tf3uumcm4bo1.cloudfront.net`                       |
| API (API Gateway) | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com` |
| カスタムドメイン  | `https://www.aws.ashnova.jp`                                  |

### Azure (japaneast)

| 目的             | URL                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------- |
| CDN (Front Door) | `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net`                                |
| API (Functions)  | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net` |
| カスタムドメイン | `https://www.azure.ashnova.jp`                                                                |

> **注意**：Azure API URL は Function App ベース URL **であり、パスサフィックスは含まない**。
> 関数はワイルドカードルーム `{*route}` を使用するため、すべての API パス（例：`/health`、`/posts`）
> がベース URL で直接配信される。`/api/HttpTrigger` パスは **使用されない**。

### GCP (asia-northeast1)

| 目的                           | URL                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- |
| CDN (Cloud CDN)                | `http://34.117.111.182`                                                                                 |
| API (Cloud Run)                | `https://multicloud-auto-deploy-staging-api-899621454670.asia-northeast1.run.app`                       |
| Web フロントエンド (Cloud Run) | `https://multicloud-auto-deploy-staging-frontend-web-899621454670.asia-northeast1.run.app` (legacy SSR) |
| カスタムドメイン               | `https://www.gcp.ashnova.jp`                                                                            |

> **注意**：Cloud Run `frontend-web` サービスは存在するが、CDN は `/sns/*` を GCS バケット（React SPA）にルーティングする —
> Cloud Run ではない。Cloud Run URL はレガシーである。

---

## 技術スタックサマリー

```
フロントエンド（SNSページ）
  AWS:   React 19.2 / Vite 7.3 / TypeScript / Tailwind CSS  ← S3 内の静的 SPA（ステージング + 本番）
  Azure: React 19.2 / Vite / TypeScript  ← Blob Storage $web/sns/ 内の静的 SPA（本番）
         (services/frontend_web Python SSR はスーパーセッドされた; CI は現在 deploy-frontend-web-azure.yml で React SPA をデプロイ)
  GCP:   React 19.2 / Vite / TypeScript  ← GCS sns/ プリフィックス内の静的 SPA（ステージング + 本番）
         (Cloud Run frontend-web は存在するが、CDN は Cloud Run ではなく GCS バケットにルーティング)

バックエンド API
  FastAPI 1.0 / Python 3.13 / Pydantic v2
  AWS:   Lambda（x86_64）+ API Gateway v2（HTTP）+ Lambda Layer + Mangum アダプター
  Azure: Azure Functions（Python 3.13、FC1 FlexConsumption）
  GCP:   Cloud Run（Python 3.13、gen2）
  ローカル: uvicorn + DynamoDB Local + MinIO

データベース（共有論理スキーマ）
  AWS:   DynamoDB — テーブル: {project}-{stack}-posts
  Azure: Cosmos DB Serverless — db: messages / container: messages
  GCP:   Firestore（Native）— コレクション: messages / posts

インフラストラクチャ
  Pulumi Python SDK 3.x
  状態: Pulumi Cloud（リモート）

認証
  AWS:   Amazon Cognito（Pulumi により自動プロビジョニング）
  Azure: Azure AD（Pulumi により自動プロビジョニング）
  GCP:   Firebase Auth（Google Sign-In、httponly Cookie セッション）
  ステージング: AUTH_DISABLED=false  ← 決して true になってはいけない
```

---

## リポジトリディレクトリツリー

```
multicloud-auto-deploy/               ← ワークスペースルート = git リポジトリルート
│
├── .github/
│   └── workflows/                    ← ★ 実際のワークフロー — CI はこれらのみを読む
│       ├── deploy-aws.yml
│       ├── deploy-azure.yml
│       ├── deploy-gcp.yml
│       ├── deploy-landing-aws.yml
│       ├── deploy-landing-azure.yml
│       ├── deploy-landing-gcp.yml
│       ├── deploy-frontend-web-aws.yml
│       ├── deploy-frontend-web-azure.yml
│       └── deploy-frontend-web-gcp.yml
│
├── infrastructure/
│   └── pulumi/
│       ├── aws/
│       │   ├── __main__.py           ← すべての AWS リソース（S3/CF/Lambda/APIGW/DDB/Cognito）
│       │   ├── Pulumi.yaml
│       │   ├── Pulumi.staging.yaml
│       │   └── requirements.txt
│       ├── azure/
│       │   ├── __main__.py           ← すべての Azure リソース（Storage/FuncApp/CosmosDB/FrontDoor/AD）
│       │   ├── Pulumi.yaml
│       │   └── requirements.txt
│       └── gcp/
│           ├── __main__.py           ← すべての GCP リソース（GCS/CloudRun/Firestore/CDN）
│           ├── Pulumi.yaml
│           └── requirements.txt
│
├── services/
│   ├── api/                          ← FastAPI バックエンド
│   │   ├── app/
│   │   │   ├── main.py               ← FastAPI アプリ、CORS、Mangum ハンドラー
│   │   │   ├── config.py             ← Pydantic Settings（環境変数をロード）
│   │   │   ├── models.py             ← Pydantic モデル（Post、Profile など）
│   │   │   ├── auth.py               ← JWT 認証ミドルウェア
│   │   │   ├── jwt_verifier.py       ← Cognito / Azure AD / Firebase JWT 検証
│   │   │   ├── backends/
│   │   │   │   ├── base.py           ← BackendBase 抽象クラス
│   │   │   │   ├── aws_backend.py    ← DynamoDB + S3 実装
│   │   │   │   ├── azure_backend.py  ← Cosmos DB + Blob Storage 実装
│   │   │   │   ├── gcp_backend.py    ← Firestore + Cloud Storage 実装
│   │   │   │   └── local_backend.py  ← DynamoDB Local + MinIO 実装
│   │   │   └── routes/
│   │   │       ├── posts.py          ← POST/GET/PUT/DELETE /posts
│   │   │       ├── profile.py        ← GET/PUT /profile/{userId}
│   │   │       └── uploads.py        ← POST /uploads/presigned-url
│   │   ├── index.py                  ← Lambda ハンドラー（Mangum ラッパー）
│   │   ├── function_app.py           ← Azure Functions ハンドラー
│   │   ├── function.py               ← GCP Cloud Functions ハンドラー
│   │   ├── requirements.txt          ← 共有依存関係（fastapi、mangum、pydantic...）
│   │   ├── requirements-aws.txt      ← AWS 固有（boto3 など）
│   │   ├── requirements-azure.txt    ← Azure 固有（azure-cosmos など）
│   │   ├── requirements-gcp.txt      ← GCP 固有（google-cloud-firestore など）
│   │   └── requirements-layer.txt    ← Lambda Layer 依存関係（boto3 を除く）
│   │
│   ├── frontend_react/               ← React フロントエンド（SNS アプリ — AWS）
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── api/                  ← Axios クライアント
│   │   │   ├── components/           ← UI コンポーネント
│   │   │   └── hooks/                ← カスタムフック
│   │   ├── vite.config.ts            ← base: "/sns/" を設定
│   │   └── package.json
│   │
│   └── frontend_web/                 ← Python FastAPI フロントエンド（SNS アプリ — Azure + GCP）
│
├── static-site/                      ← ランディングページ（平文 HTML、SPA ではない）
│   ├── index.html                    ← 共有ランディング（クラウド/ローカル環境を自動検出）
│   ├── aws/  azure/  gcp/            ← クラウドテーマ付きランディングバリアント
│   └── nginx.conf
│
├── scripts/                          ← デプロイ / テストシェルスクリプト
├── docs/
│   ├── AI_AGENT_GUIDE.md             ← ★ AI エージェント エントリーポイント
│   ├── AI_AGENT_00_CRITICAL_RULES.md ← 最初に読む
│   ├── AI_AGENT_01_CONTEXT.md        ← このファイル
│   └── archive/                      ← アーカイブ / スーパーセッドされたドキュメント
│
├── docker-compose.yml                ← api + dynamodb-local + minio
├── Makefile
└── README.md
```

---

## クイックファイルリファレンス

| やりたいこと                 | 編集するファイル（群）                            |
| ---------------------------- | ------------------------------------------------- |
| API エンドポイントを追加     | `services/api/app/routes/*.py`                    |
| DB ロジックを変更（AWS）     | `services/api/app/backends/aws_backend.py`        |
| DB ロジックを変更（Azure）   | `services/api/app/backends/azure_backend.py`      |
| DB ロジックを変更（GCP）     | `services/api/app/backends/gcp_backend.py`        |
| 環境変数を追加               | `services/api/app/config.py` + `Pulumi.*.yaml`    |
| AWS インフラを変更           | `infrastructure/pulumi/aws/__main__.py`           |
| Azure インフラを変更         | `infrastructure/pulumi/azure/__main__.py`         |
| GCP インフラを変更           | `infrastructure/pulumi/gcp/__main__.py`           |
| CI/CD ワークフロー編集       | `.github/workflows/*.yml`（ワークスペースルート） |
| React フロントエンド UI 編集 | `services/frontend_react/src/`                    |
| Python フロントエンド編集    | `services/frontend_web/`                          |
| ランディングページ編集       | `static-site/`                                    |

---

## 開発環境

### ホストマシン

- **アーキテクチャ: ARM（Apple Silicon M シリーズ Mac）**
- 開発環境: VS Code Dev Container（`.devcontainer/`）

### Dev Container

| コンポーネント | 詳細                                             |
| -------------- | ------------------------------------------------ |
| ベースイメージ | `mcr.microsoft.com/devcontainers/base:ubuntu`    |
| Python         | 3.13                                             |
| Node.js        | 24                                               |
| Docker         | Docker-in-Docker v2                              |
| クラウド CLI   | AWS CLI、Azure CLI、Google Cloud SDK、GitHub CLI |
| IaC            | Pulumi CLI                                       |
| 公開ポート     | 3000（フロントエンド開発）、8000（API）          |

### ARM ビルド警告

> ⚠️ dev container は `linux/aarch64`。すべてのクラウドランタイムは `linux/amd64` で実行される。
> デプロイ用に Python パッケージは常にクロスコンパイルする：
>
> ```bash
> docker run --rm --platform linux/amd64 \
>   -v /tmp/deploy:/out python:3.13-slim \
>   bash -c "pip install --no-cache-dir --target /out -r requirements.txt -q"
> ```
>
> 詳細は [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md) のルール 2 を参照。

### ローカル開発

```bash
cd /workspaces/multicloud-auto-deploy
docker compose up -d          # API (uvicorn) + DynamoDB Local + MinIO + frontend_web
curl http://localhost:8000/health
```

### クラウド認証情報（ホストから自動マウント）

- `~/.aws` → AWS CLI 認証情報
- `~/.azure` → Azure CLI 認証情報
- `~/.config/gcloud` → Google Cloud SDK 認証情報

---

## ブランチ戦略

```
feature/xxx  →  develop  →  push  →  staging 自動デプロイ
                    ↓
                  main   →  push  →  本番環境 自動デプロイ  ⚠️ 即座に
```

---

## 次のセクション

→ [02 — アーキテクチャ](AI_AGENT_02_ARCHITECTURE_JA.md)
