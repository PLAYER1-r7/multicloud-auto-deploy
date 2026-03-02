# データモデル・API・トラブルシューティングダイアグラム

> データベーススキーマ、API フロー、問題診断フローチャートを可視化

---

## 1. データベーススキーマ（3 クラウド共통）

マルチクラウド環境での データモデル設計。

```mermaid
graph TB
    subgraph "User Table"
        USER_ENTITY["👤 User<br/>├─ userId (PK)<br/>├─ email<br/>├─ displayName<br/>├─ profilePictureUrl<br/>├─ createdAt<br/>├─ updatedAt<br/>└─ deletedAt (soft delete)"]
    end

    subgraph "Post / SNS Table"
        POST_ENTITY["📝 Post<br/>├─ postId (PK)<br/>├─ userId (FK)<br/>├─ title<br/>├─ content<br/>├─ tags (JSON array)<br/>├─ likes (count)<br/>├─ createdAt<br/>├─ updatedAt<br/>└─ deletedAt (soft delete)"]
    end

    subgraph "Image Metadata Table"
        IMAGE_ENTITY["🖼️ Image<br/>├─ imageId (PK)<br/>├─ postId (FK)<br/>├─ s3Key / blobPath / gcsPath<br/>├─ contentType<br/>├─ size<br/>├─ width / height<br/>├─ ocr_text<br/>├─ presigned_url<br/>├─ expiresAt<br/>├─ uploadedAt<br/>└─ deletedAt"]
    end

    subgraph "MathSolver Table"
        MATH_ENTITY["🔢 MathProblem<br/>├─ problemId (PK)<br/>├─ imageId (FK)<br/>├─ ocrConfidence<br/>├─ latex_formula<br/>├─ solution_steps (JSON)<br/>├─ answer<br/>├─ solver_provider (AWS/Azure/GCP)<br/>├─ processingTimeMs<br/>├─ createdAt<br/>└─ expiresAt (90 days)"]
    end

    subgraph "Session / Cache Table"
        SESSION_ENTITY["🔑 Session<br/>├─ sessionId (PK)<br/>├─ userId (FK)<br/>├─ tokenHash<br/>├─ provider (cognito/azuread/firebase)<br/>├─ expiresAt<br/>├─ refreshToken<br/>├─ deviceFingerprint<br/>└─ ipAddress"]
    end

    subgraph "Audit Log"
        AUDIT_ENTITY["📋 AuditLog<br/>├─ logId (PK)<br/>├─ userId (FK)<br/>├─ action (create/read/update/delete)<br/>├─ resourceType<br/>├─ resourceId<br/>├─ changes (JSON)<br/>├─ ipAddress<br/>├─ userAgent<br/>└─ timestamp"]
    end

    USER_ENTITY -->|owns| POST_ENTITY
    POST_ENTITY -->|contains| IMAGE_ENTITY
    IMAGE_ENTITY -->|solves via| MATH_ENTITY
    USER_ENTITY -->|has| SESSION_ENTITY
    USER_ENTITY -->|logged in| AUDIT_ENTITY
    POST_ENTITY -->|logged in| AUDIT_ENTITY
    IMAGE_ENTITY -->|logged in| AUDIT_ENTITY
```

---

## 2. API エンドポイントマップ

全 SNS・数式・認証 API の操作一覧。

```mermaid
graph TB
    subgraph "認証 API （Auth Provider 経由）"
        AUTH["🔐 /auth<br/>├─ GET /auth/callback (OAuth callback)<br/>├─ POST /auth/logout<br/>├─ POST /auth/refresh<br/>└─ GET /auth/user (current user)"]
    end

    subgraph "投稿・SNS API"
        POST["📝 /posts<br/>├─ GET /posts (list, paginated)<br/>├─ GET /posts/:id (single)<br/>├─ POST /posts (create)<br/>├─ PATCH /posts/:id (update)<br/>├─ DELETE /posts/:id (soft delete)<br/>├─ POST /posts/:id/like (toggle)<br/>└─ GET /posts/search (full-text)"]
    end

    subgraph "画像アップロード API"
        IMAGE["🖼️ /posts/:id/image<br/>├─ GET /posts/:id/images (list)<br/>├─ PUT /posts/:id/image<br/>│ ├─ Returns: presigned URL<br/>│ └─ Client side: PUT to S3/Blob/GCS<br/>├─ DELETE /posts/:id/image/:imageId<br/>└─ GET /posts/:id/image/:imageId<br/>   (served from CDN)"]
    end

    subgraph "数学解答 API"
        MATH["🔢 /v1/solve<br/>├─ POST /v1/solve<br/>│ ├─ Input: image (URL or Base64)<br/>│ ├─ Returns: OCR + LaTeX + steps<br/>│ └─ Backend: AWS Textract / Azure Vision API / GCP Vision<br/>├─ GET /v1/solve/:problemId (cached result)<br/>└─ DELETE /v1/solve/:problemId"]
    end

    subgraph "ユーザー管理 API"
        USER["👤 /users<br/>├─ GET /users/:userId<br/>├─ PATCH /users/:userId (update profile)<br/>├─ DELETE /users/:userId<br/>├─ GET /users/:userId/posts<br/>└─ POST /users/:userId/avatar (upload)"]
    end

    subgraph "管理・診断 API"
        ADMIN["⚙️ /admin<br/>├─ GET /admin/health<br/>├─ GET /admin/metrics<br/>├─ GET /admin/logs<br/>└─ POST /admin/cleanup (maintenance)"]
    end

    AUTH ---|protect| POST
    POST ---|owns| IMAGE
    IMAGE ---|analyze| MATH
    USER ---|manage| IMAGE
    ADMIN ---|monitor| POST
```

