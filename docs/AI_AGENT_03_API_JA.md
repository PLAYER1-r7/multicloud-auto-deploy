# 03 — API とデータモデル

> 第II部 — アーキテクチャ・設計 | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## API エンドポイント

| メソッド   | パス                      | 認証 | 説明                                            |
| ---------- | ------------------------- | ---- | ----------------------------------------------- |
| GET        | `/`                       | ❌   | ルート — クラウド情報                           |
| GET        | `/health`                 | ❌   | ヘルスチェック                                  |
| GET        | `/limits`                 | ❌   | アップロード/投稿制限（`maxImagesPerPost`）     |
| GET        | `/docs`                   | ❌   | Swagger UI                                      |
| GET        | `/redoc`                  | ❌   | ReDoc                                           |
| **GET**    | `/posts`                  | ❌   | 投稿一覧（ページネーション+タグフィルター対応） |
| **GET**    | `/posts/{post_id}`        | ❌   | 単一投稿を取得                                  |
| **POST**   | `/posts`                  | ✅   | 投稿を作成                                      |
| **PUT**    | `/posts/{post_id}`        | ✅   | 投稿を更新（所有者または管理者）                |
| **DELETE** | `/posts/{post_id}`        | ✅   | 投稿を削除（所有者または管理者）                |
| GET        | `/profile/{user_id}`      | ❌   | プロフィールを取得                              |
| PUT        | `/profile/{user_id}`      | ✅   | プロフィールを更新                              |
| POST       | `/uploads/presigned-url`  | ✅   | 画像アップロード用署名付き URL を発行（単数）   |
| POST       | `/uploads/presigned-urls` | ✅   | 一括アップロード用署名付き URL を発行           |

---

## リクエスト / レスポンス スキーマ

### POST /posts — リクエストボディ

```json
{
  "content": "string（1-10000）",
  "isMarkdown": false,
  "imageKeys": ["key1", "key2"], // 最大 16（サーバー側で MAX_IMAGES_PER_POST で強制）
  "tags": ["tag1", "tag2"]
}
```

### GET /limits — レスポンス

```json
{ "maxImagesPerPost": 10 }
```

フロントエンドはマウント時にこれを取得。`MAX_IMAGES_PER_POST` はバックエンドの環境変数（デフォルト：10）。
これが正規ソース — **フロントエンドにアップロード制限をハードコードしない**。

### GET /posts — レスポンス

```json
{
  "items": [ <Post> ],
  "limit": 20,
  "nextToken": "string | null"
}
```

### Post オブジェクト

```json
{
  "postId": "uuid",
  "userId": "string",
  "nickname": "string | null",
  "content": "string",
  "isMarkdown": false,
  "imageUrls": ["https://..."],
  "tags": ["tag"],
  "createdAt": "2026-02-20T00:00:00Z",
  "updatedAt": "2026-02-20T00:00:00Z",

  // 後方互換フィールド（snake_case）
  "id": "uuid",
  "author": "string（= userId）",
  "created_at": "...",
  "updated_at": "...",
  "image_url": "string | null"
}
```

### GET /posts クエリパラメータ

| パラメータ  | 型          | デフォルト | 説明                     |
| ----------- | ----------- | ---------- | ------------------------ |
| `limit`     | int（1-50） | 20         | 返すアイテム数           |
| `nextToken` | string      | null       | ページネーショントークン |
| `tag`       | string      | null       | タグフィルター           |

> **GCP 注記**：`generate_signed_url()` は `service_account_email` + `access_token` が必須
> （IAM `signBlob` API パス）Compute Engine 認証情報は秘密鍵を含まないため。
> `AI_AGENT_00_CRITICAL_RULES.md` のルール 11 を参照。

### POST /uploads/presigned-urls — リクエストボディ

```json
{
  "count": 3, // ファイル数（ge=1、le=100；実際の制限は /limits 経由）
  "contentTypes": ["image/jpeg", "image/png", "image/webp"] // ファイルあたり 1 つ
}
```

