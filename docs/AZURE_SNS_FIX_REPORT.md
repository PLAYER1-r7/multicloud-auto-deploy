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

優先度順。上から試す。

1. **`WEBSITE_KEEPALIVE_TIMEOUT` の長期効果確認**  
   設定直後は効果不明。30 分以上継続テストして改善するか確認。

   ```bash
   OK=0; NG=0
   for i in $(seq 1 30); do
     CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://www.azure.ashnova.jp/sns/health")
     if [ "$CODE" = "200" ]; then ((OK++)); else ((NG++)); echo "FAIL $i: $CODE"; fi
     sleep 60  # 1分間隔で30回 = 30分
   done
   echo "OK=$OK NG=$NG / 30"
   ```

2. **AFD ルールセットで `Connection: close` ヘッダー付与**（最有望）  
   AFD→オリジン間の TCP 接続を Keep-Alive させず毎回新規接続させる。
   → デプロイが必要（下記「デプロイが必要なサービス」参照）

3. **`WEBSITE_IDLE_TIMEOUT_IN_MINUTES` 調整**  
   Function App インスタンスのアイドルタイムアウトを延ばしてインスタンス再サイクルを抑制。

   ```bash
   az functionapp config appsettings set \
     --name multicloud-auto-deploy-production-frontend-web \
     --resource-group multicloud-auto-deploy-production-rg \
     --settings "WEBSITE_IDLE_TIMEOUT_IN_MINUTES=60"
   ```

4. **Flex Consumption への移行**  
   Dynamic Consumption (Y1) の代わりに Flex Consumption を使うことで
   `instanceMemoryMB` / `maximumInstanceCount` が設定可能になり、インスタンスが安定する。
   Pulumi の `azure.web.WebApp` の `kind` + `serverFarmId` を変更する。

5. **AFD Premium SKU への移行検討**  
   AFD Standard の接続プール管理に問題がある可能性。
   Premium では Private Link 経由の接続が利用可能で挙動が異なる。
   ただしコストが大幅増加するため最終手段。

6. **Azure Support へのチケット起票**  
   AFD Standard + Dynamic Consumption の既知の stale connection 問題として記録がある可能性。

---

### 調査再開時のセットアップ（必要なツール）

調査中に使ったコマンドと、次回から使えるようにしておくとよいツール。

#### 1. 環境変数（毎回設定）

```bash
export RG="multicloud-auto-deploy-production-rg"
export FD="multicloud-auto-deploy-production-fd"
export EP="mcad-production-diev0w"
export OG="multicloud-auto-deploy-production-frontend-web-origin-group"
export ORIGIN="multicloud-auto-deploy-production-frontend-web-origin"
export FUNC_WEB="multicloud-auto-deploy-production-frontend-web"
export HOSTNAME="multicloud-auto-deploy-production-frontend-web.azurewebsites.net"
export AFD_URL="https://www.azure.ashnova.jp"
```

#### 2. 502 率確認スクリプト（標準テスト）

```bash
# 10回テスト（5秒間隔）
OK=0; NG=0
for i in $(seq 1 10); do
  TIMING=$(curl -s -o /dev/null -w "%{http_code}/%{time_total}" --max-time 15 "$AFD_URL/sns/health")
  CODE="${TIMING%%/*}"; TIME="${TIMING##*/}"
  if [ "$CODE" = "200" ]; then ((OK++)); else ((NG++)); fi
  echo "  $i: $CODE (${TIME}s)"
  sleep 5
done
echo "OK=$OK NG=$NG / 10"
```

#### 3. AFD IP 別テスト（どの Edge Node が問題か特定）

```bash
# AFD の IP を取得（通常 2 つ返る）
python3 -c "
import socket
ips = list(set([r[4][0] for r in socket.getaddrinfo('www.azure.ashnova.jp', 443, socket.AF_INET)]))
print('AFD IPs:', ips)
"

# 特定 IP に固定してテスト
IP1="13.107.246.46"
IP2="13.107.213.46"
for IP in $IP1 $IP2; do
  echo "=== $IP ==="
  for i in $(seq 1 5); do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
      --resolve "www.azure.ashnova.jp:443:$IP" "$AFD_URL/sns/health")
    echo "  $i: $CODE"; sleep 3
  done
done
```

#### 4. AFD 設定の現在状態確認

```bash
# Origin Group 設定
az afd origin-group show --profile-name $FD --resource-group $RG \
  --origin-group-name $OG \
  --query "{loadBalancing:loadBalancingSettings, healthProbe:healthProbeSettings}" -o json

# Origin 設定
az afd origin show --profile-name $FD --resource-group $RG \
  --origin-group-name $OG --origin-name $ORIGIN \
  --query "{hostname:hostName, enabled:enabledState, priority:priority}" -o json

# Route 設定
az afd route list --profile-name $FD --resource-group $RG --endpoint-name $EP \
  --query "[].{name:name, patterns:patternsToMatch, enabled:enabledState}" -o table
```

