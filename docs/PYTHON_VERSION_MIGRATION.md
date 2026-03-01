# Python バージョン移行ガイド

**作成日**: 2026-02-28
**更新日**: 2026-02-28 Session 3 (Azure OpenAI o3-mini JSON 修正完了)
**ステータス**: Python 3.11 Docker ビルド ✅ / Azure OpenAI 動作 ✅ / o3-mini 正常動作 ✅

## 概要

Azure Functions デプロイメントで発生した `jiter`/`pydantic_core` インポートエラーの根本原因を調査し、Python バージョン不一致が原因であることを特定。Python 3.13 への統一的な移行を計画。

---

## 問題の詳細

### 発生したエラー

**エンドポイント**: `POST /api/HttpTrigger/v1/solve` (imageUrl パス)

**エラーメッセージ**:

```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
HTTP Status: 503
```

### 根本原因

**ビルド環境とランタイム環境の Python バージョン不一致**

| 環境                                 | Python バージョン | 設定場所                            |
| ------------------------------------ | ----------------- | ----------------------------------- |
| **ビルド環境** (GitHub Codespaces)   | **3.12.12**       | `.devcontainer/devcontainer.json`   |
| **ランタイム環境** (Azure Functions) | **3.11**          | `scripts/deploy-azure.sh` (line 97) |

**技術的な問題**:

- GitHub Codespaces (Python 3.12) で `pip install` 実行
- `.cpython-312-*.so` 形式のバイナリが生成される
- Azure Functions (Python 3.11) は `.cpython-311-*.so` を期待
- バイナリ互換性なし → インポートエラー

### 設定の不整合

**deploy-azure.sh のコメントとコードの矛盾**:

```bash
# Line 24 (コメント):
# Azure Functions (Flex Consumption, Python 3.12)

# Line 97 (実際のコード):
--runtime-version 3.11
```

---

## 実施した対処（緊急対応）

### Docker ベースのビルドプロセス

Python 3.11 互換パッケージをビルドするため Docker を使用:

```bash
cd /workspaces/multicloud-auto-deploy/services/api

docker run --rm \
  -v /workspaces/multicloud-auto-deploy/services/api:/src \
  -v $(pwd):/build \
  python:3.11-slim bash -c "
    apt-get update -qq && apt-get install -y -qq zip
    cd /build
    cp -r /src/app . && cp /src/function_app.py . && cp /src/host.json .
    pip install -q --target=. -r /src/requirements-azure.txt
    zip -r9 -q function-app.zip .
  "
```

### デプロイメント実行

```bash
az functionapp deployment source config-zip \
  --resource-group multicloud-auto-deploy-staging-rg \
  --name multicloud-auto-deploy-staging-func-d8a2guhfere0etcq \
  --src function-app.zip
```

**結果**:

- ✅ パッケージサイズ: 26MB
- ✅ デプロイID: `61d09d6c-6c16-43fb-9326-2888f401a989`
- ✅ jiter/pydantic_core エラー解消

---

## Azure Functions Python サポート状況

### 調査結果 (2026-02-28)

```bash
az functionapp list-runtimes --os linux | grep -i python
```

**サポート対象バージョン**:

```
Python|3.14   (プレビュー)
Python|3.13   (推奨)
Python|3.12
Python|3.11
Python|3.10
```

### 選定基準

- **Python 3.13**: 最新の安定版（本移行で採用）
- **Python 3.14**: プレビュー段階（本番環境では非推奨）

---

## Python 3.13 移行計画

### 変更が必要なファイル

#### 1. `.devcontainer/devcontainer.json`

**現在** (lines 17-19):

```json
"ghcr.io/devcontainers/features/python:1": {
  "version": "3.12"
}
```

**変更後**:

```json
"ghcr.io/devcontainers/features/python:1": {
  "version": "3.13"
}
```

#### 2. `scripts/deploy-azure.sh`

**Line 24 (コメント修正)**:

```bash
# 現在
# Azure Functions (Flex Consumption, Python 3.12)

# 変更後
# Azure Functions (Flex Consumption, Python 3.13)
```

**Line 97 (ランタイムバージョン変更)**:

```bash
# 現在
--runtime-version 3.11

# 変更後
--runtime-version 3.13
```

#### 3. Docker ビルドプロセス（緊急対応時のみ使用）

**現在**:

```bash
python:3.11-slim
```

**変更後**:

```bash
python:3.13-slim
```

#### 4. CI/CD パイプライン

**確認が必要なファイル**:

- `.github/workflows/*.yml` (GitHub Actions)
- Python バージョン指定がある場合は 3.13 に統一

---

## 移行手順

### ステップ 1: Codespaces 環境の更新

