# アーキテクチャダイアグラム

> マルチクラウド自動デプロイシステム全体の構造と関係図

---

## 1. 全体アーキテクチャフロー

デプロイから運用までの全体的なデータフローと責任分岐を示します。

```mermaid
graph TB
    subgraph "開発環境"
        DEV["📱 Developer Workstation"]
        GIT["📂 GitHub Repository"]
    end

    subgraph "CI/CD パイプライン"
        GHA["⚙️ GitHub Actions"]
        BUILD["🔨 Build & Test"]
        PUSH["📤 Push to Cloud"]
    end

    subgraph "AWS クラウド"
        AWS_API["Lambda API"]
        AWS_CDN["CloudFront CDN"]
        AWS_STORAGE["S3 Storage"]
        AWS_DB["DynamoDB"]
        AWS_AUTH["Cognito Auth"]
    end

    subgraph "Azure クラウド"
        AZURE_FUNC["Function App"]
        AZURE_CDN["Azure Front Door"]
        AZURE_STORAGE["Blob Storage"]
        AZURE_DB["Cosmos DB"]
        AZURE_AUTH["Azure AD"]
    end

    subgraph "GCP クラウド"
        GCP_RUN["Cloud Run"]
        GCP_CDN["Cloud CDN"]
        GCP_STORAGE["Cloud Storage"]
        GCP_DB["Firestore"]
        GCP_AUTH["Firebase Auth"]
    end

    subgraph "ユーザー層"
        USER["👥 ユーザー"]
        SNS["🎓 SNS 機能"]
        MATH["🔢 数式解答"]
    end

    DEV -->|git push| GIT
    GIT -->|webhook trigger| GHA
    GHA -->|build & test| BUILD
    BUILD -->|deploy| PUSH

    PUSH -->|Lambda code| AWS_API
    PUSH -->|React build| AWS_CDN
    PUSH -->|assets| AWS_STORAGE

    PUSH -->|Function code| AZURE_FUNC
    PUSH -->|React build| AZURE_CDN
    PUSH -->|assets| AZURE_STORAGE

    PUSH -->|Container| GCP_RUN
    PUSH -->|assets| GCP_STORAGE

    USER -->|access| SNS
    USER -->|solve math| MATH

    SNS -->|API call| AWS_API
    SNS -->|API call| AZURE_FUNC
    SNS -->|API call| GCP_RUN

    AWS_API -->|data| AWS_DB
    AWS_API -->|auth| AWS_AUTH
    AWS_CDN -->|static| AWS_STORAGE

    AZURE_FUNC -->|data| AZURE_DB
    AZURE_FUNC -->|auth| AZURE_AUTH
    AZURE_CDN -->|static| AZURE_STORAGE

    GCP_RUN -->|data| GCP_DB
    GCP_RUN -->|auth| GCP_AUTH
    GCP_CDN -->|static| GCP_STORAGE
```

---

## 2. セキュリティレイヤー

認証・認可・監視の多層防御を示します。

```mermaid
graph LR
    USER["👤 ユーザー"]

    subgraph "認証層 (Authentication)"
        AUTH_AWS["Cognito"]
        AUTH_AZURE["Azure AD"]
        AUTH_GCP["Firebase Auth"]
    end

    subgraph "認可層 (Authorization)"
        IAM_AWS["AWS IAM"]
        IAM_AZURE["Azure RBAC"]
        IAM_GCP["GCP IAM"]
    end

    subgraph "保護層 (Protection)"
        WAF_AWS["CloudFront WAF"]
        ARMOR["Cloud Armor"]
        HEADERS["Security Headers"]
    end

    subgraph "監視層 (Monitoring)"
        TRAIL["CloudTrail"]
        LOGS_AZURE["Log Analytics"]
        AUDIT["Cloud Audit Logs"]
    end

    USER -->|login| AUTH_AWS
    USER -->|login| AUTH_AZURE
    USER -->|login| AUTH_GCP

    AUTH_AWS -->|token| IAM_AWS
    AUTH_AZURE -->|token| IAM_AZURE
    AUTH_GCP -->|token| IAM_GCP

    IAM_AWS -->|enforce| WAF_AWS
    IAM_AZURE -->|enforce| ARMOR
    IAM_GCP -->|enforce| HEADERS

    WAF_AWS -->|log| TRAIL
    ARMOR -->|log| LOGS_AZURE
    HEADERS -->|log| AUDIT
```

---

## 3. デプロイ戦略（Pulumi Infrastructure as Code）

Pulumi を使用した 3 クラウドへの統一デプロイメント構造。