---

## 3. POST・画像アップロード フロー

フロントエンドからサーバー、クラウドストレージへのデータフロー。

```mermaid
graph LR
    FE["🌐 Frontend<br/>(React SPA)"]

    subgraph "Step 1: ユーザー作成"
        FE1["📝 POST /posts<br/>title, content, tags"]
        BE1["🏠 Backend<br/>1. Validate input<br/>2. Encrypt content<br/>3. Save to DB<br/>4. Return postId"]
    end

    subgraph "Step 2: 画像選択・プレビュー"
        FE2["🖼️ User selects<br/>image file<br/>(JPG/PNG)"]
        FE3["✅ Client validation<br/>- Size < 10MB<br/>- Dimension check<br/>- Format verify"]
    end

    subgraph "Step 3: 署名付き URL 取得"
        FE4["🔐 PUT /posts/:id/image<br/>(metadata only)"]
        BE3["🏠 Backend<br/>1. Generate imageId<br/>2. Create presigned URL<br/>3. Return upload URL"]
        BE4["☁️ Cloud KMS<br/>Sign the URL<br/>(valid 15 min)"]
    end

    subgraph "Step 4: 直接クラウドアップロード"
        FE5["📤 PUT to<br/>S3 / Blob / GCS<br/>(presigned URL)"]
        S3["☁️ Cloud Storage<br/>- Verify signature<br/>- Store file<br/>- Trigger resize"]
    end

    subgraph "Step 5: OCR・画像処理"
        PROCESS["🔬 Async Job<br/>(SQS / Service Bus /<br/>Pub/Sub)"]
        OCR["🔍 OCR Analysis<br/>- Textract (AWS)<br/>- Vision API (Azure/GCP)<br/>- Extract text"]
        RESIZE["📏 Image Resize<br/>- Thumbnail: 200x200<br/>- Medium: 800x600<br/>- Web-optimized"]
    end

    subgraph "Step 6: URL & 返却"
        CDN["🌐 CDN Cache<br/>- CloudFront<br/>- Front Door<br/>- Cloud CDN"]
        FE6["✅ GET /posts/:id<br/>receives<br/>imageUrls[]<br/>(CDN URLs)"]
    end

    FE --> FE1
    FE1 --> BE1
    BE1 -->|postId| FE

    FE --> FE2
    FE2 --> FE3

    FE3 --> FE4
    FE4 --> BE3
    BE3 --> BE4
    BE4 -->|presigned URL| FE

    FE -->|browser PUT| FE5
    FE5 --> S3

    S3 -->|event trigger| PROCESS
    PROCESS --> OCR
    PROCESS --> RESIZE

    OCR -->|store metadata| BE3
    RESIZE -->|store variants| S3

    S3 --> CDN
    CDN --> FE6
```

---

## 4. トラブルシューティング決定ツリー

エラー症状から原因特定・解決までの診断フロー。