#### 5. Function App 設定確認

```bash
az functionapp show --name $FUNC_WEB --resource-group $RG \
  --query "{sku:sku, state:state, alwaysOn:siteConfig.alwaysOn, http20:siteConfig.http20Enabled}" -o json

az functionapp config appsettings list --name $FUNC_WEB --resource-group $RG \
  --query "[?name=='WEBSITE_KEEPALIVE_TIMEOUT' || name=='WEBSITE_WARMUP_PATH' || name=='WEBSITE_IDLE_TIMEOUT_IN_MINUTES'].{name:name,value:value}" -o table
```

#### 6. `dig` が使えない場合の DNS 確認（このコンテナでは `dig` が未インストール）

```bash
# dig の代替
python3 -c "
import socket
host = 'www.azure.ashnova.jp'
for af, name in [(socket.AF_INET, 'IPv4'), (socket.AF_INET6, 'IPv6')]:
    try:
        ips = list(set([r[4][0] for r in socket.getaddrinfo(host, 443, af)]))
        print(f'{name}: {ips}')
    except: print(f'{name}: none')
"

# dig をインストールする場合
sudo apt-get install -y dnsutils
```

---

### デプロイが必要なサービス

調査の結果、以下の Azure サービスのデプロイが有効と考えられる。

#### 優先度 HIGH: AFD ルールセット（`Connection: close` ヘッダー）

stale TCP 接続問題の根本対処。AFD→Function App 間の HTTP 接続を毎回新規作成させる。

**Pulumi コード追加箇所**: `infrastructure/pulumi/azure/__main__.py`

```python
# AFD Rule Set: Connection: close を強制してstale connection を防ぐ
frontend_web_rule_set = azure.cdn.RuleSet(
    "frontdoor-frontend-web-rule-set",
    rule_set_name=f"{project_name}-{stack}-fw-rs",
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
)

frontend_web_connection_close_rule = azure.cdn.Rule(
    "frontdoor-connection-close-rule",
    rule_name="ForceConnectionClose",
    rule_set_name=frontend_web_rule_set.name,
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    order=1,
    # 条件なし = 全リクエストに適用
    conditions=[],
    actions=[
        azure.cdn.DeliveryRuleResponseHeaderActionArgs(
            name="ModifyResponseHeader",
            parameters=azure.cdn.HeaderActionParametersArgs(
                type_name="DeliveryRuleHeaderActionParameters",
                header_action="Overwrite",
                header_name="Connection",
                value="close",
            ),
        )
    ],
)

# frontdoor_sns_route の rule_sets に追加
# frontdoor_sns_route = azure.cdn.Route(
#     ...
#     rule_sets=[azure.cdn.ResourceReferenceArgs(id=frontend_web_rule_set.id)],
#     ...
# )
```

CLI で先に試す場合:

```bash
# ルールセット作成
az afd rule-set create \
  --resource-group $RG --profile-name $FD \
  --rule-set-name fwconnclose

# ルール追加（Connection: close）
az afd rule create \
  --resource-group $RG --profile-name $FD \
  --rule-set-name fwconnclose \
  --rule-name ForceConnectionClose \
  --order 1 \
  --action-name ModifyResponseHeader \
  --header-action Overwrite \
  --header-name Connection \
  --header-value close

# SNS Route にルールセットをアタッチ
az afd route update \
  --resource-group $RG --profile-name $FD \
  --endpoint-name $EP --route-name multicloud-auto-deploy-production-sns-route \
  --rule-sets fwconnclose
```

#### 優先度 MEDIUM: Flex Consumption プランへの移行

Dynamic Consumption (Y1) → Flex Consumption に変更してインスタンス安定性を向上。
**注意**: Pulumi コードへの変更が必要。現在は手動デプロイされた Function App を参照しているため、Pulumi の外で変更する必要がある可能性がある。

```bash
# 現在のプランを確認
az functionapp show --name $FUNC_WEB --resource-group $RG \
  --query "{planName:serverFarmId, sku:sku}" -o json

# Flex Consumption プランを作成（Japan East）
az functionapp plan create \
  --resource-group $RG \
  --name multicloud-auto-deploy-production-flex-plan \
  --location japaneast \
  --sku FC1 \
  --is-linux true

# Function App を新プランに移行
az functionapp update \
  --name $FUNC_WEB \
  --resource-group $RG \
  --plan multicloud-auto-deploy-production-flex-plan
```

### 関連コミット

| コミット  | 内容                                                                           |
| --------- | ------------------------------------------------------------------------------ |
| `9ed48d6` | CI/CD バグ修正（SNS dist が `$web` を上書きする問題）                          |
| `27a44af` | AFD タイムアウト延長・ウォームアップ設定・ランディングページ修正               |
| `(最新)`  | `WEBSITE_KEEPALIVE_TIMEOUT=30`、`http20Enabled=false`、AFD origin group 再設定 |
