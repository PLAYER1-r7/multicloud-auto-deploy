# Simple-SNS Fix Report (2026-02-22)

> **対象**: AWS版・Azure版 simple-sns  
> **ステータス**: ✅ AWS・Azure 両版 動作確認済み  
> **ブランチ**: `develop`

---

## 概要

2026-02-22 のセッションで AWS版・Azure版の simple-sns に存在した複数の不具合を特定・修正した。  
本レポートはその知見をまとめる。

---

## 目次

1. [AWS版 修正一覧](#aws版-修正一覧)
2. [Azure版 修正一覧](#azure版-修正一覧)
3. [共通バックエンド修正](#共通バックエンド修正)
4. [CI/CD 修正一覧](#cicd-修正一覧)
5. [技術的知見・注意事項](#技術的知見注意事項)

---

## AWS版 修正一覧

| # | 症状 | 原因 | 修正 |
|---|------|------|------|
| 1 | Cognito ログインで `unauthorized_client` | Cognito クライアントに `implicit` フロー未設定 / staging コールバック URL 未登録 | `AllowedOAuthFlows: ["code","implicit"]` + staging URL を Pulumi に追加 |
| 2 | ログイン後 CloudFront ドメインへリダイレクト | `VITE_COGNITO_REDIRECT_URI` がハードコードの CloudFront URL を参照 | `window.location.origin` を使う動的生成に変更済み |

### AWS Bug 1 — Cognito `unauthorized_client`

**症状**: ログインボタン押下後に Cognito ホスト UI が `error=unauthorized_client` を返す。

**原因**:
- Cognito ユーザープールクライアントの `AllowedOAuthFlows` に `implicit` が含まれていなかった
- `CallbackURLs` に `https://staging.aws.ashnova.jp/sns/auth/callback` が含まれていなかった

**修正** (`infrastructure/pulumi/aws/simple-sns/__main__.py`):
```python
# 修正前
allowed_o_auth_flows=["code"]
callback_urls=["https://www.aws.ashnova.jp/sns/auth/callback"]

# 修正後
allowed_o_auth_flows=["code", "implicit"]
callback_urls=[
    "https://www.aws.ashnova.jp/sns/auth/callback",
    "https://staging.aws.ashnova.jp/sns/auth/callback",  # 追加
    "http://localhost:5173/sns/auth/callback",
]
```

---
## Azure版 修正一覧

| # | 症状 | 原因 | 修正 |
|---|------|------|------|
| 1 | ログイン後 FrontDoor 内部ホスト名へリダイレクト | Azure AD アプリの redirect_uri にカスタムドメイン未登録 | AD アプリ + フロントを `staging.azure.ashnova.jp` で再ビルド |
| 2 | SVG 画像 404 | `upload-batch` で `$web/sns/` に配置、CSS は `./assets/` 参照 | `$web/sns/assets/` にも配置するよう CI/CD 修正 |
| 3 | API 全エンドポイント 404 | Azure Functions デフォルト `routePrefix: "api"` によりパスが `/api/limits` に | `host.json` に `routePrefix: ""` を追加 |
| 4 | API 呼び出し CORS エラー | Kestrel が OPTIONS を先処理。platform CORS にカスタムドメイン未登録 | `az functionapp cors add` でカスタムドメインを登録 |
| 5 | 画像アップロード CORS エラー | Blob Storage CORS にカスタムドメイン未登録 | `az storage cors add` で Blob Storage に追加 |
| 6 | ログアウト後に SNS 画面へ戻らない | `post_logout_redirect_uri` の `/sns/` が AD アプリ未登録 | redirect_uris に `/sns/` を追加 |
| 7 | 503 Service Unavailable | `*.so` 削除 + aarch64/py3.12 でビルドしたバイナリを x86_64/py3.11 Azure に投入 | Docker `python:3.11-slim --platform linux/amd64` でビルド |
| 8 | 投稿一覧で nickname 表示されない | `_item_to_post` に `nickname` フィールド未実装（詳細は実装済みで不整合） | `nickname=item.get("nickname")` を追加 |
### Bug 3: API 全エンドポイント 404

**症状**: `/limits`, `/posts` などすべてのエンドポイントが 404

**原因**: Azure Functions のデフォルト `routePrefix` は `"api"` であるため、実際のパスは `/api/limits` になる。フロントエンドは `/limits` として呼んでいた。

**修正**: `services/api/host.json` に以下を追加

```json
{
  "version": "2.0",
  "extensions": {
    "http": {
      "routePrefix": ""
    }
  }
}
```

### Bug 4: API 呼び出し CORS エラー

**症状**: ブラウザコンソールに `Access-Control-Allow-Origin` エラー

**原因**: Azure Functions Flex Consumption では .NET の Kestrel が Python ランタイムより前にすべての OPTIONS リクエストを処理する。そのため Python コード側で CORS を設定しても意味がなく、**Azure Portal または CLI でプラットフォーム CORS を設定**しなければならない。カスタムドメイン `staging.azure.ashnova.jp` が platform CORS の許可オリジンに未登録だった。

**修正**:
```bash
az functionapp cors add \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins "https://staging.azure.ashnova.jp"
```

> **注意**: `az functionapp cors remove --allowed-origins '*'` で一旦ワイルドカードを削除してから個別に追加しないと、ワイルドカードが残ると個別の許可オリジンが無視される場合がある。

### Bug 5: 画像アップロード CORS エラー

**症状**: 画像選択後アップロード時に CORS エラー

**原因**: 画像アップロードは Azure Function を経由せず、**Blob Storage に直接 SAS URL で PUT する**。Blob Storage の CORS 設定は Function App の CORS とは**完全に独立**しており、別途設定が必要。

**修正**:
```bash
az storage cors clear \
  --account-name "$STORAGE_ACCOUNT" --services b

az storage cors add \
  --account-name "$STORAGE_ACCOUNT" \
  --services b \
  --methods GET POST PUT DELETE OPTIONS \
  --origins "https://staging.azure.ashnova.jp" \
  --allowed-headers "*" \
  --exposed-headers "*" \
  --max-age 3600
```

### Bug 6: ログアウト後 SNS 画面へ戻らない

**症状**: ログアウトボタン押下後、SNS 画面 (`/sns/`) に戻らずブラウザがブロック

**原因**: Azure AD の OIDC ログアウトフロー (`post_logout_redirect_uri`) は、**アプリ登録の redirect_uris に登録されたURI にしかリダイレクトしない**。`/sns/auth/callback` は登録済みだったが `/sns/` は未登録だった。

**修正**: AD アプリの redirect_uris に `/sns/` も追加
```bash
az ad app update \
  --id "$AD_APP_ID" \
  --web-redirect-uris \
    "https://staging.azure.ashnova.jp/sns/auth/callback" \
    "https://staging.azure.ashnova.jp/sns/"
```

### Bug 7: 503 Service Unavailable

**症状**: API 呼び出し時にすべて 503。Function App ログに `ModuleNotFoundError`

**原因**: 2つの問題が複合していた。

1. **アーキテクチャ不一致**: Dev Container は `aarch64` (ARM)、Python 3.12。Azure Functions Flex Consumption は `x86_64` (AMD)、Python 3.11。`pip install` で生成される `.so` (C拡張) のバイナリが一致しない。
2. **`.so` の誤削除**: CI/CD スクリプトが `*.so` を削除するステップを持っており、実際には必要な C 拡張バイナリまで削除していた。

**修正**: Docker でターゲット環境と同じ x86_64 / Python 3.11 を使って pip install する
```yaml
- name: Build Python packages
  run: |
    docker run --rm --platform linux/amd64 \
      -v "$(pwd)/services/api:/work" \
      python:3.11-slim \
      bash -c "pip install -r /work/requirements.txt --target /work/package"
```

> **注意**: `SCM_DO_BUILD_DURING_DEPLOYMENT` は Flex Consumption SKU では `InvalidAppSettingsException` となり**サポートされていない**。リモートビルドは使えないため、必ずローカル (Docker) でビルドした成果物をデプロイする必要がある。

### Bug 8: 投稿一覧で nickname が表示されない

**症状**: 投稿一覧の投稿者名が nickname でなく userId (UUID) で表示される

**原因**: `_item_to_post` (Cosmos DB → Post 変換関数) に `nickname` フィールドのマッピングが実装されていなかった。また `create_post` もニックネームを profiles コンテナから取得せずに投稿を保存していたため、Cosmos DB 上のドキュメントにも `nickname` フィールドが存在しなかった。

**修正** (`services/api/app/backends/azure_backend.py`):
```python
# _item_to_post
return Post(
    ...
    nickname=item.get("nickname"),  # 追加
)

# create_post
profile = await profiles_container.read_item(user_id, partition_key=user_id)
nickname = profile.get("nickname", user_id)
await posts_container.create_item({
    ...
    "nickname": nickname,  # 追加
})
```


---

## 共通バックエンド修正

AWS 版ではすでに実装済みだったが、Azure/GCP 版で未実装だった処理。

### create_post: nickname を profiles から取得して保存

**問題**: 投稿作成時に `nickname` を profiles テーブル/コレクションから取得せず、`nickname` フィールドなしで投稿を保存していた。結果として投稿ドキュメント自体に `nickname` が入らない。

| クラウド | 修正ファイル | 修正内容 |
|---------|------------|---------|
| Azure | `services/api/app/backends/azure_backend.py` | `profiles_container.read_item(user_id)` で nickname 取得 |
| GCP | `services/api/app/backends/gcp_backend.py` | `profiles_collection.document(user_id).get()` で nickname 取得 |

### _doc_to_post / _item_to_post: nickname フィールドマッピング追加

ストレージから取得したドキュメントを `Post` オブジェクトに変換する関数に `nickname` フィールドのマッピングが欠落していた。

```python
# GCP: _doc_to_post
return Post(
    ...
    nickname=data.get("nickname"),  # 追加
)

# Azure: _item_to_post
return Post(
    ...
    nickname=item.get("nickname"),  # 追加
)
```

---

## CI/CD 修正一覧 (Azure)

`.github/workflows/deploy-azure.yml` に加えた主要変更。

| # | ステップ | 変更内容 |
|---|---------|---------|
| 1 | Python パッケージビルド | `docker run --platform linux/amd64 python:3.11-slim pip install` に変更 |
| 2 | platform CORS 設定 | `az rest PUT` で `allowedOrigins` 配列を設定（clear ではなく個別追加） |
| 3 | Blob Storage CORS 設定 | `az storage cors add` で Blob に FrontDoor ホスト名 + カスタムドメイン + localhost を追加 |
| 4 | AD アプリ redirect_uris 更新 | Pulumi deploy 後に `az ad app update --web-redirect-uris` で `/sns/` と `/sns/auth/callback` を登録 |
| 5 | SVG アセット配置 | `upload-batch` 後に `dist/*.svg` を `$web/sns/assets/` にコピー |
| 6 | `.so` 削除ステップを削除 | C 拡張バイナリを誤削除していたステップを除去 |

---

## 技術的知見・注意事項

### Azure Functions Flex Consumption の CORS 動作

Flex Consumption SKU では **Kestrel (.NET HTTP サーバー) が Python ランタイムよりも前段で動作**し、すべての OPTIONS プリフライトリクエストを処理する。そのため：

- Python コード内で `Access-Control-Allow-Origin` ヘッダーを返しても効果なし
- CORS 設定は必ず Azure Portal / CLI の **platform CORS** で行う
- `az functionapp cors add` でオリジンを追加する

### Azure Blob Storage と Function App の CORS は独立

SAS URL を使った Blob への直接アップロードは Function App を経由しないため、Blob Storage の CORS は Function App とは**別に設定**しなければならない。

```
Function App CORS  →  API (GET/POST) の CORS を制御
Blob Storage CORS  →  画像直接アップロード (SAS PUT) の CORS を制御
```

### Azure AD の post_logout_redirect_uri

Azure AD の OIDC ログアウトフローで `post_logout_redirect_uri` を指定するとき、**対象 URI がアプリ登録の redirect_uris に含まれていなければならない**。ログインの callback URI だけでなく、ログアウト後の遷移先 URI もすべて登録しておく必要がある。

### Dev Container と Azure Functions のアーキテクチャ不一致

| 環境 | CPU アーキテクチャ | Python バージョン |
|------|-----------------|----------------|
| Dev Container (GitHub Codespaces) | aarch64 (ARM) | 3.12 |
| Azure Functions Flex Consumption | x86_64 (AMD) | 3.11 |

両者が異なるため、`pip install` で生成される `.so` (C 拡張バイナリ) はそのまま使えない。**必ず `--platform linux/amd64` + `python:3.11-slim` の Docker イメージでビルドする**。

### SCM_DO_BUILD_DURING_DEPLOYMENT は Flex Consumption 非対応

Flex Consumption SKU に `SCM_DO_BUILD_DURING_DEPLOYMENT=true` を設定すると `InvalidAppSettingsException` が発生する。リモートビルドは使えない。

---

## 参考リンク

- [Azure Functions routePrefix](https://docs.microsoft.com/azure/azure-functions/functions-bindings-http-webhook-output#hostjson-settings)
- [Azure Functions CORS](https://docs.microsoft.com/azure/azure-functions/functions-how-to-use-azure-function-app-settings#cors)
- [Azure Blob Storage CORS](https://docs.microsoft.com/rest/api/storageservices/cross-origin-resource-sharing--cors--support-for-the-azure-storage-services)
- [Azure AD redirect URIs](https://docs.microsoft.com/azure/active-directory/develop/reply-url)
