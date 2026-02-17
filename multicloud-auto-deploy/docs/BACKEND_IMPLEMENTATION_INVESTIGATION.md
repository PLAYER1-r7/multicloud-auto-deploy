# バックエンド実装調査レポート

**調査日**: 2026-02-17 19:30 JST  
**担当者**: GitHub Copilot (自動化エージェント)  
**関連**: [API動作確認レポート](API_OPERATION_VERIFICATION_REPORT.md)

---

## 調査目的

API動作確認で発見された500 Internal Server Errorの根本原因を特定するため、各クラウドプロバイダーのバックエンド実装状況を調査しました。

---

## エラーログ分析

### 1. AWS Lambda CloudWatch Logs

**エラーメッセージ**:

```
TypeError: Can't instantiate abstract class AwsBackend without an implementation for abstract method 'update_post'
```

**スタックトレース**:

```python
File "/var/task/app/main.py", line 95, in legacy_create_message
    backend = get_backend()
              ^^^^^^^^^^^^^
File "/var/task/app/backends/__init__.py", line 28, in get_backend
    return AwsBackend()
           ^^^^^^^^^^^^
TypeError: Can't instantiate abstract class AwsBackend without an implementation for abstract method 'update_post'
```

**原因**: `AwsBackend` クラスが抽象基底クラス `BackendBase` の `update_post` メソッドを実装していない

---

### 2. GCP Cloud Run Logs

**エラーメッセージ**:

```
NotImplementedError: GCP backend not yet implemented
```

**スタックトレース**:

```python
File "/layers/google.python.pip/pip/lib/python3.11/site-packages/fastapi/routing.py", line 301, in app
    raise NotImplementedError("GCP backend not yet implemented")
NotImplementedError: GCP backend not yet implemented
```

**原因**: `GcpBackend` クラスの全メソッドが未実装（全て `NotImplementedError` を投げる）

---

### 3. Azure Functions

Azure Functionsは正常にデプロイされたように見えますが、実際のアプリケーションコードが実行されていません（デフォルトのウェルカムページを表示）。

**推定原因**:

- デプロイパッケージの構成問題
- Azure Functions のエントリーポイント設定不備
- 環境変数 `CLOUD_PROVIDER` が正しく設定されていない可能性

---

## コード実装状況

### 抽象基底クラス (`app/backends/base.py`)

以下のメソッドが定義されています：

| メソッド                 | 説明                    | 必須実装 |
| ------------------------ | ----------------------- | -------- |
| `list_posts()`           | 投稿一覧取得            | ✅ Yes   |
| `create_post()`          | 投稿作成                | ✅ Yes   |
| `delete_post()`          | 投稿削除                | ✅ Yes   |
| `update_post()`          | 投稿更新                | ✅ Yes   |
| `get_profile()`          | プロフィール取得        | ✅ Yes   |
| `update_profile()`       | プロフィール更新        | ✅ Yes   |
| `generate_upload_urls()` | 画像アップロードURL生成 | ✅ Yes   |

---

### 各バックエンドの実装状況

#### ✅ AWS Backend (`app/backends/aws_backend.py`)

| メソッド                 | 実装状況        | コメント                           |
| ------------------------ | --------------- | ---------------------------------- |
| `list_posts()`           | ✅ 完了         | DynamoDB Query 使用                |
| `create_post()`          | ✅ 完了         | DynamoDB PutItem 使用              |
| `delete_post()`          | ✅ 完了         | DynamoDB DeleteItem 使用           |
| `update_post()`          | ✅ **修正完了** | **新規実装** (DynamoDB UpdateItem) |
| `get_profile()`          | 🟡 スタブ実装   | 固定データを返す                   |
| `update_profile()`       | 🟡 スタブ実装   | 固定データを返す                   |
| `generate_upload_urls()` | ✅ 完了         | S3 署名付きURL生成                 |

**修正内容**:

- `update_post()` メソッドを新規実装
- DynamoDB UpdateItem APIを使用
- 権限チェック、タイムスタンプ更新を含む

**環境変数要件**:

- `POSTS_TABLE_NAME`: DynamoDB テーブル名 (**必須**)
- `IMAGES_BUCKET_NAME`: S3 バケット名 (画像機能使用時)

---

#### ❌ GCP Backend (`app/backends/gcp_backend.py`)

| メソッド                 | 実装状況  | コメント              |
| ------------------------ | --------- | --------------------- |
| `list_posts()`           | ❌ 未実装 | `NotImplementedError` |
| `create_post()`          | ❌ 未実装 | `NotImplementedError` |
| `delete_post()`          | ❌ 未実装 | `NotImplementedError` |
| `update_post()`          | ❌ 未実装 | `NotImplementedError` |
| `get_profile()`          | ❌ 未実装 | `NotImplementedError` |
| `update_profile()`       | ❌ 未実装 | `NotImplementedError` |
| `generate_upload_urls()` | ❌ 未実装 | `NotImplementedError` |