```mermaid
graph TD
    START["🚨 問題報告<br/>出現"]

    Q1["Web サイト<br/>にアクセス<br/>できる？"]

    Q1_YES["✅ YES"]
    Q1_NO["❌ NO"]

    Q2["API エンドポイント<br/>は応答<br/>している？"]

    Q2_YES["✅ YES"]
    Q2_NO["❌ NO"]

    Q3["認証（ログイン）<br/>成功した？"]

    Q3_YES["✅ YES"]
    Q3_NO["❌ NO"]

    Q4["データベース<br/>接続<br/>可能？"]

    Q4_YES["✅ YES"]
    Q4_NO["❌ NO"]

    Q5["CloudWatch<br/>/Monitor<br/>エラーログ<br/>あり？"]

    Q5_YES["✅ YES"]
    Q5_NO["❌ NO"]

    START --> Q1

    Q1 --> Q1_NO
    Q1 --> Q1_YES

    Q1_NO -->|→| DNS["🔍 DNS 確認<br/>nslookup domain.com<br/>→ CloudFront / AFD / Cloud CDN<br/>確認"]
    DNS -->|問題| CERT["🔒 SSL 証明書<br/>確認<br/>curl -v https://..."]
    CERT -->|失敗| CONTACT["📞 クラウド<br/>プロバイダに<br/>問い合わせ"]

    Q1_YES --> Q2

    Q2_NO -->|→| GATEWAY["🚪 API Gateway<br/>ステータス確認<br/>AWS API Gateway<br/>Azure API App<br/>GCP API Gateway"]
    GATEWAY -->|DOWN| LAMBDA["⚡ Lambda/<br/>Function App/<br/>Cloud Run<br/>状態確認"]
    LAMBDA -->|ERROR| LOGS1["📋 ログ確認<br/>CloudWatch Logs"]

    Q2_YES --> Q3

    Q3_NO -->|→| AUTH_ERR["🔐 認証エラー<br/>- Cognito / Azure AD<br/>/ Firebase<br/>状態確認<br/>- CORS 設定確認<br/>- Token 有効期限<br/>確認"]
    AUTH_ERR -->|CORS| CORS["🌐 CORS ヘッダー<br/>確認<br/>curl -H 'Origin: ...'"]

    Q3_YES --> Q4

    Q4_NO -->|→| DB_CONN["🗄️ DB 接続失敗<br/>- Connection string<br/>確認<br/>- VPC / Network<br/>確認<br/>- 認証情報確認"]
    DB_CONN -->|VPC| SECURITY["🔒 セキュリティ<br/>グループ確認<br/>- Inbound rules<br/>- Firewall rules"]

    Q4_YES --> Q5

    Q5_YES -->|→| ANALYZE["🔍 ログ分析<br/>- Error type<br/>- Stack trace<br/>- Request context"]
    ANALYZE -->|ROOT CAUSE| FIX["🔧 修正<br/>- Hotfix deploy<br/>- または<br/>- Configuration<br/>change"]

    Q5_NO -->|→| TRACE["📊 分散トレース<br/>(X-Ray / Insights /<br/>Cloud Trace)<br/>フロー確認"]
    TRACE -->|BOTTLENECK| PERF["⚡ パフォーマンス<br/>最適化<br/>- インデックス<br/>- キャッシュ<br/>-並列化"]
```

---

## 5. キャッシュ戦略

CDN・DB キャッシュと無効化戦略。

```mermaid
graph TB
    USER["👥 ユーザー"]

    subgraph "Layer 1: ブラウザキャッシュ"
        BROWSER["🌐 Browser Cache<br/>- Cache-Control header<br/>- ETag / Last-Modified<br/>- Max-age"]
    end

    subgraph "Layer 2: CDN スーパーキャッシュ"
        CDN_CACHE["⚡ CloudFront / AFD /<br/>Cloud CDN<br/>- Static assets: 365 days<br/>- API responses: 5 min<br/>- User-specific: no-cache"]
    end

    subgraph "Layer 3: アプリ層キャッシュ"
        APP_CACHE["💾 In-memory Cache<br/>(Redis / Memcache)<br/>- User data: 1h<br/>- Post list: 5 min<br/>- Computed values: 30 min"]
    end

    subgraph "Layer 4: DB クエリキャッシュ"
        DB_CACHE["🗄️ Database<br/>- Query result cache<br/>- Connection pooling<br/>- Prepared statements"]
    end

    subgraph "無効化戦略"
        INVALIDATE["🗑️ Cache Invalidation<br/>- Time-based (TTL)<br/>- Event-based (on update)<br/>- Manual purge"]
        SOFT_PURGE["🧹 Soft purge<br/>(max-age reset)"]
        HARD_PURGE["💣 Hard purge<br/>(full delete)"]
    end

    USER --> BROWSER
    BROWSER -->|miss| CDN_CACHE
    CDN_CACHE -->|miss| APP_CACHE
    APP_CACHE -->|miss| DB_CACHE

    DB_CACHE -->|update| INVALIDATE
    INVALIDATE --> SOFT_PURGE
    INVALIDATE --> HARD_PURGE
```

---

## 6. エラーレート & SLA 監視

パフォーマンス指標と可用性 SLA。

