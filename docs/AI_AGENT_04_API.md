# 04 — API & Data Model

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## API Endpoints

| Method     | Path                     | Auth | Description                                    |
| ---------- | ------------------------ | ---- | ---------------------------------------------- |
| GET        | `/`                      | ❌   | Root — cloud info                              |
| GET        | `/health`                | ❌   | Health check                                   |
| GET        | `/docs`                  | ❌   | Swagger UI                                     |
| GET        | `/redoc`                 | ❌   | ReDoc                                          |
| **GET**    | `/posts`                 | ❌   | List posts (pagination + tag filter supported) |
| **GET**    | `/posts/{post_id}`       | ❌   | Get single post                                |
| **POST**   | `/posts`                 | ✅   | Create post                                    |
| **PUT**    | `/posts/{post_id}`       | ✅   | Update post (owner or admin)                   |
| **DELETE** | `/posts/{post_id}`       | ✅   | Delete post (owner or admin)                   |
| GET        | `/profile/{user_id}`     | ❌   | Get profile                                    |
| PUT        | `/profile/{user_id}`     | ✅   | Update profile                                 |
| POST       | `/uploads/presigned-url` | ✅   | Issue a presigned URL for image upload         |

---

## リクエスト / レスポンス スキーマ

### POST /posts — リクエスト

```json
{
  "content": "string (1-10000)",
  "isMarkdown": false,
  "imageKeys": ["key1", "key2"],
  "tags": ["tag1", "tag2"]
}
```

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
  "author": "string (= userId)",
  "created_at": "...",
  "updated_at": "...",
  "image_url": "string | null"
}
```

### GET /posts クエリパラメータ

| パラメータ  | 型         | デフォルト | 説明                     |
| ----------- | ---------- | ---------- | ------------------------ |
| `limit`     | int (1-50) | 20         | 取得件数                 |
| `nextToken` | string     | null       | ページネーショントークン |
| `tag`       | string     | null       | タグフィルタ             |

---

## Data Model (DynamoDB Single-Table Design)

Shared table design for local and AWS. Azure/GCP use the same logical model.

### Table: `simple-sns-messages` (AWS) / `simple-sns-local` (Local)

| Item type | PK              | SK                       | Key attributes                                         |
| --------- | --------------- | ------------------------ | ------------------------------------------------------ |
| Post      | `POSTS`         | `<ISO-timestamp>#<uuid>` | `postId`, `userId`, `content`, `tags`, `createdAt`     |
| Profile   | `USER#<userId>` | `PROFILE`                | `postId=PROFILE#<userId>`, `userId`, `nickname`, `bio` |

### GSI: `PostIdIndex`

| Key        | Value    |
| ---------- | -------- |
| Hash key   | `postId` |
| Projection | ALL      |

Used for direct post lookup (`/posts/{id}`) and  
profile lookup (`postId = PROFILE#<userId>`).

---

## Backend Implementation Classes

```
BackendBase (base.py)  ← abstract class
  ├── list_posts(limit, next_token, tag) → (list[Post], next_token)
  ├── get_post(post_id) → Post
  ├── create_post(body, user) → Post
  ├── update_post(post_id, body, user) → Post
  ├── delete_post(post_id, user) → dict
  ├── get_profile(user_id) → Profile
  ├── update_profile(user_id, body, user) → Profile
  └── generate_upload_urls(keys, user) → list[UploadUrl]

AwsBackend    → DynamoDB (boto3) + S3
AzureBackend  → Cosmos DB (azure-cosmos) + Blob Storage
GcpBackend    → Firestore (google-cloud-firestore) + Cloud Storage
LocalBackend  → DynamoDB Local + MinIO (S3-compatible)
```

### Backend selection

```python
# services/api/app/backends/__init__.py
def get_backend() -> BackendBase:
    provider = config.CLOUD_PROVIDER  # "aws" | "azure" | "gcp" | "local"
    ...
```

---

## Local Development Environment

```bash
cd multicloud-auto-deploy
docker compose up   # api(:8000) + dynamodb-local(:8001) + minio(:9000/:9001)
```

| Service              | URL                          | Credentials             |
| -------------------- | ---------------------------- | ----------------------- |
| FastAPI              | http://localhost:8000        | —                       |
| Swagger UI           | http://localhost:8000/docs   | —                       |
| DynamoDB Local shell | http://localhost:8001/shell/ | —                       |
| MinIO Console        | http://localhost:9001        | minioadmin / minioadmin |

### Required environment variables (auto-set by docker-compose)

```
CLOUD_PROVIDER=local
DYNAMODB_ENDPOINT=http://dynamodb-local:8001
DYNAMODB_TABLE_NAME=simple-sns-local
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=simple-sns
AUTH_DISABLED=true   ← true is acceptable for local only
```

---

## Running Tests

```bash
# Unit + integration tests (mocked)
cd services/api
pytest tests/test_backends_integration.py -v

# AWS only
pytest -m aws

# Live deployed API tests
export API_BASE_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
pytest tests/test_api_endpoints.py -v

# E2E (all clouds, curl-based)
./scripts/test-e2e.sh
```

---

## Next Section

→ [05 — Infrastructure (Pulumi)](AI_AGENT_05_INFRA.md)