```bash
# 1. devcontainer.json を編集
# 2. Codespaces をリビルド
# Command Palette > Dev Containers: Rebuild Container
```

### ステップ 2: ローカルテスト

```bash
# Python バージョン確認
python3 --version  # 3.13.x であることを確認

# 依存関係のインストール
cd /workspaces/multicloud-auto-deploy/services/api
pip install -r requirements-azure.txt

# ローカルテスト実行
# (必要に応じて)
```

### ステップ 3: Azure Functions 更新

```bash
# deploy-azure.sh を編集
# --runtime-version 3.13 に変更

# デプロイスクリプト実行
cd /workspaces/multicloud-auto-deploy
bash scripts/deploy-azure.sh
```

### ステップ 4: 動作確認

```bash
# エンドポイントテスト
curl -X POST "https://[FUNCTION_APP_URL]/api/HttpTrigger/v1/solve" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "imageUrl": "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg",
      "source": "url"
    },
    "examMetadata": {"examName": "test", "year": 2025, "subject": "math"},
    "options": {"explain_steps": false}
  }' \
  -m 60 -w "\nHTTP: %{http_code}\n"
```

**期待される結果**:

- HTTP 200 OK
- OCR → LLM パイプライン正常動作
- インポートエラーなし

---

## 現在のインフラ構成（参考）

### Azure リソース (Staging 環境)

| リソース                   | 名前                                                   | エンドポイント                                                                              |
| -------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| **Function App**           | `multicloud-auto-deploy-staging-func-d8a2guhfere0etcq` | https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net |
| **Document Intelligence**  | `mcad-di-9e3f88`                                       | https://japaneast.api.cognitive.microsoft.com/                                              |
| **Azure OpenAI**           | `mcad-openai-v2` (✅ 正常動作)                         | https://mcad-openai-v2.openai.azure.com/                                                    |
| ~~`mcad-openai-cea07c11`~~ | ❌ 削除済み                                            | ~~https://japaneast.api.cognitive.microsoft.com/~~ (`--custom-domain` なし → 共有EP)        |
| **Resource Group**         | `multicloud-auto-deploy-staging-rg`                    | -                                                                                           |

### 環境変数（Function App）

```bash
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://japaneast.api.cognitive.microsoft.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=[設定済み]
AZURE_OPENAI_ENDPOINT=https://mcad-openai-v2.openai.azure.com/  # ✅ --custom-domain 指定済み
AZURE_OPENAI_KEY=[設定済み]
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_ACCURATE_DEPLOYMENT=o3-mini              # 数学推論用高精度モデル
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

---

## チェックリスト

### 移行前の確認事項

- [ ] `.devcontainer/devcontainer.json` で Python 3.13 を指定
- [ ] `scripts/deploy-azure.sh` のコメントとコードを一致させる
- [ ] CI/CD パイプラインの Python バージョンを確認
- [ ] requirements-azure.txt の互換性を確認（Python 3.13）

### 移行後の確認事項

- [ ] Codespaces で `python3 --version` が 3.13.x を表示
- [ ] Azure Functions で `az functionapp config show` が Python 3.13 を表示
- [ ] `/api/HttpTrigger/v1/solve` エンドポイントが正常動作
- [ ] jiter/pydantic_core エラーが発生しない
- [ ] OCR → LLM パイプライン全体が正常動作

### ドキュメント更新

- [ ] README.md に Python 3.13 要件を明記
- [ ] IMPLEMENTATION_GUIDE.md を更新
- [ ] deploy-azure.sh のコメントを修正

---

## 参考情報

### 関連ドキュメント

- [Azure Functions Python バージョンサポート](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/3.13.html)

### トラブルシューティング

**症状**: デプロイ後もインポートエラーが発生

**原因候補**:

1. Codespaces 環境が古い Python でビルド
2. pip キャッシュに古いバイナリが残存
3. Azure Functions のランタイムバージョン不一致

**対処**:

```bash
# 1. Codespaces リビルド
# Dev Containers: Rebuild Container

# 2. pip キャッシュクリア
pip cache purge
pip install --no-cache-dir -r requirements-azure.txt

# 3. Azure Functions 設定確認
az functionapp config show \
  --name multicloud-auto-deploy-staging-func-d8a2guhfere0etcq \
  --resource-group multicloud-auto-deploy-staging-rg \
  --query linuxFxVersion