### POST /uploads/presigned-urls — レスポンス

```json
{
  "urls": [
    { "uploadUrl": "https://...署名付き-url...", "key": "uploads/uuid.jpg" },
    ...
  ]
}
```

> **GCP 注記**：`generate_signed_url()` は `service_account_email` + `access_token` が必須
> （IAM `signBlob` API パス）Compute Engine 認証情報は秘密鍵を含まないため。
> `AI_AGENT_00_CRITICAL_RULES.md` のルール 11 を参照。

---

## データモデル（DynamoDB Single-Table Design）

ローカルと AWS 向け共有テーブル設計。Azure/GCP は同じ論理モデルを使用。

### テーブル：`{project}-{stack}-posts`（AWS）/ `simple-sns-local`（ローカル）

| アイテムタイプ | PK              | SK                       | キー属性                                               |
| -------------- | --------------- | ------------------------ | ------------------------------------------------------ |
| 投稿           | `POSTS`         | `<ISO-timestamp>#<uuid>` | `postId`、`userId`、`content`、`tags`、`createdAt`     |
| プロフィール   | `USER#<userId>` | `PROFILE`                | `postId=PROFILE#<userId>`、`userId`、`nickname`、`bio` |

### GSI：`PostIdIndex`

| キー             | 値       |
| ---------------- | -------- |
| ハッシュキー     | `postId` |
| プロジェクション | ALL      |

直接投稿ルックアップ（`/posts/{id}`）と
プロフィールルックアップ（`postId = PROFILE#<userId>`）に使用。

---

## バックエンド実装クラス

```
BackendBase（base.py） ← 抽象クラス
  ├── list_posts(limit、next_token、tag) → （list[Post]、next_token）
  ├── get_post(post_id) → Post
  ├── create_post(body、user) → Post
  ├── update_post(post_id、body、user) → Post
  ├── delete_post(post_id、user) → dict
  ├── get_profile(user_id) → Profile
  ├── update_profile(user_id、body、user) → Profile
  └── generate_upload_urls(keys、user) → list[UploadUrl]

AwsBackend    → DynamoDB（boto3）+ S3
AzureBackend  → Cosmos DB（azure-cosmos）+ Blob Storage
GcpBackend    → Firestore（google-cloud-firestore）+ Cloud Storage
LocalBackend  → DynamoDB Local + MinIO（S3 互換）
```

### バックエンド選択

```python
# services/api/app/backends/__init__.py
def get_backend() -> BackendBase:
    provider = config.CLOUD_PROVIDER  # "aws" | "azure" | "gcp" | "local"
    ...
```

---

## ローカル開発環境

```bash
cd multicloud-auto-deploy
docker compose up   # api(:8000) + dynamodb-local(:8001) + minio(:9000/:9001)
```

| サービス              | URL                          | 認証情報                |
| --------------------- | ---------------------------- | ----------------------- |
| FastAPI               | http://localhost:8000        | —                       |
| Swagger UI            | http://localhost:8000/docs   | —                       |
| DynamoDB Local シェル | http://localhost:8001/shell/ | —                       |
| MinIO コンソール      | http://localhost:9001        | minioadmin / minioadmin |

### 必要な環境変数（docker-compose で自動設定）

```
CLOUD_PROVIDER=local
DYNAMODB_ENDPOINT=http://dynamodb-local:8001
DYNAMODB_TABLE_NAME=simple-sns-local
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=simple-sns
AUTH_DISABLED=true   ← ローカルのみ true は許容
```

---

## テスト実行

```bash
# ユニット + 統合テスト（モック）
cd services/api
pytest tests/test_backends_integration.py -v

# AWS のみ
pytest -m aws

# ライブデプロイ API テスト
export API_BASE_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
pytest tests/test_api_endpoints.py -v

# E2E（すべてのクラウド、curl ベース）
./scripts/test-e2e.sh
```

---

## 次のセクション

→ [04 — インフラストラクチャ（Pulumi）](AI_AGENT_04_INFRA_JA.md)
