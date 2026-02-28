# セキュリティ・コンプライアンスダイアグラム

> マルチクラウド環境のセキュリティ体制、脅威モデル、コンプライアンス要件を可視化

---

## 1. セキュリティディフェンスレイヤー（Defense in Depth）

多層防御の構造。

```mermaid
graph TB
    USER["👤 ユーザー"]

    subgraph "レイヤー 1: ネットワークエッジ"
        DDoS["🛡️ DDoS Protection<br/>- AWS Shield<br/>- Azure DDoS Protection<br/>- Cloud Armor"]
        GEO["🌍 地域制限<br/>ブロック"]
    end

    subgraph "レイヤー 2: API ゲートウェイ"
        API_ENDPOINT["🚪 API Endpoint<br/>- CloudFront / AFD / CDN"]
        WAF["🔒 Web Application Firewall<br/>- AWS WAF<br/>- Cloud Armor<br/>- SQL インジェクション検知"]
        RATE_LIMIT["⏱️ Rate Limiting<br/>- 1000 req/min per IP<br/>- Token bucket algorithm"]
    end

    subgraph "レイヤー 3: 認証認可"
        AUTH["🔐 認証<br/>- OAuth2 + PKCE<br/>- AWS Cognito<br/>- Azure AD<br/>- Firebase Auth"]
        AUTHZ["🔑 認可・権限管理<br/>- IAM / RBAC<br/>- 最小権限の法則<br/>- セッション検証"]
    end

    subgraph "レイヤー 4: アプリケーション"
        INPUT["✅ 入力検証<br/>- SQL インジェクション対策<br/>- XSS 対策<br/>- CSRF 対策"]
        ENCRYPT["🔒 データ暗号化<br/>- TLS 1.2+<br/>- AES-256 at rest"]
        LOGGING["📝 ロギング<br/>- すべての API 呼び出し記録<br/>- 監査証跡"]
    end

    subgraph "レイヤー 5: データ保護"
        DB_ENC["🔐 DB 暗号化<br/>- AWS: SSE-S3<br/>- Azure: SSE<br/>- GCP: Google Cloud KMS"]
        BACKUP["💾 バックアップ<br/>- ポイントインタイムリカバリ<br/>- オフサイト複製"]
    end

    subgraph "レイヤー 6: 監視・検知"
        DETECT["🔍 脅威検知<br/>- Intrusion Detection<br/>- Anomaly Detection<br/>- Behavioral Analysis"]
        RESPOND["📢 インシデント対応<br/>- アラート<br/>- ロギング<br/>- 自動隔離"]
    end

    USER --> DDoS
    DDoS --> GEO
    GEO --> API_ENDPOINT
    API_ENDPOINT --> WAF
    WAF --> RATE_LIMIT

    RATE_LIMIT --> AUTH
    AUTH --> AUTHZ

    AUTHZ --> INPUT
    INPUT --> ENCRYPT
    ENCRYPT --> LOGGING

    LOGGING --> DB_ENC
    DB_ENC --> BACKUP

    BACKUP --> DETECT
    DETECT --> RESPOND
```

---

## 2. IAM 権限マトリックス（詳細版）

ユーザータイプ別の権限分布。

