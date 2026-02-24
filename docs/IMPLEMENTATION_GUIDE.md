# ソース実装解説書

> 本ドキュメントは `docs/AI_AGENT_0*.md` の設計書を前提に、実際のソースコードがどのように実装されているかを日本語で解説する。

---

## 目次

1. [プロジェクト全体像](#1-プロジェクト全体像)
2. [バックエンド API（FastAPI）](#2-バックエンド-apifastapi)
3. [認証・JWT 検証](#3-認証jwt-検証)
4. [クラウド別バックエンド実装](#4-クラウド別バックエンド実装)
5. [クラウド別エントリーポイント](#5-クラウド別エントリーポイント)
6. [フロントエンド（React SPA）](#6-フロントエンドreact-spa)
7. [ローカル開発環境](#7-ローカル開発環境)

---

## 1. プロジェクト全体像

### アプリケーション概要

**multicloud-auto-deploy** は、SNS スタイルの投稿アプリ（文章・画像・タグ）を AWS / Azure / GCP の **3つのクラウドに同時デプロイ** するプラットフォームである。

```
ユーザー
  │
  ├─ [AWS]   CloudFront → S3 (React SPA)
  │          API Gateway v2 → Lambda (FastAPI) → DynamoDB
  │
  ├─ [Azure] Front Door → Blob Storage (React SPA)
  │          Azure Functions → Cosmos DB
  │
  └─ [GCP]   Cloud CDN → GCS (React SPA)
             Cloud Run → Firestore
```

### ディレクトリ構成（主要部分）

```
services/
  api/                        ← FastAPI バックエンド（3クラウド共通）
    app/
      main.py                 ← FastAPI アプリ本体・CORS・ルーター登録
      config.py               ← 環境変数を Pydantic Settings で管理
      models.py               ← Pydantic データモデル
      auth.py                 ← JWT 認証ミドルウェア
      jwt_verifier.py         ← Cognito / Azure AD / Firebase JWT 検証
      backends/
        base.py               ← 抽象基底クラス（インターフェース定義）
        aws_backend.py        ← DynamoDB + S3 実装
        azure_backend.py      ← Cosmos DB + Blob Storage 実装
        gcp_backend.py        ← Firestore + Cloud Storage 実装
        local_backend.py      ← DynamoDB Local + MinIO 実装
      routes/
        posts.py              ← /posts エンドポイント
        profile.py            ← /profile エンドポイント
        uploads.py            ← /uploads エンドポイント
    index.py                  ← AWS Lambda ハンドラー（Mangum）
    function_app.py           ← Azure Functions ハンドラー
    function.py               ← GCP Cloud Run ハンドラー
  frontend_react/             ← React 18 + Vite + TypeScript SPA
    src/
      App.tsx                 ← ルーティング定義
      api/                    ← Axios API クライアント
      contexts/AuthContext.tsx← 認証状態管理
      components/             ← UI コンポーネント
      pages/                  ← ページコンポーネント
      config/auth.ts          ← 認証プロバイダー設定
```

---

*次セクション → [2. バックエンド API（FastAPI）](#2-バックエンド-apifastapi)*

---

## 2. バックエンド API（FastAPI）

### 2-1. アプリケーション起動 (`main.py`)

`services/api/app/main.py` が FastAPI アプリの中心。

**主な処理の流れ:**

```python
# 1. AWS Lambda Powertools をインポート（なければ標準 logging にフォールバック）
try:
    from aws_lambda_powertools import Logger, Metrics, Tracer
    logger = Logger(service="simple-sns-api")
    ...
except ImportError:
    logger = logging.getLogger(__name__)

# 2. FastAPI アプリを生成
app = FastAPI(title="Simple SNS API", version="3.0.0", ...)

# 3. CORS ミドルウェア追加（環境変数 CORS_ORIGINS で制御）
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)

# 4. Gzip 圧縮（1KB 以上のレスポンスを自動圧縮）
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 5. ルーター登録
app.include_router(posts.router)    # /posts
app.include_router(uploads.router)  # /uploads
app.include_router(profile.router)  # /profile
app.include_router(limits.router)   # /limits
```

**ライフサイクル管理**: `@asynccontextmanager` の `lifespan` 関数でアプリ起動・終了時のログを出力する。

**後方互換エイリアス**: 旧フロントエンド向けに `/api/messages/` エンドポイントを維持している。このエンドポイントでは認証トークンがなくても `anonymous` ユーザーとして扱われる（テスト互換のための意図的な設計）。

---

### 2-2. 設定管理 (`config.py`)

`pydantic_settings.BaseSettings` を継承した `Settings` クラスで全ての環境変数を管理する。

```python
class Settings(BaseSettings):
    cloud_provider: CloudProvider = CloudProvider.LOCAL  # "aws"|"azure"|"gcp"|"local"
    auth_disabled: bool = False
    posts_table_name: Optional[str] = None   # AWS用
    cosmos_db_endpoint: Optional[str] = ...  # Azure用
    gcp_project_id: Optional[str] = None     # GCP用
    ...
```

**ポイント:**
- 環境変数名の揺れ（例: `COGNITO_USER_POOL_ID` vs `AWS_COGNITO_USER_POOL_ID`）を `AliasChoices` で吸収している。
- `CLOUD_PROVIDER` が未設定の場合は、実行環境の特徴から自動検出される（`config.py` 末尾の auto-detect ロジック）。

**クラウド自動検出ロジック:**

| 環境変数              | 判定クラウド |
| --------------------- | ----------- |
| `AWS_EXECUTION_ENV`   | aws         |
| `WEBSITE_INSTANCE_ID` | azure       |
| `K_SERVICE`           | gcp         |
| （なし）              | local       |

---

### 2-3. データモデル (`models.py`)

Pydantic v2 で定義。**camelCase と snake_case 両方を返す**ことが最大の特徴。

```python
class Post(BaseModel):
    id: str = Field(..., alias="postId")
    user_id: str = Field(..., alias="userId")
    content: str
    ...

    @model_serializer
    def serialize_model(self) -> dict:
        return {
            # 新フロントエンド用 (camelCase)
            "postId": self.id,
            "userId": self.user_id,
            ...
            # 旧フロントエンド用 (snake_case)
            "id": self.id,
            "author": self.user_id,
            "created_at": self.created_at,
        }
```

`model_config = {"populate_by_name": True}` により、リクエスト受信時は `postId`（alias）でも `id`（フィールド名）のどちらでも受け付ける。

`ListPostsResponse` も同様に `items` / `results` / `messages` の3つのキーで同じデータを返し、複数バージョンのフロントエンドと互換する。

---

### 2-4. ルーター (`routes/`)

| ファイル      | prefix      | 主な処理 |
| ------------- | ----------- | -------- |
| `posts.py`    | `/posts`    | 投稿の CRUD（GET/POST/PUT/DELETE） |
| `profile.py`  | `/profile`  | プロフィール取得・更新 |
| `uploads.py`  | `/uploads`  | 画像アップロード用署名付き URL 発行 |

**認証の使い分け:**

```python
# 認証任意（未ログインでも閲覧可）
@router.get("")
def list_posts(...) -> ListPostsResponse:
    ...

# 認証必須（require_user が 401 を返す）
@router.post("", status_code=201)
def create_post(body: CreatePostBody, user: UserInfo = Depends(require_user)):
    ...
```

`Depends(require_user)` は `auth.py` の関数で、トークンがない場合 HTTP 401 を返す。`Depends(get_current_user)` はトークンなしの場合 `None` を返す（認証任意）。

---

## 3. 認証・JWT 検証

### 3-1. 認証フロー概要 (`auth.py`)

```
クライアント
  Authorization: Bearer <JWT>
         ↓
  get_current_user() / require_user()
         ↓
  get_jwt_verifier()  ← settings.auth_provider で切替
         ↓
  JWTVerifier.verify_token()
         ↓
  UserInfo { user_id, email, groups }
```

`auth_disabled=true` の場合（ローカル開発時のみ許容）は検証をスキップし、テスト用ユーザーを返す。

**UserInfo クラス:**

```python
@dataclass
class UserInfo:
    user_id: str
    email: Optional[str] = None
    groups: Optional[list[str]] = None

    @property
    def is_admin(self) -> bool:
        return self.groups is not None and "Admins" in self.groups
```

管理者判定は `groups` リストに `"Admins"` が含まれるかで行う。

---

### 3-2. JWT 検証 (`jwt_verifier.py`)

`JWTVerifier` クラスが3クラウドの JWT 検証を統一的に処理する。

**JWKS エンドポイント:**

| プロバイダー | JWKS URI |
| ------------ | -------- |
| Cognito (AWS) | `https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json` |
| Firebase (GCP) | `https://www.googleapis.com/service_accounts/v1/jwk/securetoken@...` |
| Azure AD | `https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys` |

**JWKS キャッシュ:**
毎リクエストごとに HTTP 取得すると遅延が大きいため、1時間のインメモリキャッシュを実装している。キャッシュ期限切れ中にフェッチ失敗した場合は、古いキャッシュをフォールバックとして使い続ける（可用性優先の設計）。

```python
def get_jwks(self) -> dict:
    if キャッシュ有効:
        return self._jwks_cache
    # 取得失敗時はキャッシュを使い続ける
    if self._jwks_cache:
        logger.warning("Using expired JWKS cache")
        return self._jwks_cache
    raise
```

**トークン検証処理:**
`python-jose` ライブラリを使い、JWKS から公開鍵を取得して署名検証 + issuer / audience 検証を行う。検証後 `extract_user_info()` でクラウドごとの claims 差異を吸収して `UserInfo` に変換する。

---

## 4. クラウド別バックエンド実装

### 4-1. バックエンド選択の仕組み (`backends/__init__.py`)

```python
@lru_cache(maxsize=1)
def get_backend() -> BackendBase:
    provider = settings.cloud_provider  # 環境変数 CLOUD_PROVIDER
    if provider == CloudProvider.AWS:
        return AwsBackend()
    elif provider == CloudProvider.AZURE:
        return AzureBackend()
    elif provider == CloudProvider.GCP:
        return GcpBackend()
    else:
        return LocalBackend()
```

`@lru_cache(maxsize=1)` により、同一プロセス内ではバックエンドインスタンスを1回だけ生成する（接続の使い回し）。

---

### 4-2. 抽象基底クラス (`base.py`)

全バックエンドが実装すべきインターフェースを定義する。

```python
class BackendBase(ABC):
    @abstractmethod
    def list_posts(limit, next_token, tag) -> (list[Post], next_token)
    @abstractmethod
    def get_post(post_id) -> Optional[Post]
    @abstractmethod
    def create_post(body, user) -> dict
    @abstractmethod
    def update_post(post_id, body, user) -> dict   # ※ AWS / Local のみ完全実装
    @abstractmethod
    def delete_post(post_id, user) -> dict
    @abstractmethod
    def get_profile(user_id) -> ProfileResponse
    @abstractmethod
    def update_profile(user, body) -> ProfileResponse
    @abstractmethod
    def generate_upload_urls(count, user, content_types) -> list[dict]
```

---

### 4-3. AWS バックエンド (`aws_backend.py`)

**データストア:** DynamoDB Single Table Design + S3

**テーブル設計:**

```
PK        SK                           内容
POSTS     <ISO timestamp>#<uuid>       投稿データ
PROFILES  <userId>                     ユーザープロフィール
```

SK に `<timestamp>#<uuid>` を使うことで、`ScanIndexForward=False` クエリが標準の降順（新着順）になる。

**投稿一覧取得:**

```python
def list_posts(self, limit, next_token, tag):
    query_kwargs = {
        "KeyConditionExpression": "PK = :pk",
        "ExpressionAttributeValues": {":pk": "POSTS"},
        "ScanIndexForward": False,  # 新しい順
        "Limit": limit,
    }
    if next_token:
        query_kwargs["ExclusiveStartKey"] = {"PK": "POSTS", "SK": next_token}
    if tag:
        query_kwargs["FilterExpression"] = "contains(tags, :tag)"
    response = self.table.query(**query_kwargs)
    # next_token = LastEvaluatedKey["SK"]
```

ページネーションには `LastEvaluatedKey["SK"]`（= 最後のアイテムの SK）をトークンとして使う。

**画像 URL の解決:**

S3 に保存された画像キーは、取得時に `generate_presigned_url`（1時間有効）に変換する。
- `https://` で始まる場合はそのまま返す
- `http://` はセキュリティ上 Mixed Content となるためスキップする
- それ以外（S3 キー）は署名付き URL に変換する

---

### 4-4. Azure バックエンド (`azure_backend.py`)

**データストア:** Cosmos DB（posts / profiles コンテナ） + Blob Storage

DynamoDB との違いは、Cosmos DB では**コンテナ(テーブル)を用途ごとに分ける**点。posts コンテナと profiles コンテナを別々に持つ。

```python
self.posts_container = self.database.create_container_if_not_exists(
    id="posts",
    partition_key=PartitionKey(path="/postId"),
)
self.profiles_container = self.database.create_container_if_not_exists(
    id="profiles",
    partition_key=PartitionKey(path="/userId"),
)
```

**画像 URL:** Blob SAS（24時間有効）に変換。フル Blob URL が既に保存されている場合はキー部分を抽出して SAS を改めて付与する。

**インポート安全設計:** `azure-cosmos` や `azure-storage-blob` がインストールされていない環境でも `ImportError` をキャッチして警告ログだけ出す。実際に `AzureBackend()` を生成しようとした時に例外を投げる。

---

### 4-5. GCP バックエンド (`gcp_backend.py`)

**データストア:** Firestore（posts / profiles コレクション） + Cloud Storage

Firestore ではドキュメント ID でページネーションを行う。

```python
def list_posts(self, limit, next_token, tag):
    query = col.order_by("createdAt", direction=DESCENDING).limit(limit + 1)
    if next_token:
        cursor_doc = col.document(next_token).get()
        query = query.start_after(cursor_doc)  # カーソルベースのページネーション
```

`limit + 1` 件取得して `len(docs) > limit` なら次ページがあると判断し、最後のドキュメント ID を `next_token` として返す。

**署名付き URL の特殊対応:**
GCP では Compute Engine のデフォルト認証情報には秘密鍵がないため、`generate_signed_url()` は使えない。代わりに IAM `signBlob` API を使うカスタム実装を行う。認証情報は `google.auth.default()` で取得し、`credentials.valid` を確認してから期限切れ時のみ refresh する（毎リクエストのメタデータサーバー呼び出しを回避）。

---

### 4-6. ローカルバックエンド (`local_backend.py`)

**データストア:** DynamoDB Local + MinIO（S3 互換）

AWS バックエンドと同じ Single Table Design を使うことで、ローカルで発見したバグが AWS でも同様に再現することを保証している。テーブルが存在しない場合は**初回起動時に自動作成**する。

```python
def _init_dynamodb(self):
    # テーブルが存在しなければ作成
    try:
        self.table = self.dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "PK", ...}, {"AttributeName": "SK", ...}],
            ...
        )
    except self.dynamodb.meta.client.exceptions.ResourceInUseException:
        self.table = self.dynamodb.Table(table_name)  # 既存テーブルを使う
```

---

## 5. クラウド別エントリーポイント

FastAPI アプリ本体（`app/main.py`）は3クラウドで**共通**。クラウドごとにその前段となるアダプター層が異なる。

### 5-1. AWS Lambda (`index.py`)

```python
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
```

`Mangum` が Lambda イベント（API Gateway Proxy v2 形式）を ASGI に変換し、FastAPI へ渡す。`lifespan="off"` は Lambda の短命実行モデルに対応するための設定。

Lambda Layer に FastAPI 等の依存ライブラリを格納し、アプリコード（〜78KB）と別管理することでデプロイ速度を改善している。

---

### 5-2. Azure Functions (`function_app.py`)

Azure Functions には Mangum 相当の標準アダプターがないため、**カスタム ASGI ブリッジ**を自前実装している。

主な処理フロー:

```
Azure Functions HttpRequest
    ↓
route_params["route"] からパスを取得
    "HttpTrigger/" プレフィックスを除去
    ↓
ASGI scope dict を組み立て
    {type: "http", path: "/posts", method: "GET", ...}
    ↓
FastAPI ASGI app を呼び出し
    ↓
レスポンスを func.HttpResponse に変換して返す
```

**CORS Preflight（OPTIONS）** は Azure Functions レベルで直接処理し、FastAPI に渡さずに 204 を返す（速度・安定性のため）。

インポートエラーが発生しても 503 でエラー内容を返すフェイルセーフ設計：

```python
_IMPORT_ERROR = None
try:
    from app.main import app as fastapi_app
except Exception as e:
    _IMPORT_ERROR = traceback.format_exc()
...
if fastapi_app is None:
    return func.HttpResponse(
        body=json.dumps({"error": "Service unavailable", "detail": _IMPORT_ERROR}),
        status_code=503,
    )
```

---

### 5-3. GCP Cloud Run (`function.py`)

Cloud Run は通常の HTTP サーバーとして動作するため、`uvicorn` でそのまま FastAPI を起動できる。Lambda や Azure Functions のような特殊なアダプターは必要ない。

`Dockerfile` で `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]` のような起動コマンドを指定するだけで Cloud Run 上で動作する。

---

## 6. フロントエンド（React SPA）

### 6-1. アーキテクチャ概要

`services/frontend_react/` に React 18 + Vite + TypeScript + Tailwind CSS で構築された SPA。
3クラウドすべてで**同一のビルド成果物**をオブジェクトストレージ（S3 / Blob Storage / GCS）に配置し、CDN で配信する。

`vite.config.ts` でビルド時のベースパスを `/sns/` に設定している（CDN の `/sns/*` パスにマッピングされるため）。

---

### 6-2. ルーティング (`App.tsx`)

```tsx
<AuthProvider>
  <Layout>
    <Routes>
      <Route path="/"              element={<HomePage />} />
      <Route path="/post/:postId"  element={<PostPage />} />
      <Route path="/profile"       element={<ProfilePage />} />
      <Route path="/login"         element={<LoginPage />} />
      <Route path="/auth/callback" element={<CallbackPage />} />
      <Route path="*"              element={<HomePage />} />
    </Routes>
  </Layout>
</AuthProvider>
```

`AuthProvider` が認証状態をアプリ全体に提供する（React Context パターン）。

---

### 6-3. API クライアント (`api/client.ts`)

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',  // 空文字 → Vite プロキシ経由でローカル API
  timeout: 15000,
});

// 全リクエストに JWT トークンを付与
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('id_token') || localStorage.getItem('access_token');
  if (token) config.headers['Authorization'] = `Bearer ${token}`;
  return config;
});
```

Cognito は `id_token`（audience が client_id と一致する）を優先して使う。`access_token` はフォールバック。

---

### 6-4. 認証設定 (`config/auth.ts`)

ビルド時の環境変数 `VITE_AUTH_PROVIDER` で認証プロバイダーを切り替える。

| `VITE_AUTH_PROVIDER` | 認証方式 |
| -------------------- | -------- |
| `aws`                | Cognito PKCE 認証コードフロー |
| `azure`              | Azure AD 暗黙的フロー（id_token フラグメント） |
| `firebase`           | Firebase SDK Google Sign-In（ポップアップ） |
| `none`               | 認証なし（ローカル開発） |

**AWS (Cognito) の PKCE フロー:**
1. `generateCodeVerifier()` でランダム文字列生成 → `sessionStorage` に保存
2. SHA-256 ハッシュ → base64url エンコード → `code_challenge`
3. Cognito 認証エンドポイントへリダイレクト
4. コールバック（`/auth/callback`）で `code` を受取り + `code_verifier` で検証 → token 取得

---

### 6-5. 認証コンテキスト (`contexts/AuthContext.tsx`)

`localStorage` にトークンを保存・読込し、`window` の `storage` イベントを監視することでタブ間でログイン状態を同期する。

```typescript
// タブ間同期
useEffect(() => {
  const onStorage = () => setToken(readToken());
  window.addEventListener("storage", onStorage);
  return () => window.removeEventListener("storage", onStorage);
}, []);
```

---

### 6-6. 主要コンポーネント

| コンポーネント  | 役割 |
| ------------- | ---- |
| `HomePage`    | 投稿一覧表示・タグフィルタ・キーワード検索・ページネーション（"もっと見る"） |
| `PostForm`    | 投稿作成フォーム（テキスト・マークダウン・画像複数枚・タグ） |
| `PostCard`    | 1件の投稿表示（マークダウン対応・画像ライトボックス） |
| `ProfilePage` | ニックネーム・自己紹介の表示と編集 |
| `LoginPage`   | 各クラウドの認証フローへのリダイレクト |
| `CallbackPage`| Cognito / Azure AD の認証コールバック処理・token 保存 |

---

### 6-7. 画像アップロードフロー

```
1. POST /uploads/presigned-urls  →  { urls: [{uploadUrl, key}] }
2. 各 uploadUrl に PUT（ブラウザから直接 S3/Blob/GCS へアップロード）
3. POST /posts { imageKeys: [key1, key2, ...] }  →  投稿作成
```

バックエンドを経由しないため、大容量画像でもバックエンドに負荷をかけない設計。アップロード上限は `GET /limits` で取得し、ハードコードしない。

---

## 7. ローカル開発環境

### 7-1. Docker Compose 構成

`docker-compose.yml` で以下の4サービスを起動する。

| サービス        | ポート | 用途 |
| -------------- | ------ | ---- |
| `api`          | 8000   | FastAPI（ホットリロード付き uvicorn） |
| `frontend_web` | 8080   | Python SSR フロントエンド（レガシー） |
| `dynamodb-local` | 8001 | DynamoDB Local（AWS 互換） |
| `minio`        | 9000/9001 | MinIO（S3 互換オブジェクトストレージ） |

**API サービスの環境変数（ローカル）:**

```yaml
CLOUD_PROVIDER=local
AUTH_DISABLED=true      # ローカルのみ許容
DYNAMODB_ENDPOINT=http://dynamodb-local:8000
DYNAMODB_TABLE_NAME=simple-sns-local
MINIO_ENDPOINT=http://minio:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:9000   # ブラウザからの直接アクセス用
```

`MINIO_ENDPOINT`（コンテナ内部 URL）と `MINIO_PUBLIC_ENDPOINT`（ブラウザからの URL）を分けることで、コンテナ内→MinIO の通信とブラウザ→MinIO の通信が両立する。

---

### 7-2. ローカル起動手順

```bash
cd /workspaces/multicloud-auto-deploy
docker compose up -d

# API の動作確認
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs

# MinIO コンソール（画像アップロード確認用）
open http://localhost:9001  # minioadmin / minioadmin
```

`services/api/app` ディレクトリが `docker-compose.yml` でコンテナにマウントされるため、ソース変更は即座にホットリロードで反映される。

---

### 7-3. データ初期化

`LocalBackend._init_dynamodb()` が初回起動時に DynamoDB Local へテーブルを自動作成する。手動でのテーブル作成は不要。

MinIO のバケットも同様に `LocalBackend._init_storage()` 内で自動作成する。

---

## まとめ：実装の核心パターン

| パターン | 実装箇所 | 説明 |
| -------- | -------- | ---- |
| **Strategy パターン** | `backends/` | `BackendBase` を実装するクラスをクラウドごとに差し替え |
| **Factory + LRU Cache** | `backends/__init__.py` | `get_backend()` で1回だけインスタンスを生成 |
| **Pydantic Settings** | `config.py` | 環境変数を型安全に管理、`AliasChoices` で名前揺れを吸収 |
| **Dual serialization** | `models.py` | camelCase と snake_case を同時に返してフロントエンド互換 |
| **JWKS キャッシュ** | `jwt_verifier.py` | 1時間キャッシュ、失敗時は期限切れキャッシュをフォールバック |
| **Presigned URL** | 各バックエンド | 画像をバックエンド経由せずブラウザから直接アップロード |
| **PKCE フロー** | `config/auth.ts` | AWS Cognito で認証コードフローを安全に実装 |