```mermaid
graph TB
    CODE["📝 Infrastructure Code"]

    subgraph "Pulumi Stack"
        PULUMI["Pulumi Core"]
        CONFIG["config.yaml"]
        SECRETS["secrets.yaml"]
    end

    subgraph "AWS Stack"
        AWS_RESOURCES["Lambda, S3, DynamoDB,<br/>CloudFront, IAM, etc."]
    end

    subgraph "Azure Stack"
        AZURE_RESOURCES["Function App, Blob Storage,<br/>Cosmos DB, Front Door, RBAC, etc."]
    end

    subgraph "GCP Stack"
        GCP_RESOURCES["Cloud Run, Cloud Storage,<br/>Firestore, Cloud CDN, IAM, etc."]
    end

    CODE -->|pulumi up| PULUMI
    CONFIG -->|stack config| PULUMI
    SECRETS -->|encrypted secrets| PULUMI

    PULUMI -->|create/update| AWS_RESOURCES
    PULUMI -->|create/update| AZURE_RESOURCES
    PULUMI -->|create/update| GCP_RESOURCES

    AWS_RESOURCES -->|state| PULUMI
    AZURE_RESOURCES -->|state| PULUMI
    GCP_RESOURCES -->|state| PULUMI
```

---

## 4. CI/CD パイプラインステージ

GitHub Actions による自動テストと段階的デプロイ。

```mermaid
graph LR
    PUSH["git push"]

    subgraph "Stage 1: Checkout & Build"
        CHECKOUT["Checkout Code"]
        LINT["Lint & Format Check"]
        BUILD["Build Artifacts"]
    end

    subgraph "Stage 2: Unit Tests"
        UNIT_PY["Python Unit Tests"]
        UNIT_JS["JavaScript Unit Tests"]
    end

    subgraph "Stage 3: Integration Tests"
        INT_AWS["AWS E2E Test"]
        INT_AZURE["Azure E2E Test"]
        INT_GCP["GCP E2E Test"]
    end

    subgraph "Stage 4: Deploy"
        DEP_AWS["Deploy to AWS staging"]
        DEP_AZURE["Deploy to Azure staging"]
        DEP_GCP["Deploy to GCP staging"]
    end

    subgraph "Stage 5: Smoke Tests"
        SMOKE["Health Checks"]
        VERIFY["Endpoint Verification"]
    end

    PUSH --> CHECKOUT
    CHECKOUT --> LINT
    LINT --> BUILD

    BUILD --> UNIT_PY
    BUILD --> UNIT_JS

    UNIT_PY --> INT_AWS
    UNIT_JS --> INT_AZURE
    INT_AWS --> INT_GCP
    INT_AZURE --> INT_GCP

    INT_GCP --> DEP_AWS
    INT_GCP --> DEP_AZURE
    INT_GCP --> DEP_GCP

    DEP_AWS --> SMOKE
    DEP_AZURE --> SMOKE
    DEP_GCP --> VERIFY

    SMOKE -->|✅ Pass| COMPLETE["✅ Ready for Production"]
    VERIFY -->|✅ Pass| COMPLETE
```

---

## 5. 権限とロール分離（IAM/RBAC）

最小権限の法則に基づいた権限構造。

```mermaid
graph TD
    subgraph "ユーザーロール"
        ADMIN["👤 管理者<br/>(Administrator)"]
        DEPLOY["👤 デプロイユーザー<br/>(satoshi)"]
        READONLY["👤 読み取り専用<br/>(Viewer)"]
    end

    subgraph "AWS 権限"
        AWS_ADMIN["IAM: Administrator"]
        AWS_DEPLOY["IAM: DeploymentPolicy"]
        AWS_READ["IAM: ReadOnly"]
    end

    subgraph "Azure 権限"
        AZURE_ADMIN["RBAC: Owner"]
        AZURE_DEPLOY["RBAC: Contributor"]
        AZURE_READ["RBAC: Reader"]
    end

    subgraph "GCP 権限"
        GCP_ADMIN["IAM: Editor"]
        GCP_DEPLOY["IAM: Service Account Key User"]
        GCP_READ["IAM: Viewer"]
    end

    ADMIN -->|assigned| AWS_ADMIN
    ADMIN -->|assigned| AZURE_ADMIN
    ADMIN -->|assigned| GCP_ADMIN

    DEPLOY -->|assigned| AWS_DEPLOY
    DEPLOY -->|assigned| AZURE_DEPLOY
    DEPLOY -->|assigned| GCP_DEPLOY

    READONLY -->|assigned| AWS_READ
    READONLY -->|assigned| AZURE_READ
    READONLY -->|assigned| GCP_READ

    AWS_ADMIN -.->|can assign| AWS_DEPLOY
    AZURE_ADMIN -.->|can assign| AZURE_DEPLOY
    GCP_ADMIN -.->|can assign| GCP_DEPLOY
```

---

## 6. データモデルと API フロー

SNS 投稿の生成から取得・画像処理までのデータフロー。

