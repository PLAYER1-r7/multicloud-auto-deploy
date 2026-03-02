# 13 — テスト

> Part IV — Feature Reference | Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
>
> **カバレッジ**: 全テストスクリプト、pytest スイート、トークン取得、ローカルスタック設定、CI テスト統合。
> 詳細な pytest 情報: [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md)
> ステージングエンドポイントとトークン設定: [STAGING_TEST_GUIDE.md](STAGING_TEST_GUIDE.md)

---

## テストマップ

| スクリプト / ファイル                             | タイプ    | スコープ                                  | 認証必要   |
| ------------------------------------------------- | --------- | ----------------------------------------- | ---------- |
| `scripts/test-sns-local.sh`                       | E2E shell | ローカル docker-compose スタック          | 不要       |
| `scripts/test-sns-aws.sh`                         | E2E shell | AWS staging SNS アプリ                    | オプション |
| `scripts/test-sns-azure.sh`                       | E2E shell | Azure staging SNS アプリ                  | オプション |
| `scripts/test-sns-gcp.sh`                         | E2E shell | GCP staging SNS アプリ                    | オプション |
| `scripts/test-sns-all.sh`                         | E2E shell | 全3クラウド順次実行                       | オプション |
| `scripts/test-staging-all.sh`                     | E2E shell | 全3クラウド + サマリーレポート            | オプション |
| `scripts/test-e2e.sh`                             | Smoke     | 全3クラウド health + CRUD                 | オプション |
| `scripts/test-endpoints.sh`                       | Health    | クラウド別 API ヘルスチェック             | 不要       |
| `scripts/test-landing-pages.sh`                   | Health    | クラウド別静的ランディングページ          | 不要       |
| `scripts/test-api.sh`                             | API       | クラウド別 CRUD 操作                      | オプション |
| `scripts/test-auth-crud.sh`                       | Auth      | 完全な認証 + CRUD フロー                  | 必要       |
| `scripts/test-cloud-env.sh`                       | Config    | 環境変数とクラウド接続                    | 不要       |
| `scripts/test-local-env.sh`                       | Config    | ローカル docker-compose 環境チェック      | 不要       |
| `scripts/test-deployments.sh`                     | Deploy    | デプロイメントヘルスチェック              | 不要       |
| `scripts/test-cicd.sh`                            | CI/CD     | ワークフロートリガー + ステータスチェック | 不要       |
| `scripts/run-integration-tests.sh`                | pytest    | pytest ランナー (全バックエンド)          | 不要       |
| `services/api/tests/test_backends_integration.py` | pytest    | バックエンドクラス単体テスト (モック)     | 不要       |
| `services/api/tests/test_api_endpoints.py`        | pytest    | ライブ API エンドポイントテスト           | オプション |
| `services/api/tests/test_simple_sns_local.py`     | pytest    | ローカル docker-compose 統合              | 不要       |

---

## クイックコマンド

### 1 — 最速: 全クラウドヘルスチェック

```bash
./scripts/test-endpoints.sh
```

### 2 — E2E スモークテスト (全3クラウド、パブリックエンドポイント)

```bash
./scripts/test-e2e.sh
# 出力: クラウド別 pass/fail テーブル
```

### 3 — クラウド別完全 SNS テスト (パブリックエンドポイントのみ)

```bash
./scripts/test-sns-aws.sh
./scripts/test-sns-azure.sh
./scripts/test-sns-gcp.sh

# 全3つを1コマンドで:
./scripts/test-sns-all.sh
```

### 4 — 認証付き完全 SNS テスト

```bash
# まずトークンを取得 (下記「トークン取得」セクション参照)
./scripts/test-sns-aws.sh    --token "$AWS_TOKEN"
./scripts/test-sns-azure.sh  --token "$AZURE_TOKEN"
./scripts/test-sns-gcp.sh    --token "$GCP_TOKEN"

# トークン付き全3クラウド:
./scripts/test-staging-all.sh \
  --aws-token   "$AWS_TOKEN"   \
  --azure-token "$AZURE_TOKEN" \
  --gcp-token   "$GCP_TOKEN"
```

### 5 — ローカル docker-compose スタックテスト

```bash
# まずスタックを起動
docker compose up -d --build
sleep 30   # 全サービスが起動するまで待つ

./scripts/test-sns-local.sh
# または pytest:
cd services/api && pytest tests/test_simple_sns_local.py -v -m local
```

### 6 — pytest (unit + バックエンドモックテスト — ネットワーク不要)

```bash
cd services/api
# 全モックテスト
pytest tests/ -v

# 単一クラウドバックエンド
pytest tests/ -v -m aws
pytest tests/ -v -m gcp
pytest tests/ -v -m azure

# カバレッジ付き
pytest tests/ --cov=app --cov-report=html
# → htmlcov/index.html を開く
```

### 7 — デプロイ済みライブ API に対する pytest

```bash
cd services/api
export AWS_API_ENDPOINT="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
export AZURE_API_ENDPOINT="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"
export GCP_API_ENDPOINT="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
pytest tests/test_api_endpoints.py -v -m requires_network
```

---

## トークン取得

