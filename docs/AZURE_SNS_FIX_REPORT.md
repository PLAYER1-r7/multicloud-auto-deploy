# Azure Simple-SNS 修正レポート

## 概要

Azure 環境における `simple-sns` フロントエンドウェブアプリ (Azure Functions Python v2) が
503/404 エラーを返していた問題を特定・修正し、完全動作する状態に復元しました。

---

## 問題の状況

| エンドポイント             | 修正前                  | 修正後                  |
| -------------------------- | ----------------------- | ----------------------- |
| `GET /sns/health`          | 503 Service Unavailable | 200 `{"status":"ok"}`   |
| `GET /sns/`                | 503 Service Unavailable | 200 HTML ホームページ   |
| `GET /sns/login`           | 503 Service Unavailable | 200 HTML ログインページ |
| `GET /sns/static/app.css`  | 503 Service Unavailable | 200 CSS ファイル        |
| `POST /api/posts` (未認証) | 正常                    | 401 (認証ガード動作)    |

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

---

## Issue 2: AFD 経由 `/sns/*` 間欠的 502 エラー（調査中）

> **発生日**: 2026-02-21  
> **対象**: `www.azure.ashnova.jp/sns/*`（Production）  
> **状態**: 🔴 **未解決** — 継続調査中

### 症状

- `www.azure.ashnova.jp/sns/health` への AFD 経由アクセスが **約 50% の確率で HTTP 502** を返す
- Function App 直接アクセス（`multicloud-auto-deploy-production-frontend-web.azurewebsites.net`）は **100% 成功**
- 502 应答は即時返却（**0.08〜0.36 秒**）→ AFD がオリジンへの接続を試みずに返している

```
AFD 経由テスト結果（典型例）:
  1: 200 (0.27s)
  2: 502 (0.10s)  ← 即時
  3: 200 (0.26s)
  4: 502 (0.10s)  ← 即時
…
OK=10 NG=10 / 20
```

### 判明した事実

| 項目                       | 内容                                                           |
| -------------------------- | -------------------------------------------------------------- |
| Function App 直接          | 6/6 = 100% HTTP 200                                            |
| AFD 経由                   | 約 50% HTTP 502（即時返却）                                    |
| 502 のレスポンスボディ     | AFD 標準エラー HTML（249 bytes）= AFD 自身が生成               |
| `x-cache` ヘッダー         | `CONFIG_NOCACHE`（キャッシュではない）                         |
| AFD Edge Node              | 同一ノード `15bbd5d46d5` から 200 と 502 両方が返る            |
| AFD の DNS                 | 2 つの IP: `13.107.246.46`、`13.107.213.46` — 両方で同パターン |
| Function App の HTTP/2     | `http20Enabled: true`（無効化しても改善なし）                  |
| Function App の SKU        | Dynamic Consumption (Y1)、`alwaysOn: false`                    |
| Function App の OS/Runtime | Linux / Python 3.12                                            |

### 試みた対策と結果

| 対策                                                  | 結果               |
| ----------------------------------------------------- | ------------------ |
| AFD `originResponseTimeoutSeconds` 30s → 60s          | 502 継続           |
| AFD health probe 間隔 100s → 30s                      | 502 継続           |
| AFD `sampleSize` 4→2、`successfulSamplesRequired` 3→1 | 502 継続           |
| Function App 再起動                                   | 502 継続           |
| SNS Route 無効化→有効化                               | 502 継続           |
| `http20Enabled` false（HTTP/2 無効化）                | 502 継続           |
| `WEBSITE_KEEPALIVE_TIMEOUT=30` 設定                   | 502 継続（確認中） |
| `pulumi up`（origin group 再設定）                    | 502 継続           |

### 根本原因の仮説

**AFD Standard の stale TCP 接続プール問題**

```
AFD Edge Node
  ├── Connection Pool
  │     ├── Conn A  → Function App インスタンス X（稼働中）→ 200 ✅
  │     └── Conn B  → Function App インスタンス Y（再サイクル済）→ TCP 切断 → 502 ❌
  │
  └── 新規接続は即成功、stale 接続は即 502
```

Dynamic Consumption では Function App インスタンスが定期的に再サイクルされる。
AFD はその際の TCP 接続断を検知できず、stale 接続プールに残り続ける。
次のリクエストが stale 接続に割り当てられると即時 502 になる。

**証拠**:

- 502 が即時返却（AFD→オリジン接続なし）
- Function App 直接は 100% 成功（インスタンス自体は正常）
- パターンが規則的（再サイクル後は 1 回 502、その後 200 に戻る）

### 現在の設定状態（2026-02-21）

```bash
# Function App
WEBSITE_KEEPALIVE_TIMEOUT=30    # 追加済み
WEBSITE_WARMUP_PATH=/sns/health  # 追加済み
http20Enabled=false              # 無効化済み

# AFD Origin Group
probeIntervalInSeconds=30        # 30s（Pulumi 適用済み）
sampleSize=2                     # 緩和済み（4→2）
successfulSamplesRequired=1      # 緩和済み（3→1）

# AFD Profile
originResponseTimeoutSeconds=60  # 延長済み（30s→60s）
```

### 次の調査方針（別チャットで継続）

1. **`WEBSITE_KEEPALIVE_TIMEOUT` の効果確認**: 30 分以上継続テストして改善するか確認
2. **Azure Support / Known Issues 調査**: AFD Standard + Dynamic Consumption の既知の stale connection 問題
3. **`WEBSITE_IDLE_TIMEOUT_IN_MINUTES` 調整**: インスタンス再サイクル頻度を変更
4. **AFD ルールセットで `Connection: close` ヘッダー付与**: TCP 接続の再利用を強制的に防ぐ
5. **Premium SKU への移行検討**: AFD Standard の接続プール管理が改善している可能性
6. **Flex Consumption への移行**: `alwaysOn` 相当の設定が可能で、インスタンス再サイクルを抑制

### 関連コミット

| コミット  | 内容                                                                           |
| --------- | ------------------------------------------------------------------------------ |
| `9ed48d6` | CI/CD バグ修正（SNS dist が `$web` を上書きする問題）                          |
| `27a44af` | AFD タイムアウト延長・ウォームアップ設定・ランディングページ修正               |
| `(最新)`  | `WEBSITE_KEEPALIVE_TIMEOUT=30`、`http20Enabled=false`、AFD origin group 再設定 |
