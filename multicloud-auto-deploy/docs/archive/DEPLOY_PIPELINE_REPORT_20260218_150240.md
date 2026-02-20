# デプロイパイプライン実行レポート

**実行日時**: 20260218 15:02:40  
**総合結果**: ❌ 一部テストFAIL  
**担当者**: 自動実行 (deploy-pipeline.sh)

---

## パイプライン概要

```
local → develop (push) → [GitHub Actions staging deploy] → staging test
       → main (merge+push) → [GitHub Actions production deploy] → production test
```

---

## 各ステップ結果

| ステップ | 内容 | 結果 |
|---------|------|------|
| STEP 1 | ローカルテスト | PASS: 43 / FAIL: 1 / WARN+SKIP: 1 |
| STEP 2 | develop ブランチ push | commit: 68a1ca5 |
| STEP 3 | GitHub Actions (staging) 待機 | AWS: success (run_id: 22143624953, sha: 68a1ca5) |
| STEP 4 | staging 環境テスト | PASS: 14 / FAIL: 4 / WARN+SKIP: 3 |
| STEP 5 | main ブランチ merge + push | commit: 8bc2770 |
| STEP 6 | GitHub Actions (production) 待機 | AWS: success (run_id: 22144555848, sha: 8bc2770) |
| STEP 7 | production 環境テスト | PASS: 13 / FAIL: 4 / WARN+SKIP: 4 |

---

## GitHub Actions ステータス

| ワークフロー | ブランチ | ステータス |
|------------|--------|---------|
| deploy-aws.yml | develop (staging) | success (run_id: 22143624953, sha: 68a1ca5) |
| deploy-aws.yml | main (production) | success (run_id: 22144555848, sha: 8bc2770) |
| deploy-gcp.yml | develop (staging) | failure (run_id: 22143629706, sha: 68a1ca5) |
| deploy-azure.yml | develop (staging) | success (run_id: 22143635262, sha: 68a1ca5) |

---

## エンドポイント (staging)

| クラウド | API | Frontend CDN |
|---------|-----|-------------|
| AWS | https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com | https://d1tf3uumcm4bo1.cloudfront.net |
| Azure | https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger | https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net |
| GCP | https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app | http://34.117.111.182 |

---

## ローカルテスト詳細

