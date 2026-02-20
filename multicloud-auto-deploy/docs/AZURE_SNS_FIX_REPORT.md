# Azure Simple-SNS 修正レポート

## 概要

Azure 環境における `simple-sns` フロントエンドウェブアプリ (Azure Functions Python v2) が
503/404 エラーを返していた問題を特定・修正し、完全動作する状態に復元しました。

---

## 問題の状況

| エンドポイント | 修正前 | 修正後 |
|---|---|---|
| `GET /sns/health` | 503 Service Unavailable | 200 `{"status":"ok"}` |
| `GET /sns/` | 503 Service Unavailable | 200 HTML ホームページ |
| `GET /sns/login` | 503 Service Unavailable | 200 HTML ログインページ |
| `GET /sns/static/app.css` | 503 Service Unavailable | 200 CSS ファイル |
| `POST /api/posts` (未認証) | 正常 | 401 (認証ガード動作) |

---

## 特定された問題と修正内容

### 問題 1: `host.json` の JSON 構文エラー (根本原因・503 の直接原因)

**ファイル**: `services/frontend_web/host.json`

```json
// 修正前 (❌ 無効なJSON)
{
  "version": "2.0",
  "extensions": {"http": {"routePrefix": ""}}
}
}  // ← 余分な閉じ括弧

// 修正後 (✅ 有効なJSON)
{
  "version": "2.0",
  "extensions": {"http": {"routePrefix": ""}},
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

**影響**: 全エンドポイントが 503 を返していた

---

### 問題 2: Function App デプロイ方式の不一致 (Functions が空)

**原因**: `WEBSITE_RUN_FROM_PACKAGE` に外部 SAS URL を設定していた。Dynamic Consumption (Y1) Linux
プランでは、外部 URL から ZIP をマウントした場合、Python v2 プログラミングモデルの関数が登録されない。

**調査過程**:
- `admin/functions` → `[]` (空)
- `admin/host/status` → `state: Running` (ホストは正常)
- Application Insights → トレースなし (Python ワーカーが関数を検出できていない)

**修正**: `WEBSITE_RUN_FROM_PACKAGE` 設定を削除し、`az functionapp deployment source config-zip`
(Kudu ZIP デプロイ) に切り替え。コードが `/home/site/wwwroot/` に展開されることで、
Python ワーカーが `function_app.py` を正常に読み込めるようになった。

```bash
# 修正前 (❌ 外部 URL　→ Functions 未登録)
WEBSITE_RUN_FROM_PACKAGE = https://mcadfuncd45ihd.blob.core.windows.net/...

# 修正後 (✅ config-zip デプロイ)
az functionapp deployment source config-zip \
  --resource-group "multicloud-auto-deploy-staging-rg" \
  --name "multicloud-auto-deploy-staging-frontend-web" \
  --src frontend-web-x86.zip
# → WEBSITE_RUN_FROM_PACKAGE が自動設定 (Kudu 管理の URL)
```

---

### 問題 3: CPU アーキテクチャ不一致 (pydantic_core インポートエラー)

**エラー**: `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`

**原因**: 開発環境が `aarch64` (ARM64) なのに対し、Azure Functions は `x86_64` (AMD64) で動作。
ローカルで `pip install --target` すると `aarch64` 向けのコンパイル済み `.so` がインストールされ、
Azure で実行すると CPU アーキテクチャ不一致でロードに失敗する。

**修正**: Docker の `linux/amd64` プラットフォームを指定してパッケージをビルド。

```bash
# ❌ ローカルビルド (aarch64 → Azure で動作しない)
pip3 install pydantic==2.9.0 fastapi==0.115.0 --target build/

# ✅ x86_64 向けビルド (Docker 使用)
docker run --rm \
  --platform linux/amd64 \
  -v "$(pwd):/workspace" \
  python:3.12-slim \
  pip install pydantic==2.9.0 fastapi==0.115.0 --target /workspace/build-x86

# 作成した zip をデプロイ
az functionapp deployment source config-zip \
  --src frontend-web-x86.zip ...
```

---

### 問題 4: 静的ファイル・テンプレートの相対パス参照

**ファイル**: `services/frontend_web/app/main.py`, `app/routers/views.py`, `app/routers/auth.py`

Azure Functions では CWD が保証されないため、相対パスが機能しない。

```python
# ❌ 修正前 (相対パス)
StaticFiles(directory="app/static")
Jinja2Templates(directory="app/templates")

# ✅ 修正後 (__file__ 基準の絶対パス)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
StaticFiles(directory=os.path.join(_APP_DIR, "static"))

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
Jinja2Templates(directory=_TEMPLATES_DIR)
```

---

### 問題 5: `function_app.py` の同期ハンドラ

**原因**: `AsgiMiddleware.handle()` (同期) を使用していた。

**修正**: 手動 ASGI 変換 (API Function App と同じパターン) に切り替え。

```python
# ✅ 修正後 (手動 ASGI + エラー診断機能)
_IMPORT_ERROR: str | None = None
fastapi_app = None
try:
    from app.main import app as fastapi_app