```mermaid
graph TB
    subgraph "主要メトリクス"
        LATENCY["⏱️ Latency<br/>- P50: < 100ms<br/>- P95: < 500ms<br/>- P99: < 2s"]
        ERROR["❌ Error Rate<br/>- 5xx: < 0.1%<br/>- 4xx: < 1%<br/>- Timeout: < 0.05%"]
        THROUGHPUT["🔄 Throughput<br/>- RPS: 1000/sec<br/>- Sustained: 500/sec<br/>- Peak: 2000/sec"]
    end

    subgraph "可用性 SLA"
        SLA99["99% Uptime<br/>= 43.8 分/月<br/>downtime"]
        SLA999["99.9% Uptime<br/>= 4.38 分/月"]
        SLA9999["99.99% Uptime<br/>= 26.3 秒/月<br/>(Business Critical)"]
    end

    subgraph "監視アラート"
        ALERT_HIGH["🔴 P99 > 2s → SEV2"]
        ALERT_MED["🟡 Error > 0.5% → SEV3"]
        ALERT_LOW["🟢 Warning threshold"]
    end

    subgraph "対応 SLA"
        DETECT_SLA["🚨 Detection: < 1 min"]
        ACK_SLA["📢 Acknowledge: < 5 min"]
        MITIGATE_SLA["⚡ Mitigate: < 15min (SEV1)"]
        RESOLVE_SLA["✅ Resolve: < 4h (SEV2)"]
    end

    LATENCY --> SLA99
    ERROR --> SLA999
    THROUGHPUT --> SLA9999

    SLA99 --> ALERT_HIGH
    SLA999 --> ALERT_MED
    SLA9999 --> ALERT_LOW

    ALERT_HIGH --> DETECT_SLA
    ALERT_MED --> DETECT_SLA

    DETECT_SLA --> ACK_SLA
    ACK_SLA --> MITIGATE_SLA
    MITIGATE_SLA --> RESOLVE_SLA
```

---

## 7. ロードバランシング・スケーリング

マルチリージョン・マルチプロバイダへのトラフィック分散。

```mermaid
graph TB
    USERS["👥 Global Users"]

    subgraph "DNS ロードバランシング"
        GLOBAL_DNS["🌍 Route53 / Azure DNS /<br/>Cloud DNS<br/>- Geo-routing<br/>- Latency-based<br/>- Failover"]
    end

    subgraph "AWS リージョン"
        AWS_ALB["🚪 Application Load Balancer<br/>(ap-northeast-1)"]
        AWS_ASG["📈 Auto Scaling Group<br/>Lambda: Auto-scale<br/>Target: 70% utilization"]
        AWS_RDS["🗄️ RDS Aurora<br/>(Read replicas)"]
    end

    subgraph "Azure リージョン"
        AZURE_AFD["🚪 Azure Front Door<br/>(Global edge)"]
        AZURE_VMSS["📈 Virtual Machine<br/>Scale Set<br/>Target: 75% CPU"]
        AZURE_COSMOS["🗄️ Cosmos DB<br/>(Multi-region)"]
    end

    subgraph "GCP リージョン"
        GCP_LB["🚪 Load Balancer<br/>(Global)"]
        GCP_MIG["📈 Managed Instance<br/>Group<br/>Target: 60% CPU"]
        GCP_FIRESTORE["🗄️ Firestore<br/>(Distributed)"]
    end

    subgraph "スケーリング ポリシー"
        SCALE_UP["📈 Scale Up<br/>- CPU > threshold<br/>- Latency > SLA<br/>- Queue depth"]
        SCALE_DOWN["📉 Scale Down<br/>- CPU < 30%<br/>- No requests<br/>- Off-peak hours"]
    end

    USERS --> GLOBAL_DNS
    GLOBAL_DNS -->|route| AWS_ALB
    GLOBAL_DNS -->|route| AZURE_AFD
    GLOBAL_DNS -->|route| GCP_LB

    AWS_ALB --> AWS_ASG
    AZURE_AFD --> AZURE_VMSS
    GCP_LB --> GCP_MIG

    AWS_ASG --> AWS_RDS
    AZURE_VMSS --> AZURE_COSMOS
    GCP_MIG --> GCP_FIRESTORE

    AWS_ASG -->|trigger| SCALE_UP
    SCALE_UP -->|more capacity| SCALE_DOWN
```

---

## 参照

- [AI_AGENT_03_API.md](AI_AGENT_03_API.md) — API 仕様詳細
- [AI_AGENT_12_OCR_MATH.md](AI_AGENT_12_OCR_MATH.md) — 数学解答 API
- [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) — 環境ステータス・トラブルシューティング
- [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md) — 運用ハンドブック