認証テストには、各クラウドの ID プロバイダーからのベアラートークンが必要です。

### AWS — Cognito アクセストークン

```bash
# ブラウザ経由: https://d1tf3uumcm4bo1.cloudfront.net/sns/ でログイン
# DevTools → Application → Local Storage → origin → access_token

# AWS CLI 経由 (メール/パスワード):
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=<email>,PASSWORD=<password> \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' --output text
```

### Azure — Azure AD id_token

```bash
# ブラウザ経由: https://staging.azure.ashnova.jp/sns/ でログイン
# DevTools → Application → Local Storage → id_token
```

### GCP — Firebase id_token

```bash
# gcloud 経由 (ログイン済みの Google アカウントを使用 — 登録ユーザーである必要あり):
gcloud auth print-identity-token

# ブラウザ経由: https://staging.gcp.ashnova.jp/sns/ でログイン
# DevTools → Application → Local Storage → id_token
```

---

## ローカル Docker Compose スタック

完全なローカル開発スタックは、リポジトリルートの `docker-compose.yml` で定義されています。

```bash
docker compose up -d --build    # 全サービス起動
docker compose ps                # 全コンテナが Up か確認
docker compose logs api -f       # API ログをストリーム
docker compose down              # 全サービス停止
```

**起動されるサービス**:

| サービス         | ポート | 説明                                          |
| ---------------- | ------ | --------------------------------------------- |
| `api`            | 8000   | FastAPI バックエンド (DynamoDB Local + MinIO) |
| `frontend_web`   | 8080   | Python/FastAPI SSR フロントエンド (Jinja2)    |
| `minio`          | 9000   | S3 互換オブジェクトストレージ                 |
| `dynamodb-local` | 8001   | DynamoDB Local                                |
| `frontend_react` | 3001   | React SPA (nginx, `/sns/`)                    |
| `static_site`    | 8090   | 静的ランディングページ (nginx proxy)          |

**docker-compose で自動設定される主要環境変数**:

```
AUTH_DISABLED=true
CLOUD_PROVIDER=local
DYNAMODB_ENDPOINT=http://dynamodb-local:8001
MINIO_ENDPOINT=http://minio:9000
```

---

## pytest マーカー

| マーカー           | アクティブ化条件                         | 説明                                      |
| ------------------ | ---------------------------------------- | ----------------------------------------- |
| `aws`              | 常時                                     | AWS バックエンド固有テスト                |
| `gcp`              | 常時                                     | GCP バックエンド固有テスト                |
| `azure`            | 常時                                     | Azure バックエンド固有テスト              |
| `local`            | 常時                                     | ローカル docker-compose 統合テスト        |
| `requires_network` | `--run-network-tests` または環境変数設定 | ライブ API エンドポイントを呼び出すテスト |
| `slow`             | `--run-slow-tests`                       | 5秒以上かかるテスト                       |

---

## ステージングエンドポイント (リファレンス)

| クラウド       | API エンドポイント                                                                                | フロントエンド URL                           |
| -------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| AWS staging    | `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com`                                     | `https://d1tf3uumcm4bo1.cloudfront.net/sns/` |
| Azure staging  | `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api` | `https://staging.azure.ashnova.jp/sns/`      |
| GCP staging    | `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app`                              | `https://staging.gcp.ashnova.jp/sns/`        |
| AWS production | `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`                                     | `https://www.aws.ashnova.jp/sns/`            |
| GCP production | (同じ Cloud Run URL)                                                                              | `https://www.gcp.ashnova.jp/sns/`            |

> 本番前に必ずステージングをテストしてください。現在のヘルス状態については [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) を参照してください。

---

## CI/CD テスト統合

テストは GitHub Actions 経由で push ごとに自動実行されます:

| ワークフロー               | トリガー                              | 実行されるテスト                         |
| -------------------------- | ------------------------------------- | ---------------------------------------- |
| `deploy-aws.yml`           | `develop` / `main` への push          | デプロイ後 `./scripts/test-endpoints.sh` |
| `deploy-azure.yml`         | `develop` / `main` への push          | デプロイ後 `./scripts/test-endpoints.sh` |
| `deploy-gcp.yml`           | `develop` / `main` への push          | デプロイ後 `./scripts/test-endpoints.sh` |
| `run-integration-tests.sh` | 手動または `test-staging-all.sh` 経由 | pytest + E2E shell                       |

---

## トラブルシューティング

| 問題                                  | 原因                            | 修正方法                                                                |
| ------------------------------------- | ------------------------------- | ----------------------------------------------------------------------- |
| `pytest: command not found`           | Python 環境が有効化されていない | `source .venv/bin/activate` または `pip install pytest`                 |
| `ImportError: No module named 'app'`  | 作業ディレクトリが間違っている  | `cd services/api` してから pytest を実行                                |
| ローカルテストで `Connection refused` | docker-compose が起動していない | `docker compose up -d && sleep 30`                                      |
| 認証テストで 401                      | トークン期限切れ                | トークンを再取得 (トークンは約1時間で期限切れ)                          |
| ステージングで 503                    | サービスコールドスタート        | 30秒待って再試行；[AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) を確認 |

---

_最終更新: 2026-02-27_