```

---

## タイムライン

| 日付       | イベント                                                          |
| ---------- | ----------------------------------------------------------------- |
| 2026-02-28 | jiter エラー発生・調査                                            |
| 2026-02-28 | Python 3.11 Docker ビルドで緊急対応                               |
| 2026-02-28 | `mcad-openai-cea07c11` 認証エラー発生・調査                       |
| 2026-02-28 | `--custom-domain` なしが根本原因と判明、`mcad-openai-v2` で再作成 |
| 2026-02-28 | gpt-4o HTTP 200 全パイプライン動作確認 (latency 23s)              |
| 2026-02-28 | o3-mini デプロイ・`max_completion_tokens`・`extra_body`修正       |
| 2026-02-28 | o3-mini JSON 出力修正 (`response_format` + `_token_limit`)        |
| 2026-02-28 | o3-mini HTTP 200 完全動作確認 (confidence 0.9) ✅                 |
| 2026-02-28 | Python バージョン不一致の根本原因特定                             |
| 2026-02-28 | Python 3.13 移行計画策定                                          |
| **TBD**    | **Python 3.13 移行実施**                                          |

---

## Azure OpenAI 設定の問題 ✅ 全件解決済み (2026-02-28)

**状況**: 2026-02-28、全ての問題解決、o3-mini 正常動作

### 発生した問題と解決内容

| 段階 | エラー                           | 原因                                                  | 状態                         |
| ---- | -------------------------------- | ----------------------------------------------------- | ---------------------------- |
| 1    | HTTP 401 (Unauthorized)          | `--custom-domain` なしリソース → 共有EP               | ✅ `mcad-openai-v2` に再作成 |
| 2    | HTTP 502 (Connection error)      | エンドポイント URL 誤設定                             | ✅ 正しい専用ドメインに変更  |
| 3    | HTTP 404 DeploymentNotFound      | `AZURE_OPENAI_ACCURATE_DEPLOYMENT=o3-mini` 未デプロイ | ✅ `o3-mini` デプロイ        |
| 4    | o3-mini `message.content=None`   | `max_completion_tokens=2000` 不足                     | ✅ 8192 に変更               |
| 5    | `extra_body` エラー              | Azure OpenAI 非対応                                   | ✅ 削除                      |
| 6    | 「解答を生成できませんでした。」 | `response_format` 未設定 → JSON パース失敗            | ✅ `response_format` 追加    |

### 試みた対応

#### ✅ 全て完了

- [x] `mcad-openai-cea07c11` 削除（`--custom-domain` なし → HTTP 401 の根本原因）
- [x] `mcad-openai-v2` 再作成（`--custom-domain mcad-openai-v2` 付き）
- [x] gpt-4o デプロイメント作成（バージョン: 2024-11-20）
- [x] o3-mini デプロイメント作成
- [x] 環境変数設定：
  - `AZURE_OPENAI_ENDPOINT=https://mcad-openai-v2.openai.azure.com/`
  - `AZURE_OPENAI_KEY=<設定済み>`
  - `AZURE_OPENAI_DEPLOYMENT=gpt-4o`
  - `AZURE_OPENAI_ACCURATE_DEPLOYMENT=o3-mini`
  - `AZURE_OPENAI_API_VERSION=2024-12-01-preview`
- [x] `azure_math_solver.py` のバグ修正（`_token_limit` + `response_format`）
- [x] Python 3.11 Docker ビルド (18MB) → デプロイ → HTTP 200 確認

### 確認済みリソース状態 (2026-02-28)

```json
{
  "name": "mcad-openai-v2",
  "kind": "OpenAI",
  "location": "japaneast",
  "sku": "S0",
  "endpoint": "https://mcad-openai-v2.openai.azure.com/",
  "customDomain": "mcad-openai-v2",
  "provisioningState": "Succeeded",
  "deployments": [
    {
      "name": "gpt-4o",
      "model": "gpt-4o",
      "version": "2024-11-20",
      "status": "ok"
    },
    {
      "name": "o3-mini",
      "model": "o3-mini",
      "version": "latest",
      "status": "ok"
    }
  ]
}
```

### 確認済みテスト結果

```
HTTP: 200
status: completed
final: '(1) Uₜ = (t²(3-2t), 3t(1-t)), (2) 面積 = 3/5, (3) 弧長 = 2a³ - 3a² + 3a.'
steps count: 4
confidence: 0.9
```

---

## 承認・レビュー

- **作成者**: AI Assistant (GitHub Copilot)
- **レビュー者**: TBD
- **承認日**: TBD

---

## 変更履歴

| バージョン | 日付       | 変更内容                                                      |
| ---------- | ---------- | ------------------------------------------------------------- |
| 1.0        | 2026-02-28 | 初版作成（調査結果・移行計画）                                |
| 1.1        | 2026-02-28 | Azure OpenAI 設定トラブル詳細・対応策追加                     |
| 1.2        | 2026-02-28 | 全問題解決後の更新：mcad-openai-v2 確認・o3-mini 動作確認反映 |
