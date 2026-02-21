# 認証セットアップガイド 🔐

このガイドでは、マルチクラウド環境での認証機能のセットアップ方法を説明します。

## ✨ 自動化状況

v1.3.0より、**全クラウドプロバイダーでPulumi自動化に対応**しました！

| プラットフォーム | 認証サービス | Pulumi自動化 | JWT検証 | APIコード対応 |
|------------|------------|------------|---------|-------------|
| **AWS** | Amazon Cognito | ✅ 完全自動 | ✅ 実装済み | ✅ 完全対応 |
| **Azure** | Azure AD | ✅ 完全自動 | ✅ 実装済み | ✅ 完全対応 |
| **GCP** | Firebase Auth | ✅ 完全自動 | ✅ 実装済み | ✅ 完全対応 |

### 🚀 自動化により実現したこと
- `pulumi up` だけで認証リソースを自動作成
- AWS Cognitoと同レベルの自動化をAzure AD/Firebaseにも提供
- 手動セットアップなしで認証機能が利用可能

## AWS Cognito（完全自動化 ✅）

AWS版は完全に自動化されています。Pulumiが以下を自動的にプロビジョニングします：

### リソース
- Cognito User Pool
- User Pool Client
- User Pool Domain

### 環境変数（自動設定）
```bash
AUTH_PROVIDER=cognito
COGNITO_USER_POOL_ID=<自動生成>
COGNITO_CLIENT_ID=<自動生成>
AWS_REGION=ap-northeast-1
```

### 確認方法
```bash
# AWSマネジメントコンソール → Cognito
# User Poolが作成されていることを確認
```

---

## Azure AD（完全自動化 ✅）

Azure版もPulumiで完全自動化されています。`pulumi-azuread`を使用して、以下を自動作成します：

### 自動作成されるリソース
- **Azure AD Application**: API用のアプリケーション登録
- **Service Principal**: アプリケーションのサービスプリンシパル
- **Redirect URIs**: フロントエンド向けのリダイレクトURI
- **OAuth2 Permission Scopes**: API.Access スコープ

### 環境変数（Pulumiが自動出力）
`pulumi up` 実行後、以下の情報がOutputsとして出力されます：

```bash
AUTH_PROVIDER=azure
AZURE_TENANT_ID=<pulumi output "azure_ad_tenant_id">
AZURE_CLIENT_ID=<pulumi output "azure_ad_client_id">
```

### 手動設定が必要な部分（オプション）

**Azure AD B2Cを使用する場合のみ**、以下の手動設定が必要です：
- B2Cテナントの作成（通常のAzure ADとは別管理）
- ユーザーフローのカスタマイズ

### 旧手動セットアップ方法（参考）

<details>
<summary>v1.2.x以前の手動セットアップ方法（クリックして展開）</summary>

1. **アプリケーション登録を作成**

```bash
# Azure CLI
az ad app create \
  --display-name "multicloud-auto-deploy-staging-api" \
  --sign-in-audience AzureADMyOrg
```

または、Azureポータルから：
- Azure Portal → Azure Active Directory → App registrations → New registration
- Name: `multicloud-auto-deploy-staging-api`
- Supported account types: `Accounts in this organizational directory only`
- Register

2. **リダイレクトURIを設定**

- Authentication → Add a platform → Single-page application
- Redirect URIs: `https://<your-frontend-domain>/callback`

3. **APIアクセス許可を設定**（オプション）

- API permissions → Add a permission → Microsoft Graph
- Delegated permissions: `User.Read`, `openid`, `profile`, `email`

4. **環境変数を設定**

Azure Function Appの環境変数に以下を追加：

```bash
AUTH_PROVIDER=azure
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<application-client-id>
```

取得方法：
```bash
# Tenant ID
az account show --query tenantId -o tsv

# Client ID
az ad app list --display-name "multicloud-auto-deploy-staging-api" \
  --query "[0].appId" -o tsv
```

#### GitHub Secretsに追加

```bash
# .github/workflows/deploy-azure.ymlで使用
gh secret set AZURE_TENANT_ID --body "<your-tenant-id>"
gh secret set AZURE_CLIENT_ID --body "<your-client-id>"
```

### オプション2: Azure AD B2C（高度な設定）

より高度な認証フローが必要な場合はAzure AD B2Cを使用します。

#### 手順

1. **B2Cテナントを作成**

- Azure Portal → Create a resource → Azure AD B2C → Create
- Tenant name: `multicloudautodeploy`
- Domain name: `multicloudautodeploy.onmicrosoft.com`

2. **アプリケーションを登録**

- Azure AD B2C → App registrations → New registration
- Name: `multicloud-auto-deploy-api`
- Redirect URI: `https://<your-frontend>/callback`

3. **ユーザーフローを作成**

- Azure AD B2C → User flows → New user flow
- Type: Sign up and sign in
- Name: `B2C_1_signupsignin`

4. **環境変数を設定**

```bash
AUTH_PROVIDER=azure
AZURE_TENANT_ID=multicloudautodeploy.onmicrosoft.com
AZURE_CLIENT_ID=<b2c-client-id>
# B2Cの場合は追加設定が必要
# jwt_verifier.pyでis_b2c=Trueを設定
```

---

## GCP Firebase Authentication（完全自動化 ✅）

GCP版もPulumiで完全自動化されています。`pulumi-gcp`の`firebase`モジュールを使用して、以下を自動作成します：

