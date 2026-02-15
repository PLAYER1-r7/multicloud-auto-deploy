# トラブルシューティングガイド

CI/CDワークフロー実行時に遭遇する可能性のある問題と解決策

## 📋 目次

- [Azure認証問題](#azure認証問題)
- [GCPリソース競合](#gcpリソース競合)
- [フロントエンドAPI接続問題](#フロントエンドapi接続問題)
- [Terraform State管理](#terraform-state管理)
- [権限エラー](#権限エラー)
- [AWS Lambda Runtime Errors](#aws-lambda-runtime-errors)
- [GCP Cloud Run 500 Errors](#gcp-cloud-run-500-errors)
- [Azure Functions 500 Errors](#azure-functions-500-errors)

---

## Azure認証問題

### 問題1: "Authenticating using the Azure CLI is only supported as a User"

**症状**:
```
Error: building account: could not acquire access token to parse claims: 
Authenticating using the Azure CLI is only supported as a User (not a Service Principal).
```

**原因**:
- Azure CLIでログイン後、TerraformがCLI認証を試みるが、Service Principalでは使用不可

**解決策**:

1. **ワークフローから初回Azure Loginを削除**:
```yaml
# この部分をコメントアウト
# - name: Azure Login
#   uses: azure/login@v1
#   with:
#     creds: ${{ secrets.AZURE_CREDENTIALS }}
```

2. **Terraform Providerで明示的に無効化**:
```terraform
provider "azurerm" {
  features {}
  use_cli  = false
  use_msi  = false
  use_oidc = false
}
```

3. **環境変数で認証**:
```yaml
env:
  ARM_CLIENT_ID: ${{ secrets.ARM_CLIENT_ID }}
  ARM_CLIENT_SECRET: ${{ secrets.ARM_CLIENT_SECRET }}
  ARM_SUBSCRIPTION_ID: ${{ secrets.ARM_SUBSCRIPTION_ID }}
  ARM_TENANT_ID: ${{ secrets.ARM_TENANT_ID }}
```

### 問題2: Terraform Wrapper による環境変数の干渉

**症状**:
Terraformの出力や環境変数が正しく渡らない

**解決策**:
```yaml
- name: Setup Terraform
  uses: hashicorp/setup-terraform@v3
  with:
    terraform_version: 1.7.5
    terraform_wrapper: false  # 必須！
```

### 問題3: Azure CLI認証後のTerraform実行エラー

**症状**:
ACR操作のためにAzure CLIログイン後、terraform outputコマンドが失敗

**解決策**:
Terraform outputsをインフラデプロイ時にGitHub Actions outputsに保存：

```yaml
- name: Deploy Infrastructure
  id: terraform
  run: |
    terraform apply -auto-approve
    
    # Terraformからoutputsを取得してGitHub Actionsに保存
    ACR_NAME=$(terraform output -raw container_registry_name)
    echo "acr_name=$ACR_NAME" >> $GITHUB_OUTPUT

- name: Use Output Later
  run: |
    # GitHub Actions outputsから取得
    echo "ACR: ${{ steps.terraform.outputs.acr_name }}"
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
- Terraformがローカルbackendを使用していた
- GitHub Actions実行ごとにクリーンな環境で実行されるため、stateが保存されない
- Terraformが既存リソースを認識できず、毎回新規作成を試みる

**解決策（永続的なremote state）**:

1. **GCSバケットの作成**:
```bash
gcloud storage buckets create gs://multicloud-auto-deploy-tfstate-gcp \
  --location=asia-northeast1 \
  --uniform-bucket-level-access
```

2. **サービスアカウントに権限付与**:
```bash
gcloud storage buckets add-iam-policy-binding gs://multicloud-auto-deploy-tfstate-gcp \
  --member="serviceAccount:github-actions-deploy@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

3. **GCS backendの有効化**:
```terraform
# infrastructure/terraform/gcp/main.tf
terraform {
  backend "gcs" {
    bucket = "multicloud-auto-deploy-tfstate-gcp"
    prefix = "terraform/state"
  }
}
```

4. **既存リソースのインポート（一度だけ実行）**:
```bash
cd infrastructure/terraform/gcp

# Terraformの初期化
terraform init

# 既存リソースをインポート
terraform import google_artifact_registry_repository.main \
  "projects/PROJECT_ID/locations/REGION/repositories/REPO_NAME"

terraform import google_storage_bucket.frontend "BUCKET_NAME"

terraform import google_compute_global_address.frontend \
  "projects/PROJECT_ID/global/addresses/ADDRESS_NAME"

terraform import google_firestore_database.main \
  "projects/PROJECT_ID/databases/(default)"

terraform import google_cloud_run_v2_service.api \
  "projects/PROJECT_ID/locations/REGION/services/SERVICE_NAME"

terraform import google_compute_backend_bucket.frontend "BACKEND_BUCKET_NAME"

terraform import google_compute_url_map.frontend \
  "projects/PROJECT_ID/global/urlMaps/URLMAP_NAME"

terraform import google_compute_target_http_proxy.frontend \
  "projects/PROJECT_ID/global/targetHttpProxies/PROXY_NAME"

terraform import google_compute_global_forwarding_rule.frontend_http \
  "projects/PROJECT_ID/global/forwardingRules/RULE_NAME"

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

## Terraform State管理

### ベストプラクティス

1. **Remote Backend を必ず使用**:
   - AWS: S3 + DynamoDB
   - Azure: Storage Account
   - GCP: GCS

2. **State Locking を有効化**:
   - AWS DynamoDBテーブル
   - Azure Storage Account（自動）
   - GCS（自動）

3. **State の定期バックアップ**:
```bash
# GCSの例
gcloud storage cp gs://tfstate-bucket/terraform/state/default.tfstate \
  ./backups/tfstate-$(date +%Y%m%d-%H%M%S).tfstate
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
export ARM_CLIENT_ID="..."
export AWS_ACCESS_KEY_ID="..."

# Terraformコマンドを実行
cd infrastructure/terraform/azure
terraform init
terraform plan
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
{"message": "Internal Server Error"}
```

- Lambdaを直接呼び出すと成功する
- API Gateway経由だと500エラーになる
- CloudWatch LogsにLambdaの実行ログが記録されない
- CloudWatch MetricsでLambda呼び出し回数が0のまま

**原因**:
Lambda関数のリソースポリシーでSourceArn形式が正しくない。

#### HTTP API vs REST API の違い

| API種類 | SourceArn形式 | 例 |
|---------|--------------|-----|
| **HTTP API** | `arn:aws:execute-api:{region}:{account-id}:{api-id}/*/*` | `arn:aws:execute-api:ap-northeast-1:123456789012:abc123def4/*/*` |
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

## サポート

問題が解決しない場合:

1. [GitHub Issues](https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues) で報告
2. エラーログとコマンド出力を添付
3. 実行環境（OS、CLIバージョン等）を明記

**修正履歴**:
- 2026-02-15: AWS Lambda ImportModuleError解決方法追加
- 2026-02-15: GCP Cloud Run 500エラー（環境変数・型エラー）解決方法追加
- 2026-02-15: Azure Functions 500エラー（Cosmos DB）解決方法追加