**状態**: 完全に未実装（全メソッドがNotImplementedErrorを投げる）

**必要な実装**:

- Firestore クライアント初期化
- Cloud Storage クライアント初期化
- 各メソッドの実装（Firestore CRUD操作）

---

#### ❌ Azure Backend (`app/backends/azure_backend.py`)

| メソッド                 | 実装状況  | コメント              |
| ------------------------ | --------- | --------------------- |
| `list_posts()`           | ❌ 未実装 | `NotImplementedError` |
| `create_post()`          | ❌ 未実装 | `NotImplementedError` |
| `delete_post()`          | ❌ 未実装 | `NotImplementedError` |
| `update_post()`          | ❌ 未実装 | `NotImplementedError` |
| `get_profile()`          | ❌ 未実装 | `NotImplementedError` |
| `update_profile()`       | ❌ 未実装 | `NotImplementedError` |
| `generate_upload_urls()` | ❌ 未実装 | `NotImplementedError` |

**状態**: 完全に未実装（全メソッドがNotImplementedErrorを投げる）

**必要な実装**:

- Cosmos DB クライアント初期化
- Blob Storage クライアント初期化
- 各メソッドの実装（Cosmos DB CRUD操作）

---

#### ✅ Local Backend (`app/backends/local_backend.py`)

**目的**: ローカル開発・テスト用  
**実装**: メモリ内辞書を使用した完全実装

---

## 修正内容

### ✅ AWS Backend: `update_post()` メソッド追加

**ファイル**: `services/api/app/backends/aws_backend.py`

```python
def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
    """投稿を更新 (DynamoDB UpdateItem)"""
    try:
        # まず postId から SK を取得
        response = self.table.query(
            IndexName="PostIdIndex",
            KeyConditionExpression="postId = :postId",
            ExpressionAttributeValues={":postId": post_id},
        )

        if not response.get("Items"):
            raise ValueError(f"Post not found: {post_id}")

        item = response["Items"][0]

        # ユーザー権限チェック
        if item["userId"] != user.user_id and not user.is_admin:
            raise PermissionError("You do not have permission to update this post")

        # 更新
        now = datetime.now(timezone.utc).isoformat()
        update_expr = "SET updatedAt = :updatedAt"
        expr_values = {":updatedAt": now}

        if body.content is not None:
            update_expr += ", content = :content"
            expr_values[":content"] = body.content

        if body.tags is not None:
            update_expr += ", tags = :tags"
            expr_values[":tags"] = body.tags

        if body.image_keys is not None:
            update_expr += ", imageUrls = :imageUrls"
            expr_values[":imageUrls"] = body.image_keys

        self.table.update_item(
            Key={"PK": "POSTS", "SK": item["SK"]},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
        )

        return {
            "status": "updated",
            "post_id": post_id,
            "updated_at": now,
        }

    except Exception as e:
        logger.error(f"Error updating post: {e}")
        raise
```

**動作**:

1. PostIdIndexを使用してGSIから投稿を検索
2. ユーザー権限を確認（作成者または管理者のみ更新可能）
3. DynamoDB UpdateItemで部分更新
4. content, tags, image_keysが指定された場合のみ更新

---

## 次のアクションプラン

### 優先度：高 🔴

#### 1. AWS Backend の再デプロイ

```bash
# Lambda Layer 再ビルド
cd services/api
chmod +x build_lambda_layer.sh
./build_lambda_layer.sh

# AWS staging 再デプロイ
cd ../../infrastructure/pulumi/aws
pulumi up -s staging
```

**期待される結果**: `/api/messages/` エンドポイントが正常動作

---

#### 2. DynamoDB環境変数の確認

**確認事項**:

- Lambda関数に `POSTS_TABLE_NAME` 環境変数が設定されているか
- DynamoDB テーブルが存在するか
- Lambda実行ロールがDynamoDBへのアクセス権限を持っているか

```bash
# Lambda環境変数確認
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --query 'Environment.Variables'

# DynamoDB テーブル確認
aws dynamodb describe-table \
  --table-name [TABLE_NAME]
```

---

### 優先度：中 🟡

#### 3. GCP Backend の実装

**実装手順**:

1. Firestore client の初期化
2. `list_posts()` 実装（Firestore collection query）
3. `create_post()` 実装（Firestore document add）
4. `delete_post()` 実装（Firestore document delete）
5. `update_post()` 実装（Firestore document update）
6. Cloud Storage 署名付きURL生成