```mermaid
graph TB
    USER["👤 ユーザー"]

    subgraph "API レイヤー"
        POST_API["POST /posts"]
        GET_POSTS["GET /posts"]
        UPLOAD_API["PUT /posts/:id/image"]
    end

    subgraph "ビジネスロジック"
        VALIDATE["入力検証"]
        ENCRYPT["暗号化"]
        IMAGE_GEN["画像生成"]
    end

    subgraph "ストレージレイヤー"
        POSTS_DB["Posts Table<br/>(AWS/Azure/GCP)"]
        IMAGE_STORE["Image Storage<br/>(S3/Blob/GCS)"]
        CACHE["キャッシュ<br/>(CloudFront/AFD/CDN)"]
    end

    USER -->|POST| POST_API
    USER -->|GET| GET_POSTS
    USER -->|PUT| UPLOAD_API

    POST_API --> VALIDATE
    VALIDATE --> ENCRYPT
    ENCRYPT --> POSTS_DB

    UPLOAD_API --> IMAGE_GEN
    IMAGE_GEN --> IMAGE_STORE
    IMAGE_STORE --> CACHE

    POSTS_DB -->|fetch| GET_POSTS
    CACHE -->|serve| USER
    GET_POSTS -->|return| USER
```

---

## 7. インシデント対応フロー

本番環境のトラブルシューティングとロールバック手順。

```mermaid
graph LR
    INCIDENT["🚨 インシデント<br/>検出"]

    subgraph "検出フェーズ"
        MONITOR["モニタリング<br/>(CloudWatch/Monitor/Logging)"]
        ALERT["アラート<br/>通知"]
    end

    subgraph "調査フェーズ"
        LOGS["ログ分析"]
        TRACE["分散トレース"]
        ROOT_CAUSE["根本原因<br/>特定"]
    end

    subgraph "対応フェーズ"
        DECIDE{修正方法<br/>の選択}
        HOTFIX["ホットフィックス<br/>デプロイ"]
        ROLLBACK["ロールバック<br/>実行"]
    end

    subgraph "検証フェーズ"
        SMOKE_TEST["スモークテスト"]
        HEALTH_CHECK["ヘルスチェック"]
        VERIFY["機能検証"]
    end

    subgraph "事後処理"
        POSTMORTEM["ポストモーテム<br/>作成"]
        DOCS["ドキュメント<br/>更新"]
        MONITORING["監視ルール<br/>強化"]
    end

    INCIDENT --> MONITOR
    MONITOR --> ALERT
    ALERT --> LOGS
    LOGS --> TRACE
    TRACE --> ROOT_CAUSE

    ROOT_CAUSE --> DECIDE
    DECIDE -->|軽微な修正| HOTFIX
    DECIDE -->|重大な問題| ROLLBACK

    HOTFIX --> SMOKE_TEST
    ROLLBACK --> SMOKE_TEST
    SMOKE_TEST --> HEALTH_CHECK
    HEALTH_CHECK --> VERIFY

    VERIFY -->|✅ OK| POSTMORTEM
    POSTMORTEM --> DOCS
    DOCS --> MONITORING
```

---

## 8. マルチクラウド冗長性戦略

3 つのクラウドプロバイダーにおける同時運用と災害復旧。

```mermaid
graph TB
    USER["👥 ユーザー"]

    subgraph "プライマリ層"
        PRIMARY["🟢 Primary Region<br/>(ap-northeast-1)"]
    end

    subgraph "セカンダリ層"
        SEC_AWS["🟡 AWS Staging"]
        SEC_AZURE["🟡 Azure Staging"]
        SEC_GCP["🟡 GCP Staging"]
    end

    subgraph "フェイルオーバー戦略"
        HEALTH["ヘルスチェック"]
        SWITCH["自動フェイルオーバー"]
        NOTIFY["チーム通知"]
    end

    subgraph "復旧プロセス"
        BACKUP["バックアップ<br/>復元"]
        VERIFY["データ同期<br/>確認"]
        RESTORE["本番復帰"]
    end

    USER -->|Normal| PRIMARY
    PRIMARY -->|replication| SEC_AWS
    PRIMARY -->|replication| SEC_AZURE
    PRIMARY -->|replication| SEC_GCP

    PRIMARY -->|health| HEALTH
    HEALTH -->|failure| SWITCH
    SWITCH -->|route to| SEC_AWS
    SWITCH -->|route to| SEC_AZURE
    SWITCH -->|route to| SEC_GCP
    SWITCH --> NOTIFY

    SEC_AWS -->|detected downtime| BACKUP
    SEC_AZURE -->|detected downtime| BACKUP
    SEC_GCP -->|detected downtime| BACKUP

    BACKUP --> VERIFY
    VERIFY --> RESTORE
    RESTORE --> PRIMARY
```

---

## 参照

- [AI_AGENT_02_ARCHITECTURE.md](AI_AGENT_02_ARCHITECTURE.md) — 詳細アーキテクチャ
- [AI_AGENT_04_INFRA.md](AI_AGENT_04_INFRA.md) — インフラストラクチャ設定
- [AI_AGENT_05_CICD.md](AI_AGENT_05_CICD.md) — CI/CD パイプライン詳細
- [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md) — 運用手順書
- [AI_AGENT_08_SECURITY.md](AI_AGENT_08_SECURITY.md) — セキュリティ設定
