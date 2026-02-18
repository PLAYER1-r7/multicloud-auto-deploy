# トラブルシューティングガイド

CI/CDワークフロー実行時に遭遇する可能性のある問題と解決策

## 📋 目次

- [開発環境の認証セットアップ](#開発環境の認証セットアップ)
- [Azure認証問題](#azure認証問題)
- [GCPリソース競合](#gcpリソース競合)
- [フロントエンドAPI接続問題](#フロントエンドapi接続問題)
- [Pulumi State管理](#pulumi-state管理)
- [権限エラー](#権限エラー)
- [AWS Lambda Runtime Errors](#aws-lambda-runtime-errors)
- [GCP Cloud Run 500 Errors](#gcp-cloud-run-500-errors)
- [Azure Functions 500 Errors](#azure-functions-500-errors)

---

## 開発環境の認証セットアップ

### GitHub CLI認証

GitHub CLIを使用してリポジトリの操作やCI/CDワークフローの監視を行う場合、認証が必要です。

**認証手順**:

```bash
# GitHub CLI認証を開始
gh auth login

# 対話型プロンプトで以下を選択:
# 1. Where do you use GitHub? → GitHub.com
# 2. What is your preferred protocol? → HTTPS
# 3. Authenticate Git with your GitHub credentials? → Yes
# 4. How would you like to authenticate? → Login with a web browser

# ワンタイムコードが表示されるのでコピー
# Enterを押してブラウザが開いたら、コードを入力して認証完了
```

**認証確認**:

```bash
# ログイン状態を確認
gh auth status

# ワークフロー実行リストを確認
gh run list --branch develop --limit 5
```

### Pulumi認証

PulumiはインフラストラクチャのState管理とデプロイに使用されます。ローカル開発環境とGitHub Actionsの両方で認証が必要です。

**ローカル環境での認証**:

```bash
# Pulumiにログイン（ブラウザ認証）
pulumi login

# ログイン状態を確認
pulumi whoami
```

**GitHub Actions環境での認証**:

GitHub ActionsではPulumiアクセストークンをSecretsとして設定する必要があります。

1. **Pulumiアクセストークンの生成**:
   - [Pulumi Console](https://app.pulumi.com/)にログイン
   - Settings → Access Tokens
   - "Create Token"をクリック
   - トークン名を入力（例: `github-actions-multicloud-auto-deploy`）
   - トークンをコピー

2. **GitHub Secretsに設定**:
   - GitHubリポジトリの Settings → Secrets and variables → Actions
   - "New repository secret"をクリック
   - Name: `PULUMI_ACCESS_TOKEN`
   - Value: コピーしたPulumiトークンを貼り付け
   - "Add secret"をクリック

**トークン検証**:

```bash
# ローカルでPulumiトークンを確認
pulumi whoami

# GitHub Secretsが設定されているか確認（Webブラウザで）
# https://github.com/<YOUR_ORG>/<YOUR_REPO>/settings/secrets/actions
```

**トラブルシューティング**:

もしGitHub Actionsで以下のエラーが出た場合:

```
error: problem logging in: Unauthorized: No credentials provided or are invalid.
```

対処法:

1. Pulumiトークンが有効期限切れでないか確認
2. GitHub Secretsの`PULUMI_ACCESS_TOKEN`が正しく設定されているか確認
3. 必要に応じて新しいトークンを生成してSecretsを更新

---

## Azure認証問題

### 問題1: "Authenticating using the Azure CLI is only supported as a User"

**症状**:

```
Error: building account: could not acquire access token to parse claims:
Authenticating using the Azure CLI is only supported as a User (not a Service Principal).
```

**原因**:

- Azure CLIでログイン後、Pulumiが認証情報を取得できない場合がある

**解決策**:

1. **AZURE_CREDENTIALSから認証情報を抽出**:

```bash
# GitHub SecretsからAZURE_CREDENTIALSを取得し、環境変数に設定
export AZURE_CLIENT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.clientId')
export AZURE_CLIENT_SECRET=$(echo $AZURE_CREDENTIALS | jq -r '.clientSecret')
export AZURE_SUBSCRIPTION_ID=$(echo $AZURE_CREDENTIALS | jq -r '.subscriptionId')
export AZURE_TENANT_ID=$(echo $AZURE_CREDENTIALS | jq -r '.tenantId')
```

2. **Pulumi設定で明示的に指定**:

```bash
pulumi config set azure-native:clientId $AZURE_CLIENT_ID --secret
pulumi config set azure-native:clientSecret $AZURE_CLIENT_SECRET --secret
pulumi config set azure-native:subscriptionId $AZURE_SUBSCRIPTION_ID
pulumi config set azure-native:tenantId $AZURE_TENANT_ID
```

### 問題2: Azure CLI認証後のPulumi実行エラー

**症状**:
ACR操作のためにAzure CLIログイン後、pulumi stack output コマンドが失敗

**解決策**:
Pulumi outputsをインフラデプロイ時にGitHub Actions outputsに保存：

```yaml
- name: Deploy Infrastructure
  id: pulumi
  run: |
    pulumi up --yes

    # Pulumiからoutputsを取得してGitHub Actionsに保存
    ACR_NAME=$(pulumi stack output container_registry_name)
    echo "acr_name=$ACR_NAME" >> $GITHUB_OUTPUT

- name: Use Output Later
  run: |
    # GitHub Actions outputsから取得
    echo "ACR: ${{ steps.pulumi.outputs.acr_name }}"
```

---

## GCPリソース競合

### 問題1: "Error 409: The repository already exists"

**症状**:

```
Error: Error creating Repository: googleapi: Error 409: the repository already exists.
Error: Error creating Service: googleapi: Error 409: Resource already exists.
Error: Error creating BackendBucket: googleapi: Error 409: already exists.
```

**根本原因**:

- Pulumiがローカルstateファイルを使用していた
- GitHub Actions実行ごとにクリーンな環境で実行されるため、stateが保存されない
- Pulumiが既存リソースを認識できず、毎回新規作成を試みる

**解決策（永続的なremote state）**:

1. **GCSバケットの作成**:

```bash
gcloud storage buckets create gs://multicloud-auto-deploy-pulumi-state-gcp \
  --location=asia-northeast1 \
  --uniform-bucket-level-access
```

2. **サービスアカウントに権限付与**:

```bash
gcloud storage buckets add-iam-policy-binding gs://multicloud-auto-deploy-pulumi-state-gcp \
  --member="serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

3. **Pulumi backendの設定**:

```bash
# GCS backendにログイン
pulumi login gs://multicloud-auto-deploy-pulumi-state-gcp

# または環境変数で設定
export PULUMI_BACKEND_URL="gs://multicloud-auto-deploy-pulumi-state-gcp"
```

4. **既存リソースのインポート（一度だけ実行）**:

```bash
cd infrastructure/pulumi/gcp

# 既存リソースをインポート
pulumi import google-native:artifactregistry/v1:Repository main \
  "projects/PROJECT_ID/locations/REGION/repositories/REPO_NAME"

pulumi import gcp:storage/bucket:Bucket frontend "BUCKET_NAME"

pulumi import gcp:compute/globalAddress:GlobalAddress frontend \
  "projects/PROJECT_ID/global/addresses/ADDRESS_NAME"

pulumi import gcp:firestore/database:Database main \
  "projects/PROJECT_ID/databases/(default)"

pulumi import gcp:cloudrunv2/service:Service api \
  "projects/PROJECT_ID/locations/REGION/services/SERVICE_NAME"

# Stateの確認
terraform state list

# 変更内容の確認
terraform plan
```

5. **ワークフローのシンプル化**:

```yaml
# import処理は不要になる
- name: Deploy Infrastructure
  run: |
    cd infrastructure/terraform/gcp
    terraform init
    terraform plan -var="project_id=${{ secrets.GCP_PROJECT_ID }}"
    terraform apply -var="project_id=${{ secrets.GCP_PROJECT_ID }}" -auto-approve
```

### 問題2: "Error 403: Permission denied on Firestore"

**症状**:

```
Error: Error creating database: googleapi: Error 403:
The caller does not have permission
```

**解決策**:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.owner"
```

### 問題3: "Error 403: Permission 'run.services.setIamPolicy' denied"

**症状**:
Cloud RunサービスのIAMポリシーを設定できない

**解決策**:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

---

## フロントエンドAPI接続問題

### 問題: メッセージ送信が「送信中」のまま固まる

**症状**:

- フロントエンドからAPIへのリクエストがタイムアウト
- ブラウザのコンソールに"Failed to fetch"エラー

**原因**:
フロントエンドビルド時に正しいAPI URLが設定されていない

**Azure・AWSでの発生パターン**:

1. フロントエンドをインフラデプロイ**前**にビルド
2. API URLがまだ存在しない/間違った値
3. ビルドされたフロントエンドが間違ったURLを使用

**解決策（推奨フロー）**:

```yaml
jobs:
  build-and-deploy:
    steps:
      # 1. インフラをデプロイ（API URLを生成）
      - name: Deploy Infrastructure
        id: terraform
        run: |
          terraform apply -auto-approve

          # API URLをoutputsに保存
          API_URL=$(terraform output -raw api_url)
          echo "api_url=$API_URL" >> $GITHUB_OUTPUT

      # 2. バックエンドをデプロイ
      - name: Deploy Backend
        run: |
          # Docker build & push, Lambda update, etc.

      # 3. フロントエンドを正しいAPI URLでビルド
      - name: Build Frontend
        run: |
          cd services/frontend
          npm install
          npm run build
        env:
          VITE_API_URL: ${{ steps.terraform.outputs.api_url }}

      # 4. フロントエンドをデプロイ
      - name: Deploy Frontend
        run: |
          # S3/Storage/GCSにアップロード
```

**重要ポイント**:

- フロントエンドのビルドは必ずインフラデプロイ**後**に実行
- Terraform outputsから動的にAPI URLを取得
- 環境変数`VITE_API_URL`に正しい値を設定

**検証方法**:

```bash
# デプロイ後にフロントエンドのJSファイルを確認
curl -s https://YOUR-FRONTEND-URL/assets/index-*.js | grep -o "https://.*execute-api.*"
```

---

## Pulumi State管理

### ベストプラクティス

1. **Remote Backend を必ず使用**:
   - AWS: S3 (`pulumi login s3://bucket-name`)
   - Azure: Azure Blob Storage (`pulumi login azblob://container`)
   - GCP: GCS (`pulumi login gs://bucket-name`)
   - Pulumi Service: `pulumi login` (推奨)

2. **State の暗号化**:
   - Pulumiは自動的にstateを暗号化
   - パスフレーズまたはKMS統合を使用

3. **State の定期バックアップ**:

```bash
# Pulumi Service使用時
pulumi stack export > backups/stack-$(date +%Y%m%d-%H%M%S).json

# GCS使用時
gcloud storage cp gs://pulumi-state-bucket/.pulumi/stacks/* \
  ./backups/
```

---

## 権限エラー

### AWS Lambda更新失敗

**必要な権限**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "*"
    }
  ]
}
```

### Azure ACR Push失敗

**必要なロール**:

- `AcrPush` または `Contributor`

**確認方法**:

```bash
az role assignment list \
  --assignee YOUR_SERVICE_PRINCIPAL_ID \
  --scope /subscriptions/SUB_ID/resourceGroups/RG_NAME/providers/Microsoft.ContainerRegistry/registries/ACR_NAME
```

### GCP Artifact Registry Push失敗

**必要なロール**:

- `roles/artifactregistry.writer`
- `roles/storage.admin`

**付与方法**:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/artifactregistry.writer"
```

---

## よくある質問

### Q: ワークフローが途中で止まる

**確認ポイント**:

1. GitHub Actionsのログで最後の出力を確認
2. タイムアウト設定を確認（デフォルト: 360分）
3. リソースクォータを確認（特にGCP）

### Q: 手動デプロイの方法は？

**答え**:

1. GitHub リポジトリの **Actions** タブを開く
2. 対象のワークフロー（deploy-aws.yml等）を選択
3. **Run workflow** をクリック
4. 環境（staging/production）を選択して実行

### Q: デプロイを元に戻したい

**答え**:

```bash
# Terraformでリソースを削除
cd infrastructure/terraform/[aws|azure|gcp]
terraform destroy -auto-approve

# 特定のリソースだけ削除
terraform destroy -target=google_cloud_run_v2_service.api
```

---

## デバッグ手順

### 1. ローカルで再現

```bash
# 環境変数を設定
export AZURE_CLIENT_ID="..."
export AWS_ACCESS_KEY_ID="..."

# Pulumiコマンドを実行
cd infrastructure/pulumi/azure
pulumi preview
```

### 2. GitHub Actions ログの確認

重要な情報:

- エラーメッセージの完全な内容
- 失敗したステップ名
- 環境変数の値（機密情報は除く）

### 3. リソースの手動確認

```bash
# AWS
aws apigatewayv2 get-apis --region ap-northeast-1
aws s3 ls
aws cloudfront list-distributions

# Azure
az group list
az containerapp list
az storage account list

# GCP
gcloud run services list
gcloud storage buckets list
gcloud compute addresses list --global
```

---

## AWS Lambda + API Gateway統合問題

### 問題: API Gateway経由でLambda呼び出し時に500エラー

**症状**:

```json
{ "message": "Internal Server Error" }
```

- Lambdaを直接呼び出すと成功する
- API Gateway経由だと500エラーになる
- CloudWatch LogsにLambdaの実行ログが記録されない
- CloudWatch MetricsでLambda呼び出し回数が0のまま

**原因**:
Lambda関数のリソースポリシーでSourceArn形式が正しくない。

#### HTTP API vs REST API の違い

| API種類      | SourceArn形式                                              | 例                                                                 |
| ------------ | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| **HTTP API** | `arn:aws:execute-api:{region}:{account-id}:{api-id}/*/*`   | `arn:aws:execute-api:ap-northeast-1:123456789012:abc123def4/*/*`   |
| **REST API** | `arn:aws:execute-api:{region}:{account-id}:{api-id}/*/*/*` | `arn:aws:execute-api:ap-northeast-1:123456789012:abc123def4/*/*/*` |

**重要**: HTTP APIは `/*/*` (2つのワイルドカード)、REST APIは `/*/*/*` (3つのワイルドカード)

**解決策**:

1. **現在の権限を確認**:

```bash
aws lambda get-policy --function-name YOUR_FUNCTION_NAME --query Policy --output text | jq .
```

2. **API Gatewayアクセスログを有効化**（エラー詳細を確認するため）:

```bash
# CloudWatch Logsグループ作成
aws logs create-log-group --log-group-name /aws/apigateway/YOUR_API_NAME

# アクセスログ有効化
aws apigatewayv2 update-stage \
  --api-id YOUR_API_ID \
  --stage-name '$default' \
  --access-log-settings "DestinationArn=arn:aws:logs:REGION:ACCOUNT_ID:log-group:/aws/apigateway/YOUR_API_NAME:*,Format=\$context.requestId \$context.error.message \$context.integrationErrorMessage \$context.status"

# ログ確認
aws logs tail /aws/apigateway/YOUR_API_NAME --follow
```

3. **正しい権限を設定**（HTTP API用）:

```bash
# 古い権限を削除
aws lambda remove-permission \
  --function-name YOUR_FUNCTION_NAME \
  --statement-id OLD_STATEMENT_ID

# 正しい権限を追加
aws lambda add-permission \
  --function-name YOUR_FUNCTION_NAME \
  --statement-id apigateway-http-api \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:REGION:ACCOUNT_ID:API_ID/*/*"
```

4. **動作確認**:

```bash
curl https://YOUR_API_ID.execute-api.REGION.amazonaws.com/api/messages/
```

**デバッグ手順**:

1. Lambda直接呼び出しテスト:

```bash
aws lambda invoke \
  --function-name YOUR_FUNCTION_NAME \
  --payload '{"version":"2.0","routeKey":"$default","rawPath":"/api/messages/","headers":{"accept":"application/json"},"requestContext":{"http":{"method":"GET","path":"/api/messages/"}}}' \
  /tmp/response.json
```

2. CloudWatch Metricsで呼び出し回数確認:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=YOUR_FUNCTION_NAME \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum
```

3. API Gatewayアクセスログ確認（最も重要）:

```bash
aws logs tail /aws/apigateway/YOUR_API_NAME --since 5m
```

**参考リンク**:

- [AWS Lambda リソースベースのポリシー](https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html)
- [API Gateway HTTP API と Lambda の統合](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html)

---

## AWS Lambda Runtime Errors

### 問題1: Runtime.ImportModuleError - index.handler not found

**症状**:

```
[ERROR] Runtime.ImportModuleError: Unable to import module 'index': No module named 'index'
```

**原因**:

- GitHub ActionsワークフローがLambda関数用に`handler.py`を生成
- Lambda関数設定では`index.handler`を期待
- ファイル名のミスマッチ

**解決策**:

1. **既存の`index.py`を使用するようワークフロー修正**:

```yaml
# ❌ 動的生成（削除）
# cat > package/handler.py << 'EOF'
# from mangum import Mangum
# from app.main import app
# handler = Mangum(app, lifespan="off")
# EOF

# ✅ 既存ファイルをコピー
cp index.py package/
```

2. **`services/api/index.py`の内容確認**:

```python
"""AWS Lambda エントリーポイント"""
from mangum import Mangum
from app.main import app

# Lambda handler
handler = Mangum(app, lifespan="off")
```

3. **Lambda設定確認**:

```bash
aws lambda get-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --query 'Handler'
# 出力: "index.handler" であることを確認
```

4. **デプロイ後の動作確認**:

```bash
# CloudWatch Logsでエラーがないことを確認
aws logs tail /aws/lambda/YOUR_FUNCTION_NAME --since 5m

# API経由でテスト
curl https://YOUR_API_URL/health
```

**修正コミット例**:

```bash
git commit -m "fix(ci): Use index.py instead of handler.py for Lambda entry point"
```

---

## GCP Cloud Run 500 Errors

### 問題1: 500 Internal Server Error - LocalBackend connection refused

**症状**:

```
ConnectionRefusedError: [Errno 111] Connection refused
File "/workspace/app/backends/local.py", line 30, in __init__
  self._ensure_bucket()
```

**原因**:

- `CLOUD_PROVIDER`環境変数が未設定
- アプリケーションがLocalBackend（MinIO localhost:9000）を使用しようとする
- Cloud Runでlocalhost:9000は存在しない

**解決策**:

1. **環境変数を設定**:

```yaml
# .github/workflows/deploy-gcp.yml
gcloud functions deploy $FUNCTION_NAME \
--set-env-vars=ENVIRONMENT=staging,CLOUD_PROVIDER=gcp,GCP_PROJECT_ID=$PROJECT_ID,FIRESTORE_COLLECTION=messages
```

2. **環境変数確認**:

```bash
gcloud run services describe YOUR_SERVICE_NAME \
  --region=asia-northeast1 \
  --format="value(spec.template.spec.containers[0].env)"
```

3. **Cloud Runログで確認**:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=YOUR_SERVICE_NAME AND severity>=ERROR" \
  --limit 10 \
  --format="table(timestamp,textPayload)" \
  --freshness=5m
```

### 問題2: AttributeError - 'bytes' object has no attribute 'encode'

**症状**:

```
AttributeError: 'bytes' object has no attribute 'encode'
File "/workspace/main.py", line 19, in handler
  "query_string": request.query_string.encode() if request.query_string else b"",
```

**原因**:

- `request.query_string`は既に`bytes`型
- `.encode()`を再度呼び出すとエラー

**解決策**:

`services/api/function.py`を修正:

```python
# ❌ 誤り
"query_string": request.query_string.encode() if request.query_string else b"",

# ✅ 正しい
"query_string": request.query_string if request.query_string else b"",
```

**動作確認**:

```bash
curl -X POST "https://YOUR_CLOUD_RUN_URL/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test message","author":"DevOps"}'
```

---

## Azure Functions 500 Errors

### 問題1: 500 Internal Server Error - Cosmos DB connection failed

**症状**:

```
HTTP 500 Internal Server Error (No response body)
```

**原因**:

- `AZURE_COSMOS_ENDPOINT`と`AZURE_COSMOS_KEY`が空
- 既存の環境変数名が`COSMOS_DB_ENDPOINT`/`COSMOS_DB_KEY`
- アプリケーションが間違った環境変数を参照

**解決策**:

1. **既存の環境変数を確認**:

```bash
az functionapp config appsettings list \
  --name YOUR_FUNCTION_APP \
  --resource-group YOUR_RESOURCE_GROUP \
  --output table | grep COSMOS
```

2. **ワークフローで既存値を取得して設定**:

```yaml
# Get existing Cosmos DB settings
COSMOS_ENDPOINT=$(az functionapp config appsettings list \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query "[?name=='COSMOS_DB_ENDPOINT'].value | [0]" -o tsv)

COSMOS_KEY=$(az functionapp config appsettings list \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query "[?name=='COSMOS_DB_KEY'].value | [0]" -o tsv)

# Set environment variables
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    CLOUD_PROVIDER=azure \
    ENVIRONMENT=staging \
    AZURE_COSMOS_ENDPOINT="${COSMOS_ENDPOINT}" \
    AZURE_COSMOS_KEY="${COSMOS_KEY}"
```

3. **即座の修正（手動）**:

```bash
# 既存値を取得
COSMOS_ENDPOINT=$(az functionapp config appsettings list \
  --name YOUR_FUNCTION_APP \
  --resource-group YOUR_RESOURCE_GROUP \
  --query "[?name=='COSMOS_DB_ENDPOINT'].value | [0]" -o tsv)

COSMOS_KEY=$(az functionapp config appsettings list \
  --name YOUR_FUNCTION_APP \
  --resource-group YOUR_RESOURCE_GROUP \
  --query "[?name=='COSMOS_DB_KEY'].value | [0]" -o tsv)

# 新しい変数名で設定
az functionapp config appsettings set \
  --name YOUR_FUNCTION_APP \
  --resource-group YOUR_RESOURCE_GROUP \
  --settings \
    "AZURE_COSMOS_ENDPOINT=${COSMOS_ENDPOINT}" \
    "AZURE_COSMOS_KEY=${COSMOS_KEY}"
```

4. **Function App再起動待機（約30秒）後、テスト**:

```bash
curl -X POST "https://YOUR_FUNCTION_APP.azurewebsites.net/api/HttpTrigger/api/messages/" \
  -H "Content-Type: application/json" \
  -d '{"content":"Azure test","author":"DevOps"}'
```

### 問題2: 404 Not Found / 405 Method Not Allowed (Front Door経由)

**症状**:

- ブラウザから Front Door URL経由でアクセス: 404 Error
- POST /api/messages/: 405 Method Not Allowed

**原因**:

- フロントエンドが間違ったAPI URLを使用
- `/api/HttpTrigger`パスが含まれていない

**解決策**:

1. **正しいAPI URLを設定**:

```yaml
# .github/workflows/deploy-azure.yml
FUNC_HOSTNAME=$(az functionapp show --name YOUR_FUNCTION_APP --resource-group YOUR_RESOURCE_GROUP --query defaultHostName -o tsv)
echo "api_url=https://${FUNC_HOSTNAME}/api/HttpTrigger" >> $GITHUB_OUTPUT
```

2. **フロントエンドビルド時に正しいURLを使用**:

```yaml
- name: Build Frontend
  run: |
    cd services/frontend_react
    npm install
    VITE_API_URL="${{ steps.pulumi_outputs.outputs.api_url }}" npm run build
  env:
    VITE_API_URL: ${{ steps.pulumi_outputs.outputs.api_url }}
```

3. **Function App直接アクセスで動作確認**:

```bash
# 正しいパスでテスト
curl https://YOUR_FUNCTION_APP.azurewebsites.net/api/HttpTrigger/health
```

---

## Azure Functions Flex Consumption Plan

### 問題1: Deployment shows "Partially Successful" but function works

**症状**:

```
ERROR: Deployment was partially successful. These are the deployment logs:
[***"message": "The logs you are looking for were not found. In flex consumption plans,
the instance will be recycled and logs will not be persisted after that..."***]

⚠️  Deployment status unclear, retrying...
```

しかし、Function Appは実際には正常に動作している。

**原因**:

- Azure Flex Consumption プランではインスタンスがリサイクルされ、デプロイログが保持されない
- `az functionapp deployment source config-zip` が "partially successful" を返すが、実際にはデプロイは成功している
- 詳細なステップログ（`UploadPackageStep`, `OryxBuildStep`等）が出力されない

**解決策**:

1. **"Deployment was successful" メッセージを検出**:

```yaml
# Check for successful deployment (in order of reliability)
# 1. Explicit success message (most reliable for Flex Consumption)
if grep -q "Deployment was successful" deploy_log.txt; then
  echo "✅ Deployment successful!"
  DEPLOY_SUCCESS=true
  break
# 2. Deployment steps completed (for other plan types)
elif grep -q "UploadPackageStep.*completed" deploy_log.txt || \
     grep -q "SyncTriggerStep" deploy_log.txt; then
  echo "✅ Deployment steps completed!"
  DEPLOY_SUCCESS=true
  break
fi
```

2. **"partially successful" を無視**:

```yaml
# Critical error (but not "partially successful")
elif grep -q "ERROR:" deploy_log.txt && ! grep -q "partially successful" deploy_log.txt; then
echo "❌ Critical deployment error"
cat deploy_log.txt
exit 1
fi
```

3. **ヘルスチェックを必須検証に**:

```yaml
- name: Verify Deployment
  run: |
    # ... ヘルスチェック実行 ...

    if [ "$health_check_passed" = true ]; then
      echo "✅ Azure Function deployment verified successfully!"
    else
      echo "❌ Health check failed"
      exit 1  # 失敗として扱う
    fi
```

### 問題2: defaultHostName returns null for Flex Consumption

**症状**:

```
Testing: https:///api/HttpTrigger/health
❌ Health check failed
```

`az functionapp show --query defaultHostName` がnullを返し、URLが空になる。

**原因**:

- Flex Consumption プランでは `defaultHostName` フィールドがnullまたは未設定
- 標準的な `az functionapp show` コマンドでホスト名を取得できない

**解決策**:

**`az functionapp config hostname list` を使用**:

```yaml
# Get hostname - for Flex Consumption plan, use config hostname list
# (defaultHostName is not reliable for Flex Consumption SKU)
FUNC_HOSTNAME=$(az functionapp config hostname list \
  --webapp-name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query '[0].name' -o tsv)

if [ -n "$FUNC_HOSTNAME" ] && [ "$FUNC_HOSTNAME" != "None" ]; then
  echo "✅ Got hostname: $FUNC_HOSTNAME"
  FUNC_URL="https://${FUNC_HOSTNAME}/api/HttpTrigger"
else
  echo "❌ Failed to get Function App hostname"
  exit 1
fi
```

**検証例**:

```bash
# ❌ 動作しない（Flex Consumptionでnull）
az functionapp show --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg \
  --query defaultHostName -o tsv

# ✅ 動作する
az functionapp config hostname list \
  --webapp-name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg \
  --query '[0].name' -o tsv

# Output: multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net
```

### 問題3: Kudu restart during deployment causes failures

**症状**:

```
🔄 Kudu restart detected, retrying...
Attempt 2/3...
```

大きなデプロイパッケージでKuduが再起動し、デプロイが中断される。

**解決策**:

1. **パッケージサイズの最適化**:

```yaml
- name: Package Function App
  run: |
    cd services/api

    echo "📦 Creating optimized deployment package..."

    # Install dependencies
    pip install --target .deployment --no-cache-dir -r requirements.txt

    # Clean up unnecessary files from dependencies
    find .deployment -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find .deployment -type f -name "*.pyc" -delete 2>/dev/null || true
    find .deployment -type f -name "*.pyo" -delete 2>/dev/null || true
    find .deployment -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find .deployment -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

    # Copy application code
    cp -r app .deployment/
    cp function_app.py .deployment/
    cp host.json .deployment/

    # Create ZIP package
    cd .deployment
    zip -r -q ../function-app.zip .

    echo "✅ Package size: $(du -h ../function-app.zip | cut -f1)"
```

2. **リトライロジックの実装**:

```yaml
# Retry deployment up to 3 times to handle Kudu restarts
MAX_RETRIES=3
RETRY_COUNT=0
DEPLOY_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  echo "Attempt $((RETRY_COUNT+1))/$MAX_RETRIES..."

  # Run deployment
  az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP \
    --src services/api/function-app.zip \
    --timeout 600 \
    2>&1 | tee deploy_log.txt || true

  # Check for Kudu restart
  if grep -q "Kudu has been restarted" deploy_log.txt; then
    echo "🔄 Kudu restart detected, retrying..."
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 30
    continue
  fi

  # Check for success
  if grep -q "Deployment was successful" deploy_log.txt; then
    DEPLOY_SUCCESS=true
    break
  fi

  RETRY_COUNT=$((RETRY_COUNT+1))
  sleep 30
done
```

---

## フロントエンドワークフロー認証エラー

### 問題: Frontend deployment fails with credentials error

**症状**:

**AWS**:

```
##[error]Credentials could not be loaded, please check your action inputs:
Could not load credentials from any providers
```

**GCP**:

```
##[error]google-github-actions/auth failed with: the GitHub Action workflow
must specify exactly one of "workload_identity_provider" or "credentials_json"!
```

**原因**:

- フロントエンドデプロイワークフローがOIDC/Workload Identityを使用
- メインデプロイワークフローは静的認証情報（Access Keys / Service Account JSON）を使用
- 認証方法の不一致により、シークレットが見つからない

**解決策**:

**フロントエンドワークフローを静的認証情報に統一**:

1. **AWS**:

```yaml
# Before (OIDC - 失敗)
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }} # ❌ 設定されていない
    aws-region: ${{ env.AWS_REGION }}

# After (Static credentials - 成功)
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }} # ✅
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }} # ✅
    aws-region: ${{ env.AWS_REGION }}
```

2. **GCP**:

```yaml
# Before (Workload Identity - 失敗)
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }} # ❌
    service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }} # ❌

# After (Service Account JSON - 成功)
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_CREDENTIALS }} # ✅

- name: Set up Cloud SDK
  uses: google-github-actions/setup-gcloud@v2
  with:
    project_id: ${{ secrets.GCP_PROJECT_ID }} # ✅
```

---

## サポート

問題が解決しない場合:

1. [GitHub Issues](https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues) で報告
2. エラーログとコマンド出力を添付
3. 実行環境（OS、CLIバージョン等）を明記

**修正履歴**:

- 2026-02-15: AWS Lambda ImportModuleError解決方法追加
- 2026-02-15: GCP Cloud Run 500エラー（環境変数・型エラー）解決方法追加
- 2026-02-15: Azure Functions 500エラー（Cosmos DB）解決方法追加
- 2026-02-15: Azure Functions Flex Consumption Plan特有の問題と解決策追加
- 2026-02-15: フロントエンドワークフロー認証エラー解決方法追加