```
[0;32m  ✅ PASS[0m python3 が利用可能: /usr/local/python/current/bin/python3
[0;32m  ✅ PASS[0m pip3 が利用可能: /usr/local/python/current/bin/pip3
[0;32m  ✅ PASS[0m docker が利用可能: /usr/bin/docker
[0;32m  ✅ PASS[0m curl が利用可能: /usr/bin/curl
[0;32m  ✅ PASS[0m git が利用可能: /usr/local/bin/git
[0;32m  ✅ PASS[0m node が利用可能: /usr/local/share/nvm/versions/node/v22.22.0/bin/node
[0;32m  ✅ PASS[0m npm が利用可能: /usr/local/share/nvm/versions/node/v22.22.0/bin/npm
[0;32m  ✅ PASS[0m docker compose が利用可能: 2.40.3
[0;32m  ✅ PASS[0m docker-compose.yml が存在: /workspaces/ashnova/multicloud-auto-deploy/docker-compose.yml
[0;32m  ✅ PASS[0m API Dockerfile が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/Dockerfile
[0;32m  ✅ PASS[0m API requirements.txt が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/requirements.txt
[0;32m  ✅ PASS[0m API requirements-dev.txt が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/requirements-dev.txt
[0;32m  ✅ PASS[0m API app/main.py が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/app/main.py
[0;32m  ✅ PASS[0m API app/config.py が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/app/config.py
[0;32m  ✅ PASS[0m pytest.ini が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/pytest.ini
[0;32m  ✅ PASS[0m tests/conftest.py が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/tests/conftest.py
[0;32m  ✅ PASS[0m tests/test_backends_integration.py が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/tests/test_backends_integration.py
[0;32m  ✅ PASS[0m tests/test_api_endpoints.py が存在: /workspaces/ashnova/multicloud-auto-deploy/services/api/tests/test_api_endpoints.py
[0;36m  ℹ  [0m Python バージョン: 3.12.12
[0;32m  ✅ PASS[0m Python >= 3.11 ✓ (3.12.12)
[0;32m  ✅ PASS[0m fastapi インストール済み (0.115.0)
[0;32m  ✅ PASS[0m pydantic インストール済み (2.9.0)
[0;32m  ✅ PASS[0m uvicorn インストール済み (0.32.0)
[0;32m  ✅ PASS[0m httpx インストール済み (0.25.0)
[0;32m  ✅ PASS[0m pytest インストール済み (7.4.3)
[0;32m  ✅ PASS[0m minio インストール済み (7.2.9)
[0;32m  ✅ PASS[0m boto3 インストール済み (1.35.0)
[0;36m  ℹ  [0m uvicorn を起動中 (port=18765)...
[0;32m  ✅ PASS[0m uvicorn 起動成功 (PID=96801, port=18765)
[0;32m  ✅ PASS[0m GET /         (ルート) → HTTP 200
[0;32m  ✅ PASS[0m GET /         レスポンス形式 → レスポンスに 'status' キーを確認
[0;32m  ✅ PASS[0m GET /health   (ヘルスチェック) → HTTP 200
[0;32m  ✅ PASS[0m GET /docs     (Swagger UI) → HTTP 200
[0;32m  ✅ PASS[0m GET /openapi.json (OpenAPI スキーマ) → HTTP 200
[0;32m  ✅ PASS[0m GET /posts    (投稿一覧) → HTTP 200
[0;32m  ✅ PASS[0m GET /posts    レスポンス形式 → レスポンスに 'items' キーを確認
[0;32m  ✅ PASS[0m GET /api/messages/ (旧互換エンドポイント) → HTTP 200
[0;36m  ℹ  [0m CRUD フロー: 投稿作成 → 一覧確認
[0;32m  ✅ PASS[0m POST /posts → HTTP 201
[0;36m  ℹ  [0m 一覧件数: 4 件
[0;32m  ✅ PASS[0m GET /posts → 4 件取得
[0;36m  ℹ  [0m pytest 実行中 (ローカルバックエンド単体テスト)...
[0;32m  ✅ PASS[0m pytest: 2 passed
[0;32m  ✅ PASS[0m docker-compose.yml の構文が正常
[0;36m  ℹ  [0m 定義サービス: minio api frontend_reflex 
[0;32m  ✅ PASS[0m サービス 'api' が定義されています
[0;32m  ✅ PASS[0m サービス 'minio' が定義されています
[0;36m  ℹ  [0m docker compose build api を実行中（キャッシュ利用）...
[0;32m  ✅ PASS[0m API Docker イメージのビルド成功
[0;32m✅ PASS[0m: 42
[0;31m❌ FAIL[0m: 0
[1;33m⏭ SKIP[0m: 0
[0;36m  ℹ  [0m テスト用 uvicorn プロセスを停止 (PID=96801)
```

---

## Staging テスト詳細

```
[0;36m  ℹ  [0m エンドポイント一覧:
[0;36m  ℹ  [0m API: https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
[0;32m  ✅ PASS[0m [AWS] GET /       (ルート) → HTTP 200
[0;32m  ✅ PASS[0m [AWS] GET /       レスポンス形式(status) → HTTP 200, 'status' キー確認
[0;32m  ✅ PASS[0m [AWS] GET /health (ヘルスチェック) → HTTP 200
[0;36m  ℹ  [0m [AWS] CRUD テスト: 投稿作成 → 一覧取得
[1;33m  ⚠️  WARN[0m [AWS] POST /posts → HTTP 401 (認証が必要: AUTH_DISABLED=false)
[0;31m  ❌ FAIL[0m [AWS] GET /posts → HTTP 500
[0;32m  ✅ PASS[0m [AWS] フロントエンド CDN → HTTP 200, HTML/SPA 確認
[0;36m  ℹ  [0m API: https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger
[0;32m  ✅ PASS[0m [Azure] GET /       (ルート) → HTTP 200
[0;32m  ✅ PASS[0m [Azure] GET /health (ヘルスチェック) → HTTP 200
[0;36m  ℹ  [0m [Azure] CRUD テスト: 投稿作成 → 一覧取得
[0;31m  ❌ FAIL[0m [Azure] POST /posts → HTTP 404
[0;31m  ❌ FAIL[0m [Azure] GET /posts → HTTP 404
[0;32m  ✅ PASS[0m [Azure] フロントエンド CDN → HTTP 200, HTML/SPA 確認
[0;36m  ℹ  [0m API: https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app
[0;32m  ✅ PASS[0m [GCP] GET /       (ルート) → HTTP 200
[0;32m  ✅ PASS[0m [GCP] GET /       レスポンス形式(status) → HTTP 200, 'status' キー確認
[0;32m  ✅ PASS[0m [GCP] GET /health (ヘルスチェック) → HTTP 200
[0;36m  ℹ  [0m [GCP] CRUD テスト: 投稿作成 → 一覧取得
[0;32m  ✅ PASS[0m [GCP] POST /posts → HTTP 201
[0;32m  ✅ PASS[0m [GCP] GET /posts → HTTP 200, 5 件
[0;32m  ✅ PASS[0m [GCP] フロントエンド CDN → HTTP 200, HTML/SPA 確認
[0;32m✅ PASS[0m: 13
[0;31m❌ FAIL[0m: 3
[1;33m⚠️  WARN[0m: 1
[1;33m⏭ SKIP[0m: 0
```