except Exception as _e:
    _IMPORT_ERROR = traceback.format_exc()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="Web")
@app.route(route="{*path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    if fastapi_app is None:
        return func.HttpResponse(
            body=f"<h1>Import Error</h1><pre>{_IMPORT_ERROR}</pre>",
            status_code=503
        )
    # ... 手動 ASGI 変換
```

---

## デプロイ手順 (再現可能)

```bash
cd multicloud-auto-deploy/services/frontend_web

# 1. x86_64 向けパッケージをビルド
docker run --rm \
  --platform linux/amd64 \
  -v "$(pwd):/workspace" \
  python:3.12-slim \
  bash -c "pip install \
    fastapi==0.115.0 pydantic==2.9.0 pydantic-settings==2.5.2 \
    jinja2==3.1.4 python-multipart==0.0.9 azure-functions==1.20.0 \
    requests==2.32.3 itsdangerous==2.2.0 \
    --target /workspace/build-x86 --quiet"

# 2. ソースコードを追加
cp -r app function_app.py host.json requirements.txt build-x86/
touch build-x86/app/__init__.py  # namespace package 対応

# 3. ZIP 作成
cd build-x86 && zip -r ../frontend-web-x86.zip . \
  --exclude "*.pyc" --exclude "__pycache__/*"
cd ..

# 4. デプロイ
az functionapp deployment source config-zip \
  --resource-group "multicloud-auto-deploy-staging-rg" \
  --name "multicloud-auto-deploy-staging-frontend-web" \
  --src frontend-web-x86.zip

# 5. 動作確認
./scripts/test-sns-azure.sh
```

---

## テスト結果

```
============================================================
  Azure Simple-SNS — End-to-End Test Suite
============================================================
  Front Door  : https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net
  Frontend-web: https://multicloud-auto-deploy-staging-frontend-web.azurewebsites.net
  API Function: https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net

Section 1 — Frontend-web Function App (direct)
  ✅  Frontend-web /sns/health returns 200  [HTTP 200]
  ✅    .status == "ok" (FastAPI running)
  ✅  Frontend-web /sns/ returns 200 (HTML)  [HTTP 200]
  ✅    SNS page Content-Type is text/html
  ✅  Frontend-web /sns/login page returns 200 (HTML)  [HTTP 200]
  ✅  Frontend-web /sns/static/app.css returns 200  [HTTP 200]

Section 2 — API Function App (direct)
  ✅  API /api/health returns 200  [HTTP 200]
  ✅    .provider=azure
  ✅  API GET /api/posts returns 200 (unauthenticated)  [HTTP 200]
  ✅    .items array present (16 posts)

Section 3 — Front Door CDN routing
  ✅  Front Door /sns/health via CDN returns 200  [HTTP 200]
  ✅  Front Door /sns/ returns 200 (HTML)  [HTTP 200]
  ✅  Front Door /sns/login returns 200 (HTML)  [HTTP 200]
  ✅  Front Door /sns/static/app.css returns 200 (static file)  [HTTP 200]

Section 4 — Auth guard (unauthenticated = 401)
  ✅  POST /api/posts without token returns 401  [HTTP 401]
  ✅  POST /api/uploads/presigned-urls without token returns 401  [HTTP 401]

Test Results: PASS=16 FAIL=0 SKIP=7 (認証テストはトークン必要)
✅ All tests passed!
```

---

## アーキテクチャ概要

```
ブラウザ
  │
  ▼
Azure Front Door (mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net)
  ├── /sns/*  → frontend-web Function App (Consumption Linux, Python 3.12)
  │               FastAPI SSR → テンプレート (Jinja2) + API 呼び出し
  │               AUTH_DISABLED=true (Azure AD 認証はフロントエンド描画のみ)
  │
  └── /*      → Azure Blob Static Web (index.html)

frontend-web → API Function App (Flex Consumption, Python 3.12)
                 (server-side fetch: /api/posts, /api/profile など)
                 Cosmos DB (messages/messages コンテナ, docType="post")
                 Azure Blob Storage (画像アップロード SAS URL 生成)
```

---

## 注意事項 (今後の運用)

1. **デプロイは必ず `linux/amd64` Docker ビルドで**: 開発環境が ARM64 の場合、
   ローカルビルドした zip は Azure で pydantic_core エラーになる。

2. **config-zip を使用すること**: `WEBSITE_RUN_FROM_PACKAGE` に外部 SAS URL を
   直接設定する方法は Dynamic Consumption Linux では Python v2 モデルで関数が登録されない。

3. **Cold Start に注意**: Consumption プランのため、アイドル後の初回リクエストに
   数十秒かかる場合がある。Front Door のヘルスプローブが `/sns/health` を定期確認。
