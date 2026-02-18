# Troubleshooting Guide

本番環境デプロイで遭遇した問題と解決策のナレッジベース。

## 🚀 クイック診断フローチャート

```
デプロイが失敗した？
  │
  ├─ GitHub Actions エラー？
  │   ├─ YAML構文エラー → [GitHub Actions YAML構文エラー](#github-actions-yaml構文エラー)
  │   ├─ シークレット参照エラー → [GitHub Actionsシークレット参照エラー](#github-actionsシークレット参照エラー)
  │   └─ ワークフローがトリガーされない → [ワークフローがトリガーされない](#github-actionsワークフローがトリガーされない)
  │
  ├─ AWS エラー？
  │   ├─ Lambda Layer権限エラー → [AWS Lambda Layer権限エラー](#aws-lambda-layer権限エラー)
  │   ├─ ResourceConflictException → [AWS Lambda ResourceConflictException](#aws-lambda-resourceconflictexception)
  │   ├─ CloudFrontエラー → [CloudFront IDの取得とキャッシュ無効化](#cloudフロントidの取得とキャッシュ無効化)
  │   ├─ Lambda依存関係エラー → [Lambda Layerビルド時の依存関係エラー](#lambda-layerビルド時の依存関係エラー)
  │   └─ Lambda ImportModuleError → [AWS Lambda Runtime Errors](#aws-lambda-runtime-errors)
  │
  ├─ Azure エラー？
  │   ├─ CORS設定の名前競合 → [Azure CORS設定の名前競合](#azure-cors設定の名前競合)
  │   ├─ リソースが見つからない → [Azureリソース名のハードコード問題](#azureリソース名のハードコード問題)
  │   ├─ デプロイメント競合 → [Azure Function Appデプロイメント競合](#azure-function-appデプロイメント競合)
  │   ├─ Front Doorエンドポイント取得 → [Azure Front Doorエンドポイント取得](#azure-front-doorエンドポイント取得)
  │   ├─ Partially Successful → [Azure Flex Consumption: Partially Successful](#azure-flex-consumption-partially-successful)
  │   ├─ defaultHostName null → [Azure Flex Consumption: defaultHostName null](#azure-flex-consumption-defaulthostname-null)
  │   └─ Kudu再起動 → [Azure Flex Consumption: Kudu再起動](#azure-flex-consumption-kudu再起動)
  │
  ├─ GCP エラー？
  │   ├─ Cloud Run 500エラー → [GCP Cloud Run 500 Errors](#gcp-cloud-run-500-errors)
  │   └─ Firestore 403エラー → [GCP権限エラー](#gcp権限エラー)
  │
  └─ Pulumi エラー？
      ├─ スタックが見つからない → [Pulumiスタックとディレクトリの混同](#pulumiスタックとディレクトリの混同)
      ├─ パスワード/パスフレーズエラー → [Pulumiパスワード・パスフレーズエラー](#pulumiパスワードパスフレーズエラー)
      └─ リソース競合 → [GCPリソース競合](#gcpリソース競合)
```

## 📊 エラーメッセージ別インデックス

素早く解決策を見つけるために、エラーメッセージから検索してください。