**参考**: `ashnova.v2/services/simple_sns_api/app/backends/gcp_backend.py` に既存実装あり

---

#### 4. Azure Backend の実装

**実装手順**:

1. Cosmos DB client の初期化
2. `list_posts()` 実装（Cosmos DB query）
3. `create_post()` 実装（Cosmos DB create_item）
4. `delete_post()` 実装（Cosmos DB delete_item）
5. `update_post()` 実装（Cosmos DB patch_item）
6. Blob Storage SAS URL生成

**参考**: `ashnova.v2/services/simple_sns_api/app/backends/azure_backend.py` に既存実装あり

---

#### 5. Azure Functions デプロイ問題の調査

**確認事項**:

- Pulumi Azure デプロイスクリプトの確認
- Functions App のランタイム設定
- `CLOUD_PROVIDER` 環境変数の設定
- デプロイパッケージの構成

```bash
# Azure Functions の設定確認
az functionapp config appsettings list \
  --name multicloud-auto-deploy-staging-func-d8a2guhfere0etcq \
  --resource-group [RESOURCE_GROUP]

# Functions リスト
az functionapp function list \
  --name multicloud-auto-deploy-staging-func-d8a2guhfere0etcq \
  --resource-group [RESOURCE_GROUP]
```

---

### 優先度：低 🟢

#### 6. 統合テストの実装

各バックエンドの動作を検証するテストスイート：

```python
# tests/integration/test_backends.py
import pytest
from app.backends import get_backend
from app.models import CreatePostBody
from app.auth import UserInfo

@pytest.mark.parametrize("provider", ["aws", "gcp", "azure"])
def test_create_and_list_posts(provider):
    """投稿作成と一覧取得のテスト"""
    backend = get_backend(provider)
    user = UserInfo(user_id="test-user", email="test@example.com")

    # 投稿作成
    body = CreatePostBody(content="Test post")
    result = backend.create_post(body, user)
    assert result["post_id"]

    # 一覧取得
    posts, next_token = backend.list_posts(limit=10, next_token=None, tag=None)
    assert len(posts) > 0
```

---

## 推定コスト・工数

| タスク                     | 工数    | 優先度 |
| -------------------------- | ------- | ------ |
| AWS Backend 再デプロイ     | 30分    | 🔴 高  |
| DynamoDB 環境変数確認      | 15分    | 🔴 高  |
| GCP Backend 実装           | 4-6時間 | 🟡 中  |
| Azure Backend 実装         | 4-6時間 | 🟡 中  |
| Azure Functions 調査・修正 | 2-3時間 | 🟡 中  |
| 統合テスト実装             | 3-4時間 | 🟢 低  |

**合計**: 約15-20時間（2-3日）

---

## リスク

### ⚠️ 高リスク

- **DynamoDB テーブルが存在しない**: インフラデプロイ時のエラー可能性
- **IAM権限不足**: Lambda実行ロールがDynamoDB/S3にアクセスできない

### 🟡 中リスク

- **GCP/Azure未実装**: 現時点でこれらの環境は使用不可
- **Azure Functions デプロイ問題**: 原因不明の問題が潜在している可能性

---

## 結論

### ✅ 解決済み

- AWS Backend の `update_post()` メソッド実装完了

### 🔄 進行中

- AWS staging 環境への再デプロイ準備

### ⏳ 未着手

- GCP Backend 完全実装
- Azure Backend 完全実装
- Azure Functions デプロイ問題の解決

### 📊 プロジェクト進捗

- **AWSバックエンド**: 95% 完了（コア機能実装済み、プロフィール機能は簡易実装）
- **GCPバックエンド**: 5% 完了（スケルトンのみ）
- **Azureバックエンド**: 5% 完了（スケルトンのみ）
- **総合**: 約35% 完了

---

## 次のステップ実行コマンド

```bash
# 1. AWS Backend 再デプロイ
cd /workspaces/ashnova/multicloud-auto-deploy/services/api
./build_lambda_layer.sh

cd ../../infrastructure/pulumi/aws
pulumi up -s staging -y

# 2. 環境変数確認
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --query 'Environment.Variables'

# 3. 再テスト
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/api/messages/ | jq .
```

---

**レポート終了**: 2026-02-17 19:35 JST

---

## 関連ドキュメント

- [API動作確認レポート](API_OPERATION_VERIFICATION_REPORT.md)
- [Lambda Layer自動化ログ](LAMBDA_LAYER_AUTOMATION_DEPLOYMENT_LOG.md)
- [最終デプロイ検証レポート](DEPLOYMENT_VERIFICATION_REPORT_FINAL.md)