---

## Production テスト詳細

```
[0;36m  ℹ  [0m エンドポイント一覧:
[0;36m  ℹ  [0m API: https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com
[0;32m  ✅ PASS[0m [AWS] GET /       (ルート) → HTTP 200
[0;32m  ✅ PASS[0m [AWS] GET /       レスポンス形式(status) → HTTP 200, 'status' キー確認
[0;32m  ✅ PASS[0m [AWS] GET /health (ヘルスチェック) → HTTP 200
[0;36m  ℹ  [0m [AWS] CRUD テスト: 投稿作成 → 一覧取得
[1;33m  ⚠️  WARN[0m [AWS] POST /posts → HTTP 401 (認証が必要: AUTH_DISABLED=false)
[0;32m  ✅ PASS[0m [AWS] GET /posts → HTTP 200, 3 件
[0;32m  ✅ PASS[0m [AWS] フロントエンド CDN → HTTP 200, HTML/SPA 確認
[0;36m  ℹ  [0m API: https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api/HttpTrigger
[0;32m  ✅ PASS[0m [Azure] GET /       (ルート) → HTTP 200
[0;32m  ✅ PASS[0m [Azure] GET /health (ヘルスチェック) → HTTP 200
[0;36m  ℹ  [0m [Azure] CRUD テスト: 投稿作成 → 一覧取得
[0;31m  ❌ FAIL[0m [Azure] POST /posts → HTTP 404
[0;31m  ❌ FAIL[0m [Azure] GET /posts → HTTP 404
[0;32m  ✅ PASS[0m [Azure] フロントエンド CDN → HTTP 200, HTML/SPA 確認
[0;36m  ℹ  [0m API: https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app
[0;32m  ✅ PASS[0m [GCP] GET /       (ルート) → HTTP 200
[0;32m  ✅ PASS[0m [GCP] GET /       レスポンス形式(status) → HTTP 200, 'status' キー確認
[0;32m  ✅ PASS[0m [GCP] GET /health (ヘルスチェック) → HTTP 200
[0;36m  ℹ  [0m [GCP] CRUD テスト: 投稿作成 → 一覧取得
[1;33m  ⚠️  WARN[0m [GCP] POST /posts → HTTP 401 (認証が必要: AUTH_DISABLED=false)
[0;31m  ❌ FAIL[0m [GCP] GET /posts → HTTP 500
[0;32m  ✅ PASS[0m [GCP] フロントエンド CDN → HTTP 200, HTML/SPA 確認
[0;32m✅ PASS[0m: 12
[0;31m❌ FAIL[0m: 3
[1;33m⚠️  WARN[0m: 2
[1;33m⏭ SKIP[0m: 0
```

---

## git ログ (直近5件)

```
8bc2770 chore: Merge develop -> main for production deploy (2026-02-18)
68a1ca5 feat(ci): Add deploy pipeline scripts + fix LocalBackend SQLite
952170a docs(test): Complete GCP integration testing - all 3 providers 6/6 success
59ba17b docs(test): Update GCP test results and analysis
d612121 fix(aws): Add missing environment variables to Lambda function
```

---

*このレポートは scripts/generate-pipeline-report.sh により自動生成されました。*