| エラーメッセージ                                      | 問題                     | セクション                                                           |
| ----------------------------------------------------- | ------------------------ | -------------------------------------------------------------------- |
| `mapping values are not allowed in this context`      | YAML構文エラー           | [GitHub Actions YAML](#github-actions-yaml構文エラー)                |
| `Application setting already exists`                  | CORS設定の競合           | [Azure CORS設定](#azure-cors設定の名前競合)                          |
| `AZURE_COSMOS_DATABASE value is null`                 | Azure CLI書式問題        | [Azure CLI --settings書式](#azure-cli---settings-yaml-multi-line書式問題) |
| `environment variables all null`                      | Azure CLI書式問題        | [Azure CLI --settings書式](#azure-cli---settings-yaml-multi-line書式問題) |
| `AccessDeniedException ... PublishLayerVersion`       | Lambda Layer権限不足     | [Lambda Layer権限](#aws-lambda-layer権限エラー)                      |
| `ResourceConflictException ... update is in progress` | Lambda更新の競合         | [Lambda ResourceConflict](#aws-lambda-resourceconflictexception)     |
| `Resource ... not found`                              | リソース名のハードコード | [Azureリソース名](#azureリソース名のハードコード問題)                |
| `Deployment was cancelled and another deployment`     | 同時デプロイ             | [Azure デプロイメント競合](#azure-function-appデプロイメント競合)    |
| `pathspec ... did not match any files`                | Gitパス問題              | [Gitパス問題](#モノレポ構造でのgitパス問題)                          |
| `no stack named ... found`                            | Pulumiディレクトリ       | [Pulumiスタック](#pulumiスタックとディレクトリの混同)                |
| `invalid character ... after object key:value pair`   | JSON構文エラー           | [環境変数エスケープ](#環境変数の引用符とエスケープ)                  |
| `invalid CloudFront distribution ids`                 | CloudFront ID            | [CloudFront](#cloudフロントidの取得とキャッシュ無効化)               |
| `Could not find a version that satisfies`             | pip依存関係              | [Lambda Layer依存関係](#lambda-layerビルド時の依存関係エラー)        |
| `unrecognized named-value: 'secrets'`                 | シークレット参照         | [GitHub Secretsエラー](#github-actionsシークレット参照エラー)        |
| `Deployment was partially successful`                 | Azure Flex特有           | [Partially Successful](#azure-flex-consumption-partially-successful) |
| `defaultHostName returns null`                        | Azure Flex特有           | [defaultHostName null](#azure-flex-consumption-defaulthostname-null) |
| `Kudu has been restarted`                             | Azure Flex特有           | [Kudu再起動](#azure-flex-consumption-kudu再起動)                     |
| `Runtime.ImportModuleError`                           | Lambda entrypoint        | [Lambda ImportError](#aws-lambda-runtime-errors)                     |
| `ConnectionRefusedError: [Errno 111]`                 | GCP環境変数未設定        | [GCP Cloud Run 500](#gcp-cloud-run-500-errors)                       |

## 📑 目次

### クラウド別トラブルシューティング

#### AWS

- [AWS Lambda Layer権限エラー](#aws-lambda-layer権限エラー)
- [AWS Lambda ResourceConflictException](#aws-lambda-resourceconflictexception)
- [AWS Lambda Runtime Errors](#aws-lambda-runtime-errors)
- [CloudフロントIDの取得とキャッシュ無効化](#cloudフロントidの取得とキャッシュ無効化)
- [Lambda Layerビルド時の依存関係エラー](#lambda-layerビルド時の依存関係エラー)

#### Azure

- [Azure CORS設定の名前競合](#azure-cors設定の名前競合)
- [Azure CLI --settings YAML Multi-line書式問題](#azure-cli---settings-yaml-multi-line書式問題)
- [Azure環境変数の予約名問題](#azure環境変数の予約名問題) ⚠️ 誤解だったケース
- [Azure Front Doorエンドポイント取得](#azure-front-doorエンドポイント取得)
- [Azureリソース名のハードコード問題](#azureリソース名のハードコード問題)
- [Azure Function Appデプロイメント競合](#azure-function-appデプロイメント競合)
- [Azure Flex Consumption: Partially Successful](#azure-flex-consumption-partially-successful)
- [Azure Flex Consumption: defaultHostName null](#azure-flex-consumption-defaulthostname-null)
- [Azure Flex Consumption: Kudu再起動](#azure-flex-consumption-kudu再起動)

#### GCP

- [GCP Cloud Run 500 Errors](#gcp-cloud-run-500-errors)
- [GCP権限エラー](#gcp権限エラー)
- [GCPリソース競合](#gcpリソース競合)

### 共通問題

- [GitHub Actions YAML構文エラー](#github-actions-yaml構文エラー)
- [GitHub Actionsシークレット参照エラー](#github-actionsシークレット参照エラー)
- [GitHub Actionsワークフローがトリガーされない](#github-actionsワークフローがトリガーされない)
- [モノレポ構造でのGitパス問題](#モノレポ構造でのgitパス問題)
- [Pulumiスタックとディレクトリの混同](#pulumiスタックとディレクトリの混同)
- [Pulumiパスワード・パスフレーズエラー](#pulumiパスワードパスフレーズエラー)
- [環境変数の引用符とエスケープ](#環境変数の引用符とエスケープ)
- [CORS Originsの設定ミスとプリフライトエラー](#cors-originsの設定ミスとプリフライトエラー)
- [認証プロバイダーの設定と環境変数](#認証プロバイダーの設定と環境変数)

---

## ⏱️ 5分で解決：よくある問題トップ5

### 1. 🔴 Azure Functions: "Partially Successful" だが動作する

**即座の解決策**: これは正常です。ヘルスチェックをパスすれば無視してOK。詳細は[こちら](#azure-flex-consumption-partially-successful)

### 2. 🔴 AWS Lambda: "ResourceConflictException"

**即座の解決策**: Lambda関数のステータスが`Active`になるまで待機（2-10秒）。詳細は[こちら](#aws-lambda-resourceconflictexception)

### 3. 🔴 Azure: "Application setting already exists"

**即座の解決策**: 設定を削除してから再設定。`az functionapp config appsettings delete` → `set`。詳細は[こちら](#azure-cors設定の名前競合)

### 4. 🔴 Pulumi: "no stack named 'staging' found"

**即座の解決策**: 正しいディレクトリに移動。`cd infrastructure/pulumi/[aws|azure|gcp]`。詳細は[こちら](#pulumiスタックとディレクトリの混同)

### 5. 🔴 GitHub Actions: "YAML構文エラー"

**即座の解決策**: `cat << EOF` を `echo` に置き換え、または `cat << 'EOF'` で引用符をエスケープ。詳細は[こちら](#github-actions-yaml構文エラー)

---

## Azure Flex Consumption: Partially Successful

**解決時間**: ⏱️ 2分

### 症状

```
ERROR: Deployment was partially successful. These are the deployment logs:
[***"message": "The logs you are looking for were not found. In flex consumption plans,
the instance will be recycled and logs will not be persisted after that..."***]
```

しかし、Function Appは実際には正常に動作している。

### 原因

- Azure Flex Consumptionプランではインスタンスがリサイクルされ、デプロイログが保持されない
- `az functionapp deployment source config-zip`が"partially successful"を返すが、実際にはデプロイは成功している
- 詳細なステップログ（`UploadPackageStep`, `OryxBuildStep`等）が出力されない

### 解決策

1. **"Deployment was successful"メッセージを検出**:

```bash
# 成功メッセージを最優先でチェック
if grep -q "Deployment was successful" deploy_log.txt; then
  echo "✅ Deployment successful!"
  DEPLOY_SUCCESS=true
  break
fi
```

2. **"partially successful"を無視**:

```bash
# "partially successful"を無視し、critical errorのみ失敗扱い
elif grep -q "ERROR:" deploy_log.txt && ! grep -q "partially successful" deploy_log.txt; then
  echo "❌ Critical deployment error"
  cat deploy_log.txt
  exit 1
fi
```

3. **ヘルスチェックを必須検証に**:

```bash
# デプロイ後のヘルスチェックで最終確認
curl -f -s -o /dev/null -w "%{http_code}" "$FUNC_URL/health"
if [ $? -eq 0 ]; then
  echo "✅ Health check passed!"
else
  echo "❌ Health check failed"
  exit 1
fi
```

### ベストプラクティス

- "Partially Successful"は**正常な挙動**として扱う
- デプロイ完了の判定はヘルスチェックで行う
- Flex Consumptionプランでは詳細ログが取得できないことを前提にする

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 280-310)

---

## Azure Flex Consumption: defaultHostName null

**解決時間**: ⏱️ 1分

### 症状

```
Testing: https:///api/HttpTrigger/health
❌ Health check failed
```

`az functionapp show --query defaultHostName`がnullを返し、URLが空になる。

### 原因

Flex Consumptionプランでは`defaultHostName`フィールドがnullまたは未設定。

### 解決策

**`az functionapp config hostname list`を使用**:

```bash
# Flex Consumption対応のホスト名取得
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

### 比較

| コマンド                       | Consumption Y1 | Flex Consumption | Premium EP1 |
| ------------------------------ | -------------- | ---------------- | ----------- |
| `show --query defaultHostName` | ✅ 動作        | ❌ null          | ✅ 動作     |
| `config hostname list`         | ✅ 動作        | ✅ 動作          | ✅ 動作     |

### ベストプラクティス

- すべてのSKUで動作する`config hostname list`を使用
- hostnameが取得できない場合はリトライロジックを実装
- 取得後は必ず空チェック（`-n`）を実施

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 320-330)

---

## Azure Flex Consumption: Kudu再起動

**解決時間**: ⏱️ 5分

### 症状

```
🔄 Kudu restart detected, retrying...
Attempt 2/3...
```

大きなデプロイパッケージでKuduが再起動し、デプロイが中断される。

### 原因

- デプロイパッケージに不要なファイル（`__pycache__`, `.pyc`, `tests`, `.dist-info`）が含まれサイズが大きい
- Flex Consumptionプランの動的スケーリングによりKuduインスタンスが再起動
- リトライロジックが未実装

### 解決策

#### 1. パッケージサイズの最適化

```bash
# 依存関係インストール
pip install --target .deployment --no-cache-dir -r requirements.txt

# 不要ファイルの削除
find .deployment -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find .deployment -type f -name "*.pyc" -delete 2>/dev/null || true
find .deployment -type f -name "*.pyo" -delete 2>/dev/null || true
find .deployment -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find .deployment -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# ZIP作成（quietモード）
cd .deployment
zip -r -q ../function-app.zip .

echo "✅ Package size: $(du -h ../function-app.zip | cut -f1)"
```

#### 2. リトライロジックの実装

```bash
MAX_RETRIES=3
RETRY_COUNT=0
DEPLOY_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  echo "Attempt $((RETRY_COUNT+1))/$MAX_RETRIES..."

  # デプロイ実行
  az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP \
    --src services/api/function-app.zip \
    --timeout 600 \
    2>&1 | tee deploy_log.txt || true

  # Kudu再起動を検出
  if grep -q "Kudu has been restarted" deploy_log.txt; then
    echo "🔄 Kudu restart detected, retrying..."
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 30  # Kudu安定化待ち
    continue
  fi

  # 成功判定
  if grep -q "Deployment was successful" deploy_log.txt; then
    DEPLOY_SUCCESS=true
    break
  fi

  # 失敗時は非Kuduエラーとして即座に終了
  if grep -q "ERROR:" deploy_log.txt && ! grep -q "Kudu\|partially successful" deploy_log.txt; then
    echo "❌ Non-transient error detected"
    cat deploy_log.txt
    exit 1
  fi

  RETRY_COUNT=$((RETRY_COUNT+1))
  sleep 30
done

if [ "$DEPLOY_SUCCESS" = false ]; then
  echo "❌ Deployment failed after $MAX_RETRIES attempts"
  exit 1
fi
```

### パッケージサイズの目安

| 最適化前 | 最適化後 | 削減率 |
| -------- | -------- | ------ |
| 45 MB    | 28 MB    | 38%    |

### ベストプラクティス

- パッケージサイズは30MB以下を目標
- `--no-cache-dir`を使用してpipキャッシュを削除
- リトライ間隔は30秒（Kuduの安定化時間）
- 最大3回までリトライ

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 260-295)

---

## AWS Lambda Runtime Errors

**解決時間**: ⏱️ 3分

### 症状

```
[ERROR] Runtime.ImportModuleError: Unable to import module 'index': No module named 'index'
```

### 原因

- GitHub Actionsワークフローが`handler.py`を動的生成
- Lambda関数設定では`index.handler`を期待
- ファイル名のミスマッチ

### 解決策

**既存の`index.py`をコピー**:

```yaml
# ❌ 動的生成（削除）
# cat > package/handler.py << 'EOF'
# from mangum import Mangum
# from app.main import app
# handler = Mangum(app, lifespan="off")
# EOF

# ✅ 既存ファイルをコピー
- name: Package Lambda Function
  run: |
    cd services/api
    cp index.py package/
    cp -r app package/
    cd package
    zip -r ../lambda.zip .
```

### `index.py`の内容

```python
"""AWS Lambda エントリーポイント"""
from mangum import Mangum
from app.main import app

# Lambda handler
handler = Mangum(app, lifespan="off")
```

### 確認方法

```bash
# Zipの中身確認
unzip -l lambda.zip | grep -E "(index.py|handler.py)"

# Lambda設定確認
aws lambda get-function-configuration \
  --function-name YOUR_FUNCTION_NAME \
  --query 'Handler'
# 出力: "index.handler"
```

### 該当ファイル

- `.github/workflows/deploy-aws.yml` (lines 200-220)
- `services/api/index.py`

---

## GCP Cloud Run 500 Errors

**解決時間**: ⏱️ 2分

### 症状

```
ConnectionRefusedError: [Errno 111] Connection refused
File "/workspace/app/backends/local.py", line 30, in __init__
  self._ensure_bucket()
```

### 原因

`CLOUD_PROVIDER`環境変数が未設定で、アプリケーションがLocalBackend（MinIO localhost:9000）を使用しようとする。

### 解決策

**環境変数を設定**:

```bash
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --set-env-vars="ENVIRONMENT=staging,CLOUD_PROVIDER=gcp,GCP_PROJECT_ID=$PROJECT_ID,FIRESTORE_COLLECTION=messages"
```

### 環境変数チェックリスト

| 環境変数               | 必須 | 例               | 用途                  |
| ---------------------- | ---- | ---------------- | --------------------- |
| `CLOUD_PROVIDER`       | ✅   | `gcp`            | バックエンド選択      |
| `GCP_PROJECT_ID`       | ✅   | `my-project-123` | Firestoreプロジェクト |
| `FIRESTORE_COLLECTION` | ✅   | `messages`       | コレクション名        |
| `ENVIRONMENT`          | ⚠️   | `staging`        | ログレベル            |

### 確認方法

```bash
# 環境変数確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(spec.template.spec.containers[0].env)"

# ログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit 10 \
  --format="table(timestamp,textPayload)"
```

### 該当ファイル

- `.github/workflows/deploy-gcp.yml` (lines 190-200)

---

## GCP権限エラー

**解決時間**: ⏱️ 5分

### Firestore Permission Denied

**症状**:

```
Error: Error creating database: googleapi: Error 403:
The caller does not have permission
```

**解決策**:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.owner"
```

### Cloud Run Permission Denied

**症状**:

```
Error 403: Permission 'run.services.setIamPolicy' denied
```

**解決策**:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

### 必要な権限一覧

| サービス          | ロール                          | 用途             |
| ----------------- | ------------------------------- | ---------------- |
| Cloud Run         | `roles/run.admin`               | サービス管理     |
| Firestore         | `roles/datastore.owner`         | データベース管理 |
| Artifact Registry | `roles/artifactregistry.writer` | コンテナプッシュ |
| Storage           | `roles/storage.admin`           | バケット管理     |

### 確認方法

```bash
# サービスアカウントの権限確認
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:github-actions-deploy@*"
```

---

## GCPリソース競合

**解決時間**: ⏱️ 10分（初回セットアップ）

### 症状

```
Error: Error creating Repository: googleapi: Error 409: the repository already exists.
Error: Error creating Service: googleapi: Error 409: Resource already exists.
```

### 原因

- Pulumiがローカルstateファイルを使用
- GitHub Actions実行ごとにクリーンな環境でstateが保存されない
- 既存リソースを認識できず、毎回新規作成を試みる

### 解決策（Remote State使用）

#### 1. GCSバケット作成

```bash
gcloud storage buckets create gs://multicloud-auto-deploy-pulumi-state-gcp \
  --location=asia-northeast1 \
  --uniform-bucket-level-access
```

#### 2. サービスアカウントに権限付与

```bash
gcloud storage buckets add-iam-policy-binding gs://multicloud-auto-deploy-pulumi-state-gcp \
  --member="serviceAccount:github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

#### 3. Pulumi backendの設定

```bash
# GCS backendにログイン
pulumi login gs://multicloud-auto-deploy-pulumi-state-gcp

# または環境変数で設定
export PULUMI_BACKEND_URL="gs://multicloud-auto-deploy-pulumi-state-gcp"
```

#### 4. GitHub Actionsワークフローで設定

```yaml
- name: Configure Pulumi
  run: |
    pulumi login gs://multicloud-auto-deploy-pulumi-state-gcp
```

### ベストプラクティス

- **AWS**: S3バケット (`pulumi login s3://bucket-name`)
- **Azure**: Blob Storage (`pulumi login azblob://container`)
- **GCP**: GCS (`pulumi login gs://bucket-name`)
- **推奨**: Pulumi Service (`pulumi login`)（最も簡単）

---

## GitHub Actions YAML構文エラー

### 症状

```
Error: .github/workflows/deploy-*.yml: mapping values are not allowed in this context
```

ワークフロー実行時にYAML構文エラーでパース失敗。

### 原因

GitHub Actions YAMLパーサーとbash here-document構文（`cat << EOF`）の競合。
YAMLの特殊文字（`:`、`{}`など）がhere-document内で解釈されてしまう。

### 解決策

here-documentを使わず、`echo`コマンドでファイルを構築する：

**❌ 動作しない例:**

```yaml
- name: Create config
  run: |
    cat << EOF > config.yaml
    key: value
    nested:
      key2: value2
    EOF
```

**✅ 正しい例:**

```yaml
- name: Create config
  run: |
    echo "key: value" > config.yaml
    echo "nested:" >> config.yaml
    echo "  key2: value2" >> config.yaml
```

または完全に引用符でエスケープ：

```yaml
- name: Create config
  run: |
    cat << 'EOF' > config.yaml
    key: value
    nested:
      key2: value2
    EOF
```

### 該当ファイル

- `.github/workflows/deploy-gcp.yml` (lines 172-179)
- `.github/workflows/deploy-aws.yml` (lines 247-258)

---

## Azure CORS設定の名前競合

**解決時間**: ⏱️ 2分

### 症状

```
ERROR: Application setting 'CORS_ORIGINS' already exists.
Choose --overwrite if you want to change the value
```

Azure Function Appに`CORS_ORIGINS`を設定しようとすると「既に存在する」エラー。
しかし設定一覧（`--output table`）には表示されない。

### 原因

Azureは設定名の**大文字・小文字を区別しない**。
以前に小文字`cors_origins`が設定されていると、大文字`CORS_ORIGINS`を追加できない。

### 解決策（3ステップ）

#### 1. 既存設定を確認

```bash
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --query "[?contains(name, 'cors')]" \
  --output table
```

#### 2. 両方の名前を削除

```bash
az functionapp config appsettings delete \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --setting-names CORS_ORIGINS cors_origins 2>/dev/null || true

sleep 3  # 削除の伝播待ち
```

#### 3. 新しい設定を追加

```bash
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings CORS_ORIGINS="$CORS_ORIGINS"
```

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 257-265)

### ベストプラクティス

- Azure CLIは`--overwrite`フラグをサポートしていない
- 常に`delete` → `set`のパターンを使う
- 設定変更後は`sleep 3`で伝播待ち

---

## Azure CLI --settings YAML Multi-line書式問題

**解決時間**: ⏱️ 3時間（デバッグ）→ 5分（修正）  
**試行回数**: 12回のデプロイメント

### 症状

```bash
# Bashでは正しい値が表示される
echo "DATABASE=${COSMOS_DATABASE}"  # Output: messages

# しかしAzure Function Appの環境変数は全てnullになる
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    COSMOS_DB_DATABASE="${COSMOS_DATABASE}" \
    COSMOS_DB_CONTAINER="${COSMOS_CONTAINER}"

# 結果確認
az functionapp config appsettings list ... | jq '.[] | {name, value}'
# Output: {"name": "COSMOS_DB_DATABASE", "value": null}
# Output: {"name": "COSMOS_DB_CONTAINER", "value": null}

# ハードコード値でも同様にnull
az functionapp config appsettings set --settings COSMOS_DB_DATABASE=messages
# Output: {"name": "COSMOS_DB_DATABASE", "value": null}
```

**全ての環境変数が常に`null`になる。** ハードコード文字列でも、変数展開でも、引用符の有無に関わらず、常にnull。

### 誤った仮説（試行錯誤の過程）

❌ **仮説1: 変数名が予約語**
- `AZURE_COSMOS_DATABASE` → `COSMOS_DB_DATABASE` に変更
- 結果: 変わらずnull（10分の試行）

❌ **仮説2: 変数展開の問題**  
- `"${VAR}"` → `'${VAR}'` → `$VAR` と様々な引用符を試行
- 結果: 変わらずnull（20分の試行）

❌ **仮説3: 複数の--settingsフラグの競合**
- 2つの`--settings`を1つに統合
- 結果: 変わらずnull（15分の試行）

❌ **仮説4: YAML multi-lineが原因**
- 全てを1行に書き換え（読みにくい長大な行）
- 結果: 変わらずnull（30分の試行）

❌ **仮説5: GitHub Actions環境の問題**
- ローカルで同じコマンドを試行しようとするも権限エラー
- 結果: 確認できず（15分の試行）

### 真の原因

**YAML multi-lineの書式が間違っていた。**

```yaml
# ❌ 間違い - 継続行が適切にインデントされていない
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
    KEY1=value1 \
    KEY2=value2

# これはYAMLとして以下のように解釈される:
# "--settings \ KEY1=value1 \ KEY2=value2"
# （バックスラッシュとスペースが含まれてしまう）

# ✅ 正しい - 適切なインデント付き
az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    KEY1=value1 \
    KEY2=value2 \
    KEY3=value3
```

**重要**: GitHub Actions YAMLでは、`\` による継続行の後のインデントが重要。インデントがない場合、Azure CLIは引数を正しくパースできない。

### 解決策

#### 修正前（全て null になる）

```yaml
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings COSMOS_DB_ENDPOINT="${COSMOS_ENDPOINT}" COSMOS_DB_KEY="${COSMOS_KEY}" COSMOS_DB_DATABASE="${COSMOS_DATABASE}" COSMOS_DB_CONTAINER="${COSMOS_CONTAINER}" AUTH_PROVIDER=azure
```

または

```yaml
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
COSMOS_DB_ENDPOINT="${COSMOS_ENDPOINT}" \
COSMOS_DB_KEY="${COSMOS_KEY}"
```

#### 修正後（正常動作）

```yaml
az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    CLOUD_PROVIDER=azure \
    ENVIRONMENT=staging \
    COSMOS_DB_ENDPOINT="$COSMOS_ENDPOINT" \
    COSMOS_DB_KEY="$COSMOS_KEY" \
    COSMOS_DB_DATABASE="$COSMOS_DATABASE" \
    COSMOS_DB_CONTAINER="$COSMOS_CONTAINER" \
    AUTH_PROVIDER=azure \
    AZURE_TENANT_ID="${{ steps.azure_env.outputs.tenant_id }}" \
    AZURE_CLIENT_ID="${{ steps.pulumi_outputs.outputs.azure_ad_client_id }}" \
    CORS_ORIGINS="$CORS_ORIGINS" \
  > /dev/null 2>&1
```

**ポイント**:
- `--settings` の後の各行を**2スペースまたは4スペースでインデント**
- 変数は `"$VAR"` 形式で引用符で囲む
- 各設定は `KEY=value` 形式（スペースなし）

### 検証方法

設定後、必ず以下で確認:

```bash
az functionapp config appsettings list \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  -o json | jq '.[] | select(.name | startswith("COSMOS_DB_")) | {name, value}'
```

期待される出力:
```json
{
  "name": "COSMOS_DB_DATABASE",
  "value": "messages"
}
{
  "name": "COSMOS_DB_CONTAINER",
  "value": "messages"
}
```

### デバッグのノウハウ

1. **ハードコード値でテスト**:
   ```bash
   az functionapp config appsettings set --settings TEST_VAR=hardcoded_value
   ```
   これでもnullなら、構文問題が濃厚。

2. **段階的に変数を減らす**:
   まず1つだけ設定して動作確認。動いたら徐々に増やす。

3. **出力を確認**:
   `> /dev/null` を外して、Azure CLIの実際の出力を確認。

4. **公式ヘルプを確認**:
   ```bash
   az functionapp config appsettings set --help
   ```
   Examples セクションに正しい書式が記載されている。

5. **GitHub Actions固有の問題を除外**:
   ローカルのbashでも同じコマンドを試す（権限があれば）。

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 286-303)

### ベストプラクティス

✅ **推奨する書き方**:
```yaml
az functionapp config appsettings set \
  --name "$VAR" \        # 変数は引用符で囲む
  --settings \           # 改行後はインデント必須
    KEY1=value1 \        # 2-4スペースのインデント
    KEY2="$VAR2" \       # 変数値も引用符で
    KEY3="${{ secrets.SECRET }}"  # GitHub Actionsシークレット
```

❌ **避けるべき書き方**:
```yaml
# 1. インデントなし
az functionapp config appsettings set \
--settings \
KEY1=value1   # ❌ インデントなし

# 2. 超長い1行
az functionapp config appsettings set --settings KEY1=val1 KEY2=val2 ... KEY10=val10  # ❌ 読みにくい

# 3. 引用符なしの変数（スペースを含む値では問題）
--settings KEY=$VAR   # ❌ $VARにスペースがあると分割される
```

### 関連問題

- [GitHub Actions YAML構文エラー](#github-actions-yaml構文エラー) - YAML基本構文
- [環境変数の引用符とエスケープ](#環境変数の引用符とエスケープ) - シェル変数の扱い
- [Azure CORS設定の名前競合](#azure-cors設定の名前競合) - 設定の上書き問題

### 教訓

1. **公式ドキュメントを最初に確認**:  
   `--help` や公式Examples を見れば30分で解決できた問題に3時間費やした。

2. **仮説の優先順位付け**:  
   「変数名が予約語」という珍しいケースから調査するのではなく、「構文問題」という基本から確認すべきだった。

3. **ハードコードテストの重要性**:  
   変数展開を疑う前に、まずハードコード値でテストして切り分けるべき。

4. **段階的デバッグ**:  
   一度に全ての変数を設定するのではなく、1つずつ増やして問題箇所を特定。

5. **ドキュメント化の価値**:  
   同じ問題で悩む人（未来の自分を含む）のために、試行錯誤の過程も含めて記録する。

### 参考: 試行錯誤の完全な履歴

| 試行 | アプローチ                     | 結果 | 所要時間 |
| ---- | ------------------------------ | ---- | -------- |
| 1-3  | AZURE_COSMOS_* → COSMOS_DB_*   | ❌   | 30分     |
| 4-5  | 引用符のバリエーション         | ❌   | 20分     |
| 6    | --settingsフラグ統合           | ❌   | 15分     |
| 7-8  | ハードコード値テスト           | ❌   | 20分     |
| 9-10 | 1行形式に書き換え              | ❌   | 30分     |
| 11   | 公式ヘルプ確認 → インデント発見 | ✅   | 5分      |
| 12   | 正しい書式でデプロイ           | ✅   | 8分      |

**合計**: 約3時間のデバッグ + 12回のデプロイメント（各8-10分）= **約5時間**

---

## Azure環境変数の予約名問題

> ⚠️ **注意**: この問題は最終的に**誤解**であることが判明しました。
> 真の原因は上記の「[Azure CLI --settings YAML Multi-line書式問題](#azure-cli---settings-yaml-multi-line書式問題)」です。
> 以下の内容は、間違った仮説の記録として残しています（同じミスを繰り返さないため）。

**解決時間**: ⏱️ ~~1分（環境変数名変更のみ）~~ → 実際は0分（不要だった）

### 症状

```bash
# Bashでは正しい値を表示
echo "DATABASE=${COSMOS_DATABASE}"  # Output: DATABASE=messages

# しかしAzure CLIでは常にnull
az functionapp config appsettings set --settings AZURE_COSMOS_DATABASE="${COSMOS_DATABASE}"
# Result: {"name": "AZURE_COSMOS_DATABASE", "value": null}

# ハードコード値でもnull
az functionapp config appsettings set --settings AZURE_COSMOS_DATABASE=messages
# Result: {"name": "AZURE_COSMOS_DATABASE", "value": null}
```

**特定の環境変数名がAzure Function Appで常に`null`になる問題。**

### 影響を受ける変数名

以下の環境変数名は**Azure CLIまたはFunction Appで予約されている**可能性があり、使用できません：

❌ **使用不可**:

- `AZURE_COSMOS_DATABASE`
- `AZURE_COSMOS_CONTAINER`

✅ **代替案（正常動作）**:

- `COSMOS_DB_DATABASE`
- `COSMOS_DB_CONTAINER`
- `COSMOS_DB_ENDPOINT`
- `COSMOS_DB_KEY`

### 原因

Azure CLIまたはAzure Function Appの内部で、`AZURE_COSMOS_DATABASE`と`AZURE_COSMOS_CONTAINER`という名前が特別な意味を持つか、予約されている可能性があります。

**検証結果**:

- ✅ `AZURE_COSMOS_ENDPOINT` → 正常に設定可能
- ✅ `AZURE_COSMOS_KEY` → 正常に設定可能
- ❌ `AZURE_COSMOS_DATABASE` → 常にnull（ハードコード値でも）
- ❌ `AZURE_COSMOS_CONTAINER` → 常にnull（ハードコード値でも）
- ✅ `COSMOS_DB_DATABASE` → 正常に設定可能
- ✅ `COSMOS_DB_CONTAINER` → 正常に設定可能

### 解決策（推奨）

#### 1. 環境変数名を変更

`.github/workflows/deploy-azure.yml`:

```yaml
az functionapp config appsettings set \
--settings \
COSMOS_DB_ENDPOINT="${COSMOS_ENDPOINT}" \
COSMOS_DB_KEY="${COSMOS_KEY}" \
COSMOS_DB_DATABASE="${COSMOS_DATABASE}" \
COSMOS_DB_CONTAINER="${COSMOS_CONTAINER}"
```

#### 2. config.pyで両方をサポート（互換性維持）

`services/api/app/config.py`:

```python
from pydantic import Field, AliasChoices

cosmos_db_database: str = Field(
    default="simple-sns",
    validation_alias=AliasChoices("cosmos_db_database", "azure_cosmos_database")
)
cosmos_db_container: str = Field(
    default="items",
    validation_alias=AliasChoices("cosmos_db_container", "azure_cosmos_container")
)
```

これにより、`COSMOS_DB_*`と`AZURE_COSMOS_*`の両方の名前をサポートできます。

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 290-295)
- `services/api/app/config.py` (lines 44-62)
- `services/api/app/backends/factory.py` (lines 27-30)

### ベストプラクティス

⚠️ **重要**: Azure Function Appで環境変数を設定する際の命名規則

1. **避けるべきプレフィックス**:
   - `AZURE_COSMOS_*` (DATABASE, CONTAINERは予約済み)
   - その他のAzure内部変数と競合する可能性のある名前

2. **推奨プレフィックス**:
   - `COSMOS_DB_*` - Cosmos DB関連
   - `APP_*` - アプリケーション固有
   - `CUSTOM_*` - カスタム設定

3. **検証方法**:

   ```bash
   # 設定後に必ず確認
   az functionapp config appsettings list \
     --name $FUNCTION_APP \
     --resource-group $RESOURCE_GROUP \
     -o json | jq '.[] | select(.name | startswith("COSMOS")) | {name, value}'
   ```

4. **エラーメッセージの更新**:
   ユーザーに正しい変数名を案内するため、エラーメッセージも更新：
   ```python
   raise ValueError(
       "Set COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables. "
       "(Note: AZURE_COSMOS_* names are reserved and cannot be used)"
   )
   ```

### 関連問題

- [Azure CORS設定の名前競合](#azure-cors設定の名前競合) - 大文字小文字の区別問題
- [環境変数の引用符とエスケープ](#環境変数の引用符とエスケープ) - 値の展開問題

### 参考情報

この問題は10回以上のデプロイメント試行を経て、ハードコード値でもnullになることを確認して発見されました。
Azureの公式ドキュメントには明記されていませんが、実運用では`COSMOS_DB_*`プレフィックスの使用を強く推奨します。

---

## AWS Lambda Layer権限エラー

**解決時間**: ⏱️ 5分

### 症状

```
An error occurred (AccessDeniedException) when calling the PublishLayerVersion operation:
User: arn:aws:iam::ACCOUNT:user/USER is not authorized to perform:
lambda:PublishLayerVersion on resource: arn:aws:lambda:REGION:ACCOUNT:layer:NAME
```

### 原因

IAMユーザーにLambda Layer関連の権限がない。

**必要な権限:**

1. **カスタムLayerを作成**する場合: `lambda:PublishLayerVersion`
2. Layer削除: `lambda:DeleteLayerVersion`
3. Layerバージョン取得: `lambda:GetLayerVersion`

### 解決策

#### 1. IAMポリシーの更新

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaLayerPermissions",
      "Effect": "Allow",
      "Action": [
        "lambda:PublishLayerVersion",
        "lambda:GetLayerVersion",
        "lambda:DeleteLayerVersion",
        "lambda:ListLayerVersions"
      ],
      "Resource": [
        "arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-*",
        "arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-*:*"
      ]
    }
  ]
}
```

#### 2. ポリシーバージョンの作成

```bash
aws iam create-policy-version \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/GitHubActionsDeploymentPolicy \
  --policy-document file://iam-policy-github-actions.json \
  --set-as-default
```

### 該当ファイル

- `.github/workflows/deploy-aws.yml`
- `infrastructure/aws/iam-policy-github-actions.json`

### ベストプラクティス

- **カスタムLayer使用**: 確実に動作し、完全な制御が可能
- **boto3除外**: Lambdaランタイムに含まれるため除外してサイズ削減
- **直接アップロード**: 50MB未満を維持してS3不要

---

## AWS Lambda パッケージサイズ超過（RequestEntityTooLargeException）

### 症状

```
An error occurred (RequestEntityTooLargeException) when calling the UpdateFunctionCode operation:
Request must be smaller than 69905067 bytes for the UpdateFunctionCode operation
```

Lambda関数の直接アップロードが50MBを超えて失敗。

### 原因

- Lambda関数のZIPファイルが50MBを超えている
- 依存関係がLambda関数コードに含まれている

### 解決策

#### 1. カスタムLambda Layerを使用

依存関係をLayerに分離してLambda関数コードを軽量化：

```bash
# Layer をビルド
cd /workspaces/ashnova/multicloud-auto-deploy
./scripts/build-lambda-layer.sh

# Layer をデプロイ
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "Dependencies for FastAPI + Mangum + JWT (Python 3.12)" \
  --zip-file fileb://services/api/lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1
```

#### 2. アプリケーションコードのみをパッケージング

```bash
cd services/api
rm -rf .build lambda.zip
mkdir -p .build/package

# アプリケーションコードのみコピー（依存関係は除外）
cp -r app .build/package/
cp index.py .build/package/

# ZIPファイル作成
cd .build/package
zip -r ../../lambda.zip .
cd ../..
```

#### 3. 最適化結果

- **Layer（依存関係）**: ~8-10MB
- **Lambda関数（アプリケーションのみ）**: ~78KB
- **合計**: 50MB未満（直接アップロード可能）

### 該当ファイル

- `.github/workflows/deploy-aws.yml`
- `scripts/build-lambda-layer.sh`
- `services/api/requirements-layer.txt`

### ベストプラクティス

- boto3をレイヤーから除外（Lambdaランタイムに含まれる）
- 不要なファイルを削除（テスト、ドキュメント、.pycなど）
- 直接アップロード優先（S3経由より高速）

---

## AWS Lambda ResourceConflictException

### 症状

```
An error occurred (ResourceConflictException) when calling the UpdateFunctionConfiguration operation:
The operation cannot be performed at this time.
An update is in progress for resource: arn:aws:lambda:REGION:ACCOUNT:function:NAME
```

### 原因

Lambda関数のコード更新（`update-function-code`）が完了する前に、
設定更新（`update-function-configuration`）を実行しようとした。

Lambdaは**同時に複数の更新操作を受け付けない**。

### 解決策

Lambda関数のステータスが`Active`になるまで待機する：

```yaml
- name: Update Lambda Function
  run: |
    # コード更新
    aws lambda update-function-code \
      --function-name $LAMBDA_FUNCTION \
      --zip-file fileb://lambda.zip

    # ステータス確認ループ
    echo "⏳ Waiting for Lambda function to become Active..."
    MAX_WAIT=60
    WAIT_COUNT=0
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
      STATUS=$(aws lambda get-function \
        --function-name $LAMBDA_FUNCTION \
        --query 'Configuration.State' \
        --output text)
      
      if [ "$STATUS" == "Active" ]; then
        echo "✅ Lambda function is Active"
        break
      fi
      
      echo "  Status: $STATUS, waiting... ($((WAIT_COUNT+1))/$MAX_WAIT)"
      sleep 2
      WAIT_COUNT=$((WAIT_COUNT+1))
    done

    # 設定更新
    aws lambda update-function-configuration \
      --function-name $LAMBDA_FUNCTION \
      --layers $LAYER_ARNS \
      --environment file://env.json
```

### Lambda関数の状態遷移

```
Pending → Active
         ↓
       (Update)
         ↓
Pending → Active
```

`update-function-code`実行後: `Pending` → `Active` （通常2-5秒）

### 該当ファイル

- `.github/workflows/deploy-aws.yml` (lines 237-261)

### 関連コマンド

```bash
# 現在の状態を確認
aws lambda get-function \
  --function-name <name> \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}'

# 可能な状態:
# - Pending: 更新処理中
# - Active: 正常稼働
# - Inactive: 非アクティブ
# - Failed: 更新失敗
```

---

## Azure Front Doorエンドポイント取得

### 症状

```
ERROR: Resource 'multicloud-auto-deploy-staging-endpoint' not found.
```

Front Doorのエンドポイント名を直接指定して取得しようとするとエラー。

### 原因

Azure Front Door（Standard/Premium）のエンドポイント名は**自動生成**される。
ハードコードされた名前は存在しない可能性が高い。

### 間違った方法

```yaml
# ❌ エンドポイント名を直接指定
FRONTDOOR_HOSTNAME=$(az afd endpoint show \
--endpoint-name multicloud-auto-deploy-staging-endpoint \
--profile-name $FRONTDOOR_PROFILE \
--resource-group $RESOURCE_GROUP \
--query hostName \
--output tsv)
```

### 正しい方法

**Pulumi outputsから取得**する：

```yaml
- name: Get Pulumi Outputs
  id: pulumi_outputs
  run: |
    cd multicloud-auto-deploy/infrastructure/pulumi/azure

    FRONTDOOR_HOSTNAME=$(pulumi stack output frontdoor_hostname)
    echo "frontdoor_hostname=$FRONTDOOR_HOSTNAME" >> $GITHUB_OUTPUT

- name: Configure CORS
  run: |
    FRONTDOOR_URL="${{ steps.pulumi_outputs.outputs.frontdoor_hostname }}"
    CORS_ORIGINS="https://${FRONTDOOR_URL},http://localhost:5173"
```

または、エンドポイントをリストして最初のものを取得：

```bash
# 全エンドポイントをリスト
az afd endpoint list \
  --profile-name $FRONTDOOR_PROFILE \
  --resource-group $RESOURCE_GROUP \
  --query "[0].hostName" \
  --output tsv
```

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 250-252)

### Pulumiでのexport

```python
# infrastructure/pulumi/azure/__main__.py
import pulumi

# Front Door作成
frontdoor = azure_native.cdn.Profile(...)
endpoint = azure_native.cdn.AFDEndpoint(...)

# エンドポイントのホスト名をexport
pulumi.export("frontdoor_hostname", endpoint.host_name)
```

### ベストプラクティス

- インフラのIDや名前は**Pulumiの出力から取得**する
- ハードコードを避ける
- エンドポイント名はリソース作成時に自動生成されることを想定

---

## Azureリソース名のハードコード問題

### 症状

```
ERROR: Resource group 'mcad-staging' could not be found.
```

または：

```
ERROR: The Resource 'Microsoft.Web/sites/mcad-staging-func' not found.
```

Azure CLIコマンドでリソース名やリソースグループ名を指定すると「見つからない」エラー。

### 原因

ワークフロー内で**ハードコードされたリソース名**を使用しているが、実際のPulumiで作成されたリソース名が異なる。

**例:**

- ワークフロー: `mcad-staging-func` @ `mcad-staging`
- 実際: `multicloud-auto-deploy-staging-func` @ `multicloud-auto-deploy-staging-rg`

### 調査方法

```bash
# 1. Pulumiのoutputsを確認（正しい名前が分かる）
cd infrastructure/pulumi/azure
pulumi stack output --json

# 2. Azureリソースを検索
az resource list --resource-group <rg> --output table

# 3. Function Appを検索
az functionapp list --query "[].{name:name, rg:resourceGroup}" --output table
```

### 解決策

**Pulumi outputsから動的に取得**する：

```yaml
- name: Get Pulumi Outputs
  id: pulumi_outputs
  run: |
    cd infrastructure/pulumi/azure

    RESOURCE_GROUP=$(pulumi stack output resource_group_name)
    FUNCTION_APP=$(pulumi stack output function_app_name)

    echo "resource_group_name=$RESOURCE_GROUP" >> $GITHUB_OUTPUT
    echo "function_app_name=$FUNCTION_APP" >> $GITHUB_OUTPUT

- name: Configure Settings
  run: |
    az functionapp config appsettings set \
      --name ${{ steps.pulumi_outputs.outputs.function_app_name }} \
      --resource-group ${{ steps.pulumi_outputs.outputs.resource_group_name }} \
      --settings KEY="value"
```

### Pulumiでのexport

```python
# infrastructure/pulumi/azure/__main__.py
import pulumi

resource_group = azure_native.resources.ResourceGroup("rg", ...)
function_app = azure_native.web.WebApp("func", ...)

# リソース名をexport
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("function_app_name", function_app.name)
```

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 244-265)

### ベストプラクティス

- **すべてのリソース名をPulumi outputsから取得**
- ハードコードは絶対に避ける
- 環境ごと（staging/production）に異なる命名規則を想定

---

## Azure Function App デプロイメント競合

### 症状

```
ERROR: Deployment was cancelled and another deployment is in progress.
```

Function Appへのzipデプロイが失敗し、「別のデプロイメントが進行中」エラー。

### 原因

Azure Function Appは**同時に1つのデプロイしか受け付けない**。

以下の場合に発生：

1. 前回のデプロイメントがまだ完了していない
2. 設定変更（`az functionapp config appsettings set`）直後にデプロイ
3. Kuduサービスの再起動中

### 解決策

**リトライロジック**を実装する：

```yaml
- name: Deploy Function App
  run: |
    MAX_RETRIES=3
    RETRY_COUNT=0
    DEPLOY_SUCCESS=false

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
      echo "Attempt $((RETRY_COUNT+1))/$MAX_RETRIES..."
      
      if az functionapp deployment source config-zip \
        --name $FUNCTION_APP \
        --resource-group $RESOURCE_GROUP \
        --src function-app.zip; then
        DEPLOY_SUCCESS=true
        break
      fi
      
      if [ $RETRY_COUNT -lt $((MAX_RETRIES-1)) ]; then
        echo "⏳ Another deployment in progress, waiting 60s before retry..."
        sleep 60
      fi
      
      RETRY_COUNT=$((RETRY_COUNT+1))
    done

    if [ "$DEPLOY_SUCCESS" = false ]; then
      # 最終確認: Function Appが正常に起動しているか
      echo "⚠️ Deployment uncertain after $MAX_RETRIES attempts, checking function health..."
      
      # health check logic here
      STATUS=$(az functionapp show --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --query state -o tsv)
      if [ "$STATUS" = "Running" ]; then
        echo "✅ Function App is Running, deployment may have succeeded"
      else
        echo "❌ Function App deployment failed"
        exit 1
      fi
    fi
```

### 該当ファイル

- `.github/workflows/deploy-azure.yml` (lines 268-295)

### 関連する設定変更の待機

設定変更後は短い待機を入れる：

```yaml
# 設定変更
az functionapp config appsettings set ...

# Kudu再起動の待機
sleep 10

# デプロイ実行
az functionapp deployment source config-zip ...
```

### 参考

- Kudu (App Service のデプロイメントエンジン) の再起動には5-15秒かかる
- 待機時間は環境により調整（staging: 短め、production: 長め）

---

## モノレポ構造でのGitパス問題

### 症状

```
fatal: pathspec 'multicloud-auto-deploy/services/api/app/main.py' did not match any files
```

または：

```
fatal: '../.github/workflows/deploy-aws.yml' is outside repository
```

Gitコマンドでファイルパスを指定すると「見つからない」または「リポジトリ外」エラー。

### 原因

**作業ディレクトリとGitリポジトリのルートが異なる**状態でGitコマンドを実行。

**例:**

- Gitリポジトリルート: `/workspaces/ashnova`
- 作業ディレクトリ: `/workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/azure`

この状態で `git add multicloud-auto-deploy/...` を実行すると、
`/workspaces/ashnova/multicloud-auto-deploy/multicloud-auto-deploy/...` を探してしまう。

### 調査方法

```bash
# 現在のディレクトリ
pwd

# Gitリポジトリのルート
git rev-parse --show-toplevel

# 相対パスの確認
git status --short
```

### 解決策

#### 方法1: リポジトリルートに移動してからコミット

```bash
cd $(git rev-parse --show-toplevel)
git add .github/workflows/deploy-aws.yml
git commit -m "message"
git push origin develop
```

#### 方法2: 相対パスを使う

```bash
# 現在地: /workspaces/ashnova/multicloud-auto-deploy
git add ../.github/workflows/deploy-aws.yml
git commit -m "message"

# リモート名を確認
git remote -v
# ashnova https://github.com/PLAYER1-r7/multicloud-auto-deploy.git

git push ashnova develop
```

#### 方法3: git -Cオプションを使う

```bash
# どこからでもリポジトリルートを基準に実行
git -C /workspaces/ashnova add .github/workflows/deploy-aws.yml
git -C /workspaces/ashnova commit -m "message"
git -C /workspaces/ashnova push origin develop
```

### 該当する状況

- モノレポ構造（複数のPulumiプロジェクト、複数のサービス）
- ワークフロー実行中に `cd` でディレクトリ移動
- 相対パスと絶対パスの混在

### ベストプラクティス

- Gitコマンドは**常にリポジトリルートから実行**
- 相対パスを使う場合は `git status` で確認
- スクリプト内では `cd $(git rev-parse --show-toplevel)` で統一

---

## Pulumi スタックとディレクトリの混同

### 症状

```
error: no stack named 'staging' found
```

または：

```
error: could not read current project: no Pulumi.yaml project file found
```

Pulumiコマンドを実行すると、スタックが見つからない、またはプロジェクトファイルがないエラー。

### 原因

**間違ったディレクトリでPulumiコマンドを実行**している。

モノレポでは複数のPulumiプロジェクトが存在：

- `infrastructure/pulumi/aws/`
- `infrastructure/pulumi/azure/`
- `infrastructure/pulumi/gcp/`

各ディレクトリには独立した `Pulumi.yaml` とスタックがある。

### 調査方法

```bash
# 現在のディレクトリ
pwd

# Pulumi.yamlの場所を確認
find . -name "Pulumi.yaml" -type f

# 現在のプロジェクト情報
pulumi about

# 利用可能なスタック
pulumi stack ls
```

### 解決策

**正しいディレクトリに移動してから実行**：

```bash
# AWS
cd infrastructure/pulumi/aws
pulumi stack select staging
pulumi up

# Azure
cd infrastructure/pulumi/azure
pulumi stack select staging
pulumi up

# GCP
cd infrastructure/pulumi/gcp
pulumi stack select staging
pulumi up
```

### GitHub Actionsでの対応

```yaml
- name: Deploy Infrastructure
  run: |
    # クラウドごとに正しいディレクトリに移動
    cd infrastructure/pulumi/aws  # or azure, gcp

    # スタック選択
    pulumi stack select staging --non-interactive

    # デプロイ
    pulumi up --yes
```

### エラー回避のチェックリスト

1. ✅ `Pulumi.yaml` が存在するディレクトリにいるか
2. ✅ `pulumi stack ls` でスタックが表示されるか
3. ✅ `pulumi config get <key>` で設定が取得できるか

### 該当ファイル

- `.github/workflows/deploy-aws.yml` (line 80)
- `.github/workflows/deploy-azure.yml` (line 81)
- `.github/workflows/deploy-gcp.yml` (line 168)

### ベストプラクティス

- スクリプトの冒頭で `cd` を明示的に実行
- エラーメッセージで「プロジェクトが見つからない」と出たらディレクトリを確認
- `pulumi about` で現在の状態を確認する習慣

---

## 環境変数の引用符とエスケープ

### 症状

```bash
# JSON構文エラー
Error: invalid character 'h' after object key:value pair

# または環境変数が正しく展開されない
CORS_ORIGINS=""
```

bashスクリプトやJSONファイル生成時に、環境変数が正しく展開されない、またはJSON構文エラー。

### 原因

**引用符のエスケープ不足**、または**変数展開のタイミング**の問題。

#### よくあるパターン:

1. **JSON内の引用符エスケープ漏れ**

```bash
# ❌ 間違い: 変数内のURLにコロンがあるとJSON構文エラー
echo '{"url": "$MY_URL"}' > config.json
# 結果: {"url": "$MY_URL"}  ← 変数が展開されない

# ❌ 間違い: ダブルクォートの衝突
echo "{"url": "$MY_URL"}" > config.json
# 構文エラー
```

2. **カンマ区切りリストの扱い**

```bash
# ❌ 間違い: 最後のカンマ
echo "  \"key1\": \"value1\"," >> config.json
echo "  \"key2\": \"value2\"," >> config.json  # 最後にカンマ不要
echo "}" >> config.json
# Invalid JSON: trailing comma
```

### 解決策

#### 方法1: echoで段階的に構築（推奨）

```bash
# 変数の準備
CORS_ORIGINS="https://example.com,http://localhost:5173"
DB_ENDPOINT="https://db.example.com:5432"

# JSONファイル作成（エスケープに注意）
echo '{' > /tmp/config.json
echo '  "Variables": {' >> /tmp/config.json
echo '    "CLOUD_PROVIDER": "aws",' >> /tmp/config.json
echo "    \"CORS_ORIGINS\": \"$CORS_ORIGINS\"," >> /tmp/config.json
echo "    \"DB_ENDPOINT\": \"$DB_ENDPOINT\"" >> /tmp/config.json  # 最後はカンマなし
echo '  }' >> /tmp/config.json
echo '}' >> /tmp/config.json

# 検証
cat /tmp/config.json | jq .  # jqで構文チェック
```

#### 方法2: jqを使う（最も安全）

```bash
jq -n \
  --arg cors "$CORS_ORIGINS" \
  --arg db "$DB_ENDPOINT" \
  '{
    Variables: {
      CLOUD_PROVIDER: "aws",
      CORS_ORIGINS: $cors,
      DB_ENDPOINT: $db
    }
  }' > /tmp/config.json
```

#### 方法3: Heredocument（シングルクォートで囲む）

```bash
cat > /tmp/config.json << 'EOF'
{
  "Variables": {
    "CLOUD_PROVIDER": "aws",
    "CORS_ORIGINS": "${CORS_ORIGINS}",
    "DB_ENDPOINT": "${DB_ENDPOINT}"
  }
}
EOF

# envsubstで変数展開
envsubst < /tmp/config.json > /tmp/config-final.json
```

### bash変数の引用符ルール

```bash
# ✅ 推奨: 常にダブルクォートで囲む
MY_VAR="value with spaces"
echo "Value: $MY_VAR"

# ❌ 避ける: クォートなし（スペースで分割される）
MY_VAR=value with spaces  # エラー
echo Value: $MY_VAR       # 意図しない分割

# ✅ 配列の場合
MY_ARRAY=("item1" "item2" "item3")
echo "${MY_ARRAY[@]}"

# ✅ コマンド置換もクォート
RESULT="$(aws lambda get-function --function-name xyz --query 'Configuration.State' --output text)"
```

### GitHub Actionsでの注意点

```yaml
# ✅ 正しい: ${{ }} 構文は自動エスケープ
- name: Set variable
  run: |
    CORS_ORIGINS="${{ steps.pulumi_outputs.outputs.cloudfront_domain }}"
    echo "CORS_ORIGINS=$CORS_ORIGINS" >> $GITHUB_OUTPUT

# ❌ 間違い: シングルクォート内では展開されない
- name: Wrong
  run: |
    echo 'CORS_ORIGINS=${{ steps.output.value }}'  # 文字列として出力される
```

### デバッグ方法

```bash
# 変数の内容を確認
echo "CORS_ORIGINS: [$CORS_ORIGINS]"
echo "Length: ${#CORS_ORIGINS}"

# JSONの構文チェック
cat config.json | jq . || echo "Invalid JSON"

# 特殊文字の確認
echo "$MY_VAR" | od -c  # 制御文字を表示
```

### 該当ファイル

- `.github/workflows/deploy-aws.yml` (lines 247-258)
- `.github/workflows/deploy-gcp.yml` (lines 172-179)

---

## CloudフロントIDの取得とキャッシュ無効化

### 症状

```
An error occurred (InvalidArgument) when calling the CreateInvalidation operation:
Your request contains one or more invalid CloudFront distribution ids.
```

CloudFrontのキャッシュ無効化コマンドでDistribution IDが見つからないエラー。

### 原因

1. **Distribution IDのハードコード**（実際のIDと異なる）
2. **Pulumi outputsからの取得方法が間違っている**
3. **Distribution IDとDomain Nameの混同**

CloudFrontでは：

- **Distribution ID**: `E1234ABCD5678` （アルファベット+数字、ランダム生成）
- **Domain Name**: `d1tf3uumcm4bo1.cloudfront.net` （実際のURL）

### 調査方法

```bash
# 1. Pulumi outputsを確認
cd infrastructure/pulumi/aws
pulumi stack output --json | jq .

# 2. AWS CLIで確認
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].[Id,DomainName,Comment]' \
  --output table

# 3. 特定のドメインのIDを取得
aws cloudfront list-distributions \
  --query "DistributionList.Items[?DomainName=='d1tf3uumcm4bo1.cloudfront.net'].Id" \
  --output text
```

### 解決策

#### Pulumi outputsから取得

```python
# infrastructure/pulumi/aws/__main__.py
import pulumi
import pulumi_aws as aws

distribution = aws.cloudfront.Distribution("cdn", ...)

# Distribution IDとDomain Nameの両方をexport
pulumi.export("cloudfront_id", distribution.id)
pulumi.export("cloudfront_domain", distribution.domain_name)
```

#### ワークフローで使用

```yaml
- name: Get Pulumi Outputs
  id: pulumi_outputs
  run: |
    cd infrastructure/pulumi/aws

    CLOUDFRONT_ID=$(pulumi stack output cloudfront_id)
    CLOUDFRONT_DOMAIN=$(pulumi stack output cloudfront_domain)

    echo "cloudfront_id=$CLOUDFRONT_ID" >> $GITHUB_OUTPUT
    echo "cloudfront_domain=$CLOUDFRONT_DOMAIN" >> $GITHUB_OUTPUT

- name: Invalidate CloudFront Cache
  run: |
    # キャッシュ無効化（全ファイル）
    aws cloudfront create-invalidation \
      --distribution-id ${{ steps.pulumi_outputs.outputs.cloudfront_id }} \
      --paths "/*"

    echo "✅ CloudFront cache invalidation initiated"
```

#### 無効化の確認

```bash
# 無効化ステータスの確認
aws cloudfront list-invalidations \
  --distribution-id E1234ABCD5678 \
  --query 'InvalidationList.Items[0].{Id:Id,Status:Status,CreateTime:CreateTime}'

# 特定の無効化の詳細
aws cloudfront get-invalidation \
  --distribution-id E1234ABCD5678 \
  --id I2ABCDEFGH1234
```

### 無効化のベストプラクティス

#### パスの指定

```bash
# ✅ 全ファイル（最も確実）
--paths "/*"

# ✅ 特定ディレクトリ
--paths "/images/*" "/css/*"

# ✅ 特定ファイル
--paths "/index.html" "/app.js"

# ❌ 避ける: ワイルドカードなし（単一ファイルのみ）
--paths "/"  # ルートのみ、配下は無効化されない
```

#### コスト最適化

- 月1,000回まで無料
- 1,001回目以降は$0.005/パス
- `/*` は1パスとしてカウント（推奨）
- 個別ファイル指定は各ファイルが1パスとしてカウント

#### 待機時間

```bash
# 無効化は数秒〜数分かかる
aws cloudfront create-invalidation --distribution-id $ID --paths "/*"

# 完了を待つ場合（オプション）
aws cloudfront wait invalidation-completed \
  --distribution-id $ID \
  --id <invalidation-id>
```

### 該当ファイル

- `.github/workflows/deploy-aws.yml` (lines 279-284)
- `infrastructure/pulumi/aws/__main__.py`

### 参考

- [CloudFront Cache Invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
- 無効化は即座に反映されない（通常1-3分）
- 頻繁な無効化よりバージョニング戦略（`app.v123.js`）を推奨

---

## Lambda Layer ビルド時の依存関係エラー

### 症状

```
ERROR: Could not find a version that satisfies the requirement fastapi==0.109.0
```

または：

```
ERROR: No matching distribution found for cryptography>=41.0.0
```

Lambda Layerのビルド時に、Python依存関係のインストールが失敗する。

### 原因

1. **プラットフォームの不一致**: ローカル環境（macOS/Windows）とLambda環境（Linux x86_64）のバイナリ互換性
2. **Pythonバージョンの不一致**: ビルド環境とLambdaランタイムのバージョンが異なる
3. **ネイティブ拡張**: C拡張を含むパッケージ（cryptography, psycopg2など）のビルド失敗

### 解決策

#### Lambda互換のビルド（推奨）

```bash
# Docker使用してLambda環境でビルド
docker run --rm \
  -v "$PWD":/var/task \
  public.ecr.aws/lambda/python:3.12 \
  /bin/bash -c "
    pip install -r requirements.txt -t /var/task/python/ --no-cache-dir
  "

# Layerのディレクトリ構造
# lambda-layer/
#   python/
#     fastapi/
#     pydantic/
#     ...
```

#### GitHub Actionsでのビルド

```yaml
- name: Build Lambda Layer
  run: |
    cd services/api

    # Lambda互換の依存関係をインストール
    docker run --rm \
      -v "$PWD":/var/task \
      -w /var/task \
      public.ecr.aws/lambda/python:3.12 \
      pip install -r requirements.txt -t python/ --platform manylinux2014_x86_64 --only-binary=:all:

    # Layer zipを作成
    zip -r lambda-layer.zip python/

    # サイズ確認
    ls -lh lambda-layer.zip
```

#### プラットフォーム指定（pip 20.3+）

```bash
# Linux x86_64向けにビルド
pip install -r requirements.txt \
  -t python/ \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --only-binary=:all: \
  --no-deps

# その後、依存関係を解決
pip install -r requirements.txt -t python/ --upgrade
```

### requirements.txtのベストプラクティス

```txt
# ✅ バージョン固定（再現性）
fastapi==0.115.0
pydantic==2.9.0
mangum==0.17.0

# ❌ 避ける: バージョン固定なし（予期しない破壊的変更）
fastapi
pydantic

# ✅ 範囲指定（セキュリティパッチ適用）
requests>=2.31.0,<3.0.0

# ❌ boto3/botocore を含めない（Lambdaランタイムに含まれる）
# boto3==1.35.0  # 除外してサイズ削減

# ネイティブ拡張の代替
# ❌ psycopg2（ビルドが複雑）
# ✅ psycopg2-binary（バイナリ版、Lambdaで動作）
psycopg2-binary==2.9.9
```

### Layer サイズの最適化

```bash
# 不要なファイルを削除
cd python/
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name "*.dist-info" -exec rm -rf {} +
find . -type d -name "tests" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.so" -exec strip {} \;

# 再圧縮
cd ..
zip -r lambda-layer-optimized.zip python/
```

### Lambda Layerのサイズ制限

- **展開後の最大サイズ**: 250 MB
- **zip圧縮時の最大サイズ**: 50 MB（直接アップロード）、無制限（S3経由）

サイズ超過の場合：

1. 不要な依存関係を削除
2. ネイティブ拡張を避ける（pure Pythonの代替を探す）
3. 複数のLayerに分割

### 該当ファイル

- `scripts/build-lambda-layer.sh`
- `.github/workflows/deploy-aws.yml` (lines 98-112)

### トラブルシューティング

```bash
# Layer内のパッケージを確認
unzip -l lambda-layer.zip | head -20

# 展開後のサイズ確認
unzip lambda-layer.zip -d /tmp/layer-test
du -sh /tmp/layer-test

# Lambdaでインポート可能か確認
python3 -c "import sys; sys.path.insert(0, '/tmp/layer-test/python'); import fastapi; print(fastapi.__version__)"
```

---

## GitHub Actions シークレットの参照エラー

### 症状

```yaml
The workflow is not valid. ... unrecognized named-value: "secrets"
```

または、ワークフロー実行時に：

```
Error: Process completed with exit code 1.
AWS_ACCESS_KEY_ID: command not found
```

### 原因

1. **シークレットが設定されていない**: リポジトリにシークレットが登録されていない
2. **スコープの問題**: Organization/Repository/Environmentのスコープが異なる
3. **参照方法の間違い**: `${{ secrets.NAME }}` の構文ミス
4. **環境変数での参照**: `env:` セクション外で `$AWS_ACCESS_KEY_ID` を使おうとした

### 確認方法

#### GitHubリポジトリでシークレットを確認

```
Settings → Secrets and variables → Actions → Repository secrets
```

必要なシークレット:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AZURE_CREDENTIALS` (JSON形式)
- `GCP_SERVICE_ACCOUNT_KEY` (JSON形式)
- `PULUMI_ACCESS_TOKEN`

#### GitHub CLIで確認

```bash
gh secret list --repo OWNER/REPO

# 特定のシークレットの存在確認（値は見えない）
gh secret list --repo OWNER/REPO | grep AWS_ACCESS_KEY_ID
```

### 解決策

#### 正しい参照方法

```yaml
# ✅ secrets context（GitHub Actions内）
- name: Configure AWS Credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ap-northeast-1

# ✅ 環境変数として設定
- name: Deploy
  run: |
    aws s3 cp file.txt s3://bucket/
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

# ❌ 間違い: run内で直接参照（展開されない）
- name: Wrong
  run: |
    export AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}  # 危険: ログに出力される
```

#### シークレットの設定

```bash
# GitHub CLIでシークレットを設定
gh secret set AWS_ACCESS_KEY_ID --body "AKIAIOSFODNN7EXAMPLE" --repo OWNER/REPO

# ファイルから読み込み
gh secret set GCP_SERVICE_ACCOUNT_KEY < gcp-key.json --repo OWNER/REPO

# 対話式
gh secret set PULUMI_ACCESS_TOKEN --repo OWNER/REPO
# > Paste your secret: ***
```

#### JSON形式のシークレット（Azure/GCP）

```bash
# Azure Credentials (Service Principal)
az ad sp create-for-rbac \
  --name "github-actions" \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID \
  --sdk-auth

# 出力されたJSONをそのまま AZURE_CREDENTIALS に設定
# {
#   "clientId": "xxx",
#   "clientSecret": "xxx",
#   "subscriptionId": "xxx",
#   "tenantId": "xxx",
#   ...
# }

# GCP Service Account Key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@PROJECT_ID.iam.gserviceaccount.com

# key.json の内容を GCP_SERVICE_ACCOUNT_KEY に設定
```

### 環境別シークレット（Environment Secrets）

```yaml
# ワークフロー内で環境を指定
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production # または staging
    steps:
      - name: Deploy
        run: |
          echo "Deploying to ${{ vars.ENVIRONMENT_NAME }}"
        env:
          API_KEY: ${{ secrets.PROD_API_KEY }} # production環境のシークレット
```

環境の設定:

```
Settings → Environments → New environment
→ Add secret
```

### デバッグのヒント

```yaml
# ✅ シークレットの存在確認（値は表示されない）
- name: Check secrets
  run: |
    if [ -z "${{ secrets.AWS_ACCESS_KEY_ID }}" ]; then
      echo "❌ AWS_ACCESS_KEY_ID is not set"
      exit 1
    fi
    echo "✅ AWS_ACCESS_KEY_ID is set"

# ✅ 環境変数の確認（値はマスクされる）
- name: Debug
  run: |
    echo "AWS_REGION: $AWS_REGION"
    echo "Keys configured: $(aws configure list)"
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_REGION: ap-northeast-1

# ❌ 絶対にやってはいけない: シークレットの出力（マスクされないパターン）
- name: NEVER DO THIS
  run: |
    SECRET="${{ secrets.MY_SECRET }}"
    echo "Secret is: $SECRET"  # ログに平文で出力される危険性
```

### 該当ファイル

- `.github/workflows/deploy-aws.yml` (lines 31-35)
- `.github/workflows/deploy-azure.yml` (lines 32-38)
- `.github/workflows/deploy-gcp.yml` (lines 145-149)

### セキュリティのベストプラクティス

1. **最小権限の原則**: 必要最小限の権限を持つIAMユーザー/Service Principalを使用
2. **ローテーション**: 定期的にシークレットを更新
3. **環境分離**: staging/productionで異なるシークレットを使用
4. **監査ログ**: AWS CloudTrail、Azure Activity Log等で使用状況を監視
5. **シークレットをログに出さない**: `echo` やエラーメッセージに注意

---

## 一般的なトラブルシューティングのヒント

### 1. Azure CLIのデバッグ

```bash
# デバッグログを有効化
export AZURE_CLI_DEBUG=1

# またはコマンドに --debug を追加
az <command> --debug
```

### 2. AWS CLIのデバッグ

```bash
# デバッグログを有効化
aws <command> --debug

# CloudWatch Logsで確認
aws logs tail /aws/lambda/<function-name> --follow
```

### 3. GitHub Actionsのデバッグ

```yaml
# ステップのデバッグ情報を有効化
- name: Debug
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Inputs: ${{ toJSON(github.event.inputs) }}"
    env | sort
```

リポジトリシークレット `ACTIONS_STEP_DEBUG=true` を設定すると全ステップで詳細ログが出力される。

### 4. 設定値の検証

```bash
# Azure
az functionapp config appsettings list --name <name> --resource-group <rg> --output table

# AWS
aws lambda get-function-configuration --function-name <name>

# GCP
gcloud functions describe <name> --region <region> --format json
```

### 5. デプロイメントの段階的検証

1. インフラが正しくプロビジョニングされているか（Pulumi outputsで確認）
2. アプリケーションコードがデプロイされているか
3. 環境変数が正しく設定されているか
4. CORS設定が反映されているか
5. 認証が機能しているか

各段階で失敗した場合は、**その段階だけを切り分けて**トラブルシュート。

---

## 参考リンク

- [GitHub Actions YAML Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Azure CLI Reference](https://docs.microsoft.com/en-us/cli/azure/)
- [AWS Lambda States](https://docs.aws.amazon.com/lambda/latest/dg/API_FunctionConfiguration.html)
- [Pulumi Outputs](https://www.pulumi.com/docs/concepts/inputs-outputs/)

---

## 更新履歴

| 日付       | 内容                                                                                                                                                                                                                                                                                                                                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-02-17 | 🎯 **大幅改善**: クイック診断フローチャート、エラーメッセージ別インデックス、よくある問題トップ5を追加。全セクションに解決時間を表示。Azure Flex Consumption特有の問題（Partially Successful、defaultHostName null、Kudu再起動）を詳細ドキュメント化。AWS Lambda Runtime Errors、GCP Cloud Run 500 Errors、GitHub Actionsシークレット参照エラーを追加。 |
| 2026-02-17 | 追加: リソース名ハードコード、デプロイメント競合、Gitパス、Pulumiディレクトリ、環境変数エスケープ、CloudFront、Lambda Layer、GitHub Secretsの全11トピック                                                                                                                                                                                               |
| 2026-02-17 | 初版作成（CORS hardening デプロイの知見）                                                                                                                                                                                                                                                                                                               |

---

## 📚 関連ドキュメント

- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - 本番デプロイ前のチェックリスト
- [MONITORING.md](MONITORING.md) - 監視とアラート設定
- [docs/ENDPOINTS.md](docs/ENDPOINTS.md) - 各環境のエンドポイント一覧
- [docs/CICD_SETUP.md](docs/CICD_SETUP.md) - CI/CDパイプラインセットアップ
- [CHANGELOG.md](CHANGELOG.md) - 詳細な変更履歴

---

## 🆘 サポート

問題が解決しない場合は：

1. **GitHub Issues**: [新しいIssueを作成](https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues/new)
2. **ログの確認**:
   - GitHub Actions: ワークフロー実行ログの全文をコピー
   - CloudWatch/Azure Monitor/GCP Logging: 直近5分のエラーログ
3. **再現手順**: 問題を再現できる最小限の手順を記載
4. **環境情報**: OS、クラウドプロバイダー、使用しているツールのバージョン

**報告時のテンプレート**:

```markdown
### 問題の概要

[簡潔な説明]

### エラーメッセージ
```

[エラーの全文]

```

### 再現手順
1. [手順1]
2. [手順2]
3. [エラー発生]

### 環境
- クラウド: AWS / Azure / GCP
- 環境: staging / production
- ワークフロー: [ワークフロー名]
- コミットハッシュ: [hash]

### 試したこと
- [試した解決策1]
- [試した解決策2]
```