```mermaid
graph TB
    subgraph "ユーザーカテゴリ"
        ADMIN["👤 管理者<br/>(administrator)"]
        DEPLOY["👤 デプロイユーザー<br/>(satoshi)"]
        BACKEND["👤 バックエンド開発者"]
        FRONTEND["👤 フロントエンド開発者"]
        VIEWER["👤 読み取り専用<br/>(viewer)"]
    end

    subgraph "AWS IAM 権限"
        AWS_ADMIN["💼 AdministratorAccess<br/>- すべてのリソース操作"]
        AWS_DEPLOY["📦 DeploymentPolicy<br/>- Lambda 更新<br/>- S3 アップロード<br/>- CloudFront 無効化"]
        AWS_BACKEND["⚙️ Backend Developer<br/>- Lambda 関数ログ読み取り<br/>- DynamoDB クエリ<br/>- CloudWatch 表示"]
        AWS_FRONTEND["💻 Frontend Developer<br/>- S3 バケット読み取り<br/>- CloudFront キャッシュ"]
        AWS_READ["👀 ReadOnlyAccess"]
    end

    subgraph "Azure RBAC"
        AZURE_ADMIN["💼 Owner<br/>- すべてのリソース管理"]
        AZURE_DEPLOY["📦 Contributor<br/>- Function App 更新<br/>- リソース作成制限あり"]
        AZURE_BACKEND["⚙️ Function App<br/>Contributor"]
        AZURE_FRONTEND["💻 Blob Storage<br/>Data Contributor"]
        AZURE_READ["👀 Reader"]
    end

    subgraph "GCP IAM"
        GCP_ADMIN["💼 Editor<br/>- すべてのサービス管理"]
        GCP_DEPLOY["📦 Service Account<br/>Key User<br/>- Cloud Run Deploy"]
        GCP_BACKEND["⚙️ Cloud Run Developer"]
        GCP_FRONTEND["💻 Storage Object<br/>Viewer"]
        GCP_READ["👀 Viewer"]
    end

    ADMIN --> AWS_ADMIN
    ADMIN --> AZURE_ADMIN
    ADMIN --> GCP_ADMIN

    DEPLOY --> AWS_DEPLOY
    DEPLOY --> AZURE_DEPLOY
    DEPLOY --> GCP_DEPLOY

    BACKEND --> AWS_BACKEND
    BACKEND --> AZURE_BACKEND
    BACKEND --> GCP_BACKEND

    FRONTEND --> AWS_FRONTEND
    FRONTEND --> AZURE_FRONTEND
    FRONTEND --> GCP_FRONTEND

    VIEWER --> AWS_READ
    VIEWER --> AZURE_READ
    VIEWER --> GCP_READ
```

---

## 3. 認証フロー（OAuth2 + PKCE）

ユーザーログインと トークン取得の詳細なシーケンス。

```mermaid
graph LR
    CLIENT["🌐 SPA アプリ<br/>(ブラウザ)"]
    PROVIDER["🔐 ID Provider<br/>(Cognito / Azure AD /<br/>Firebase Auth)"]
    BACKEND["🏠 バックエンド API"]

    CLIENT -->|1. Generate<br/>code_verifier| CLIENT
    CLIENT -->|2. SHA256(verifier)<br/>→ code_challenge| CLIENT
    CLIENT -->|3. Redirect to<br/>/auth/authorize<br/>?challenge=...| PROVIDER

    PROVIDER -->|4. User login<br/>& consent| PROVIDER
    PROVIDER -->|5. Return<br/>authorization_code| CLIENT

    CLIENT -->|6. Exchange<br/>code + verifier<br/>for token| PROVIDER
    CLIENT -->|7. Validate<br/>verifier = SHA256<br/>of original| PROVIDER
    PROVIDER -->|8. Return<br/>access_token<br/>+ refresh_token| CLIENT

    CLIENT -->|9. Store in<br/>sessionStorage| CLIENT
    CLIENT -->|10. Call API<br/>with Bearer token| BACKEND
    BACKEND -->|11. Verify token<br/>signature & expiry| BACKEND
    BACKEND -->|12. Return<br/>protected resource| CLIENT

    BACKEND -->|13. Token expired?<br/>Use refresh_token| PROVIDER
    PROVIDER -->|14. Return new<br/>access_token| BACKEND
```

---

## 4. パスワードレス認証とデバイス信頼

多要素認証（MFA）とデバイス管理。

```mermaid
graph TB
    USER["👤 ユーザー"]

    subgraph "認証方式の選択"
        PASSWORD["📧 従来型：<br/>Email + Password<br/>（非推奨 - 廃止予定）"]
        PASSWORDLESS["🔐 推奨：<br/>パスワードレス認証"]
    end

    subgraph "パスワードレスフロー"
        EMAIL["1️⃣ Email 入力"]
        MAGIC["2️⃣ Magic Link<br/>メール送信"]
        CLICK["3️⃣ リンククリック"]
        SESSION["4️⃣ セッション<br/>確立"]
    end

    subgraph "MFA（多要素認証）"
        TOTP["📱 Time-based OTP<br/>(Google Authenticator)"]
        SMS["📲 SMS コード<br/>(E.164 format)"]
        PUSH["🔔 Push Notification<br/>(Mobile app)"]
    end

    subgraph "デバイス信頼管理"
        TRUST["✅ デバイス信頼の記録<br/>- フィンガープリント<br/>- User-Agent<br/>- IP アドレス"]
        RISK["⚠️ 異常検知<br/>- 新しいデバイス → MFA 強制<br/>- 異なる国からアクセス → alert<br/>- 多数同時セッション → block"]
    end

    USER --> PASSWORD
    USER --> PASSWORDLESS

    PASSWORDLESS --> EMAIL
    EMAIL --> MAGIC
    MAGIC --> CLICK
    CLICK --> SESSION

    SESSION --> TOTP
    SESSION --> SMS
    SESSION --> PUSH

    SESSION --> TRUST
    TRUST --> RISK
```