### 自動作成されるリソース
- **Firebase Project**: 既存GCPプロジェクトでFirebaseを有効化
- **Firebase Web App**: Webアプリケーションの登録
- **Firebase Configuration**: API Key、Auth Domain等の設定

### 環境変数（Pulumiが自動出力）
`pulumi up` 実行後、以下の情報がOutputsとして出力されます：

```bash
AUTH_PROVIDER=firebase
GCP_PROJECT_ID=<pulumi output "firebase_project_id">
# Firebase設定（フロントエンド用）
FIREBASE_API_KEY=<pulumi output "firebase_api_key">
FIREBASE_AUTH_DOMAIN=<pulumi output "firebase_auth_domain">
```

### 手動設定が必要な部分

**以下の設定のみ手動で行う必要があります**（OAuth同意画面の要件のため）：

1. **Google Sign-Inプロバイダーの有効化**
   - [Firebase Console](https://console.firebase.google.com/) → Authentication → Sign-in method
   - Google プロバイダーを有効化
   - Project support email を設定

2. **OAuth同意画面の設定**（初回のみ）
   - GCP Console → APIs & Services → OAuth consent screen
   - User Type: External
   - アプリ名、サポートメール、開発者連絡先を入力

3. **承認済みドメインの追加**（本番環境）
   - Firebase Console → Authentication → Settings → Authorized domains
   - カスタムドメインを追加

### 旧手動セットアップ方法（参考）

<details>
<summary>v1.2.x以前の手動セットアップ方法（クリックして展開）</summary>

### 手順

1. **Firebase Consoleでプロジェクトを選択**

- [Firebase Console](https://console.firebase.google.com/)
- 既存のGCPプロジェクトを選択または新規作成

2. **Authentication を有効化**

- Build → Authentication → Get started
- Sign-in method タブを選択

3. **Google Sign-Inを有効化**

- Sign-in method → Google
- Enable
- Project support email: 設定
- Save

4. **承認済みドメインを追加**

- Sign-in method → Authorized domains
- Add domain: `<your-frontend-domain>`

5. **Web アプリを追加**

- Project Overview → Add app → Web
- App nickname: `multicloud-auto-deploy-web`
- Register app

6. **Firebase 設定を取得**

```javascript
// Firebase config
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  appId: "..."
};
```

7. **環境変数を設定**

GCP Cloud Functionsの環境変数に以下を追加：

```bash
AUTH_PROVIDER=firebase
GCP_PROJECT_ID=<your-project-id>
# 必要に応じて
# GCP_CLIENT_ID=<web-app-client-id>
```

</details>

#### GitHub Secretsに追加

```bash
gh secret set GCP_PROJECT_ID --body "<your-project-id>"
```

---

## 開発環境での認証無効化

開発環境では認証をバイパスできます：

```bash
# 環境変数
AUTH_DISABLED=true

# または docker-compose.yml
environment:
  - AUTH_DISABLED=true
```

認証無効時は、すべてのリクエストで管理者ユーザーとして扱われます：

```python
# test-user-1 (Admins group)
user_id: "test-user-1"
email: "test@example.com"
groups: ["Admins"]
```

---

## JWT検証の仕組み

実装済みのJWT検証ロジック（`app/jwt_verifier.py`）：

### Cognito
```python
issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
jwks_url = f"{issuer}/.well-known/jwks.json"
audience = client_id
```

### Azure AD
```python
issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
audience = client_id
```

### Firebase
```python
issuer = f"https://securetoken.google.com/{project_id}"
jwks_url = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
audience = project_id
```

---

## トラブルシューティング

### JWT検証失敗

**症状**: `401 Unauthorized` with "Token verification failed"

**原因と解決策**:

1. **環境変数が設定されていない**
   ```bash
   # 確認
   echo $AUTH_PROVIDER
   echo $AZURE_TENANT_ID  # または COGNITO_USER_POOL_ID, GCP_PROJECT_ID
   ```

2. **トークンの発行元が間違っている**
   - フロントエンドで取得したトークンのissuerを確認
   - バックエンドの設定と一致しているか確認

3. **JWKSの取得失敗**
   - ネットワーク接続を確認
   - jwks_urlが正しいか確認

4. **audienceが間違っている**
   - トークンのaudクレームとclient_idが一致しているか確認

### Azure AD: "invalid_client"

**原因**: Client Secret が設定されているが、アプリがPublic Clientとして登録されている

**解決策**: 
- Single-page applicationとして登録（Client Secret不要）
- または、Web applicationとして登録してClient Secretを環境変数に追加

### Firebase: "aud claim does not match"

**原因**: Project IDが間違っている

**解決策**:
```bash
# 正しいProject IDを確認
gcloud config get-value project

# 環境変数を更新
export GCP_PROJECT_ID=<correct-project-id>
```

---

## 次のステップ

1. ✅ 認証サービスのセットアップ（このガイド）
2. フロントエンド認証フローの実装
3. テストユーザーの作成
4. 本番環境へのデプロイ

---

## 参考リンク

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Azure AD Authentication](https://learn.microsoft.com/en-us/azure/active-directory/)
- [Firebase Authentication](https://firebase.google.com/docs/auth)
- [JWT.io - Token Debugger](https://jwt.io/)

---

**更新日**: 2026年2月17日  
**バージョン**: 1.0.0