---

## 5. データ暗号化とキー管理

ステータ・イン・トランジット・アット・レストの暗号化戦略。

```mermaid
graph TB
    subgraph "データ分類"
        PUBLIC["🟢 公開<br/>静的ドキュメント<br/>キャッシュ可能"]
        PROTECTED["🟡 保護<br/>ユーザープロフィール<br/>投稿内容<br/>画像メタデータ"]
        SENSITIVE["🔴 機密<br/>パスワードハッシュ<br/>認証トークン<br/>個人情報"]
    end

    subgraph "暗号化 - 転送中（In Transit）"
        TRANSIT["🔐 TLS 1.2+<br/>- HTTPS everywhere<br/>- Cipher: AES-256-GCM<br/>- Certificate: ACM (AWS)<br/>- HSTS: 1 year"]
    end

    subgraph "暗号化 - 保管中（At Rest）"
        KMS["🔑 Key Management<br/>- AWS KMS<br/>- Azure Key Vault<br/>- GCP Cloud KMS"]
        DB_ENC["🗄️ Database<br/>- Default: SSE<br/>- Sensitive: Customer KMS"]
        STORAGE["💾 Object Storage<br/>- S3: SSE-S3 or SSE-KMS<br/>- Blob: SSE<br/>- GCS: Google-managed"]
    end

    subgraph "キーローテーション"
        ROTATE["🔄 定期ローテーション<br/>- Annual: CMK（カスタマー管理）<br/>- Automatic: AWS managed<br/>- Emergency: On-demand"]
    end

    subgraph "アクセス制御"
        IAM["🔐 IAM ポリシー<br/>- 最小権限<br/>- リソース別ポリシー<br/>- VPC Endpoint (private)"]
    end

    PUBLIC --> TRANSIT
    PROTECTED --> TRANSIT
    SENSITIVE --> TRANSIT

    TRANSIT --> KMS

    PUBLIC --> STORAGE
    PROTECTED --> DB_ENC
    SENSITIVE --> DB_ENC

    DB_ENC --> ROTATE
    STORAGE --> ROTATE

    ROTATE --> IAM
```

---

## 6. セキュリティインシデント分類と対応時間

インシデントの SEV（Severity）レベルと SLA。

```mermaid
graph TB
    subgraph "SEV1 - Critical（致命的）"
        SEV1["🔴 影響: 全ユーザー<br/>例: 全システムダウン<br/>データ漏洩 active<br/>SLA: 15 分以内復旧<br/>対応: 全員召集"]
    end

    subgraph "SEV2 - High（重大）"
        SEV2["🟠 影響: 多数ユーザー<br/>例: API 部分停止<br/>不正アクセス企図 blocked<br/>SLA: 1 時間以内<br/>対応: Lead Engineer"]
    end

    subgraph "SEV3 - Medium（中程度）"
        SEV3["🟡 影響: 限定ユーザー<br/>例: 機能バグ<br/>パフォーマンス低下<br/>SLA: 4 時間以内<br/>対応: チーム内"]
    end

    subgraph "SEV4 - Low（軽微）"
        SEV4["🟢 影響: 個別ユーザー<br/>例: UI バグ<br/>ドキュメント誤字<br/>SLA: 営業日内<br/>対応: バックログ化"]
    end

    subgraph "対応フロー共通"
        TRIAGE["1️⃣ Triage<br/>(SEV 判定)"]
        DIAGNOSE["2️⃣ Diagnose<br/>(原因調査)"]
        MITIGATE["3️⃣ Mitigate<br/>(緊急対応)"]
        FIX["4️⃣ Fix<br/>(恒久修正)"]
        PREVENT["5️⃣ Prevent<br/>(再発防止)"]
    end

    SEV1 --> TRIAGE
    SEV2 --> TRIAGE
    SEV3 --> TRIAGE
    SEV4 --> TRIAGE

    TRIAGE --> DIAGNOSE
    DIAGNOSE --> MITIGATE
    MITIGATE --> FIX
    FIX --> PREVENT
```

---

## 7. OWASP Top 10 対策チェックリスト

Web セキュリティ脆弱性への対策実装状況。

```mermaid
graph TB
    subgraph "OWASP Top 10"
        A1["🟩 A1: Injection<br/>(SQL / NoSQL<br/>String interpolation)"]
        A2["🟩 A2: Broken Auth<br/>(Session fixation<br/>Weak password)"]
        A3["🟩 A3: Sensitive Data<br/>Exposure<br/>(Unencrypted transit)"]
        A4["🟩 A4: XML External Entities<br/>(XXE attacks)"]
        A5["🟩 A5: Broken Access<br/>Control<br/>(IDOR / Privilege<br/>escalation)"]
        A6["🟩 A6: Security Misconfiguration<br/>(Insecure defaults)"]
        A7["🟩 A7: XSS<br/>(DOM / Stored / Reflected)"]
        A8["🟩 A8: Insecure<br/>Deserialization<br/>(Pickle / JSON)"]
        A9["🟩 A9: Using<br/>Components with<br/>Known Vulns<br/>(Deps & SCA)"]
        A10["🟩 A10: Insufficient<br/>Logging & Monitoring<br/>(Audit trail)"]
    end

    subgraph "対策実装状況"
        IMPL1["✅ Parameterized queries"]
        IMPL2["✅ OAuth2 + PKCE"]
        IMPL3["✅ TLS 1.2+ + HSTS"]
        IMPL4["✅ XML parser sanitize"]
        IMPL5["✅ IAM + RBAC + CORS"]
        IMPL6["✅ Infrastructure as Code"]
        IMPL7["✅ CSP + DomPurify"]
        IMPL8["✅ JSON validation + type check"]
        IMPL9["✅ Dependabot + OWASP ZAP"]
        IMPL10["✅ CloudTrail + CloudWatch"]
    end

    A1 --> IMPL1
    A2 --> IMPL2
    A3 --> IMPL3
    A4 --> IMPL4
    A5 --> IMPL5
    A6 --> IMPL6
    A7 --> IMPL7
    A8 --> IMPL8
    A9 --> IMPL9
    A10 --> IMPL10
```

---

## 8. コンプライアンスフレームワーク

多クラウド環境での規制要件への対応。

```mermaid
graph TB
    subgraph "適用規制"
        GDPR["🇪🇺 GDPR<br/>(個人データ保護)"]
        CCPA["🇺🇸 CCPA<br/>(カリフォルニア)"]
        APPI["🇯🇵 APPI<br/>(個人情報保護法)"]
        PCI["💳 PCI-DSS<br/>(カード情報)"]
    end

    subgraph "対策要件"
        DATA_MIN["📊 Data Minimization<br/>- 必要最小限のみ収集<br/>- 定期削除"]
        CONSENT["✅ Consent<br/>- Opt-in mechanism<br/>- 明確な同意"]
        RIGHT["👥 Data Rights<br/>- Right to access<br/>- Right to delete<br/>- Right to port"]
        ENCRYPT["🔐 Encryption<br/>- TLS in transit<br/>- AES at rest<br/>- Key management"]
        AUDIT["📋 Audit & Logging<br/>- CloudTrail (AWS)<br/>- Activity logs (Azure)<br/>- Cloud Audit (GCP)"]
        INCIDENT["🚨 Breach Response<br/>- 72 hour notif<br/>- Root cause<br/>- Remediation"]
    end

    subgraph "認証・監査"
        AUDIT_ORG["🏢 Third-party Audit<br/>- SOC2 Type 2<br/>- ISO 27001<br/>年 1 回実施"]
        DPA["📄 Data Processing<br/>Agreement<br/>- AWS<br/>- Azure<br/>- GCP"]
    end

    GDPR --> DATA_MIN
    CCPA --> CONSENT
    APPI --> RIGHT
    PCI --> ENCRYPT

    DATA_MIN --> AUDIT
    CONSENT --> AUDIT
    RIGHT --> AUDIT
    ENCRYPT --> AUDIT

    AUDIT --> INCIDENT

    INCIDENT --> AUDIT_ORG
    INCIDENT --> DPA
```

---

## 参照

- [AI_AGENT_08_SECURITY.md](AI_AGENT_08_SECURITY.md) — セキュリティ設定詳細
- [AI_AGENT_00_CRITICAL_RULES.md](AI_AGENT_00_CRITICAL_RULES.md) — セキュリティルール
- [AI_AGENT_11_BUG_FIX_REPORTS.md](AI_AGENT_11_BUG_FIX_REPORTS.md) — 過去のセキュリティ修正
