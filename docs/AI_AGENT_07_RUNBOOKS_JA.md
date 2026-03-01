# 07 — ランブック

> Part III — 運用 | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> よくある作業とインシデント対応の手順書

---

## [RB-01] Lambda 関数を手動更新する

```bash
# 1. アプリコードのみをパッケージング (ZIP)
cd /workspaces/multicloud-auto-deploy/services/api
rm -rf .build && mkdir -p .build/package
cp -r app .build/package/
cp index.py .build/package/
cd .build/package && zip -r ../../lambda.zip . && cd ../..

# 2. Lambda を更新
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip \
  --region ap-northeast-1

# 3. 更新を確認
aws lambda invoke \
  --function-name multicloud-auto-deploy-staging-api \
  --payload '{"version":"2.0","routeKey":"$default","rawPath":"/health","requestContext":{"http":{"method":"GET","path":"/health"}}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json | python3 -m json.tool
```

---

## [RB-02] Lambda ログを確認する

```bash
# リアルタイム追従
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api --follow --region ap-northeast-1

# 直近10分のエラーのみ
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
  --since 10m --filter-pattern "ERROR" --region ap-northeast-1
```

---

## [RB-03] React フロントエンドを手動デプロイする（AWS）

```bash
cd /workspaces/multicloud-auto-deploy/services/frontend_react
npm ci

# API URL を指定してビルド; base="/sns/" は vite.config.ts で設定済み
VITE_API_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com npm run build

# S3 にアップロード — sns/ プレフィックスは必須
aws s3 sync dist/ s3://multicloud-auto-deploy-staging-frontend/sns/ \
  --delete --region ap-northeast-1

# CloudFront キャッシュを無効化
aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"
```

---

## [RB-04] ランディングページを手動デプロイする（AWS）

```bash
# static-site/ をバケットルートへアップロード
aws s3 sync /workspaces/multicloud-auto-deploy/static-site/ \
  s3://multicloud-auto-deploy-staging-frontend/ \
  --delete --region ap-northeast-1

aws cloudfront create-invalidation \
  --distribution-id E1TBH4R432SZBZ \
  --paths "/*"
```

---

## [RB-05] Azure Functions を手動デプロイする

```bash
cd /workspaces/multicloud-auto-deploy/services/api

# デプロイパッケージを作成
pip install -r requirements-azure.txt -t .deploy-azure/
cp -r app .deploy-azure/
cp function_app.py host.json local.settings.json .deploy-azure/

# Zip 化
cd .deploy-azure && zip -r ../function-app.zip . && cd ..

# Azure CLI でデプロイ
az functionapp deployment source config-zip \
  --resource-group multicloud-auto-deploy-staging-rg \
  --name multicloud-auto-deploy-staging-func \
  --src function-app.zip
```

---

## [RB-06] GCP Cloud Run を手動デプロイする

```bash
cd /workspaces/multicloud-auto-deploy/services/api

# Cloud Run ビルド用にソースを Zip 化
zip -r gcp-cloudrun-source.zip app/ function.py requirements.txt requirements-gcp.txt Dockerfile

# gcloud でソースからデプロイ
gcloud run deploy multicloud-auto-deploy-staging-api \
  --source . \
  --region asia-northeast1 \
  --project ashnova \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "CLOUD_PROVIDER=gcp,AUTH_DISABLED=false,GCP_POSTS_COLLECTION=posts"
```

---

## [RB-07] Pulumi スタックを再デプロイする

```bash
# AWS
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/aws
pulumi login
pulumi stack select staging
pulumi up --yes

# Azure
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/azure
pulumi stack select staging
pulumi up --yes

# GCP
cd /workspaces/multicloud-auto-deploy/infrastructure/pulumi/gcp
pulumi stack select staging
pulumi up --yes
```

---

## [RB-08] API エンドポイントテストを実行する

```bash
# 全クラウド E2E（curl ベース）
./scripts/test-e2e.sh

# 単一クラウド
./scripts/test-api.sh -e https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com

# pytest（モックテスト）
cd services/api
source .venv/bin/activate
pytest tests/test_backends_integration.py -v

# pytest（ライブ API）
API_BASE_URL=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com \
  pytest tests/test_api_endpoints.py -v
```

---

## [RB-09] DynamoDB PostIdIndex GSI を確認 / 作成する

```bash
# GSI が存在するか確認
aws dynamodb describe-table \
  --table-name multicloud-auto-deploy-staging-posts \
  --region ap-northeast-1 \
  --query 'Table.GlobalSecondaryIndexes[*].IndexName'

# GSI がなければ作成
aws dynamodb update-table \
  --table-name multicloud-auto-deploy-staging-posts \
  --region ap-northeast-1 \
  --attribute-definitions AttributeName=postId,AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"PostIdIndex","KeySchema":[{"AttributeName":"postId","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}}]'
```

---

## [RB-11] API Lambda を再ビルドしてホットフィックスデプロイする（CI なし）

CI を待たずに API Lambda へ緊急修正をデプロイしたい場合に使用します。

```bash
cd /workspaces/multicloud-auto-deploy/services/api

# 1. 最新ソースで .build/package を更新
cp -r app index.py .build/package/

# 2. lambda.zip を再作成
cd .build/package
zip -r ../../lambda.zip . -x "*.pyc" -x "__pycache__/*" > /dev/null
cd ../..

# 3. ガード: 進行中の更新完了を先に待機
aws lambda wait function-updated \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1

# 4. デプロイ
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --zip-file fileb://lambda.zip \
  --output text --query 'LastUpdateStatus'

# 5. デプロイ完了待機
aws lambda wait function-updated \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 && echo "Ready"
```

---

## [RB-12] AWS simple-sns E2E テストを実行する

```bash
# 公開エンドポイントのみ（認証不要）
./scripts/test-sns-aws.sh

# 完全な認証付きテスト — 先にトークンを取得
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 1k41lqkds4oah55ns8iod30dv2 \
  --auth-parameters USERNAME=<your-email>,PASSWORD=<your-password> \
  --region ap-northeast-1 \
  --query 'AuthenticationResult.AccessToken' --output text)

./scripts/test-sns-aws.sh --token "$TOKEN" --verbose
```

**参照**: [docs/AWS_SNS_FIX_REPORT.md](AWS_SNS_FIX_REPORT.md)

---

## [RB-10] ローカル開発環境を起動する

> **ホストマシン**: ARM（Apple Silicon M シリーズ Mac）
> Dev Container 内から実行してください。

```bash
cd /workspaces/multicloud-auto-deploy

# インフラ起動
docker compose up -d

# 起動確認
docker compose ps
curl http://localhost:8000/health

# ログ確認
docker compose logs -f api
```

### 環境変数の上書き（デバッグ用）

特定バックエンドを向ける場合は `.env` を作成します。

```bash
# services/api/.env または docker-compose の env_file で指定
CLOUD_PROVIDER=local
AUTH_DISABLED=true
API_BASE_URL=http://localhost:8000
```

### ARM に関する注意

- ローカルの docker compose は **ARM** でネイティブ動作（問題なし）
- Lambda 向けパッケージのビルドには `--platform linux/amd64` が必要
  → 通常は GitHub Actions（ubuntu-latest = x86_64）が処理
- GCP Cloud Function の ZIP ビルドも同様（CI で自動処理）

---

## [RB-13] GCP Cloud Function を再ビルドしてホットフィックスデプロイする（linux/amd64）

dev container は `aarch64`、Cloud Functions は `linux/amd64` で動作します。必ず Docker を使用してください。

```bash
# 1. linux/amd64 パッケージをビルド
mkdir -p /tmp/deploy_gcp/.deployment
docker run --rm --platform linux/amd64 \
  -v /tmp/deploy_gcp:/out \
  python:3.13-slim \
  bash -c "pip install --no-cache-dir --target /out/.deployment \
           -r /workspaces/multicloud-auto-deploy/services/api/requirements-gcp.txt -q"

# 2. アプリコードをコピー
cp -r /workspaces/multicloud-auto-deploy/services/api/app /tmp/deploy_gcp/.deployment/
# Cloud Build は --entry-point 指定時でも main.py を要求
cp /workspaces/multicloud-auto-deploy/services/api/function.py /tmp/deploy_gcp/.deployment/main.py
cp /workspaces/multicloud-auto-deploy/services/api/function.py /tmp/deploy_gcp/.deployment/function.py

# 3. ZIP を作成（__pycache__ を除外）
cd /tmp/deploy_gcp/.deployment
find . -name "__pycache__" -path "*/app/*" -exec rm -rf {} + 2>/dev/null || true
zip -r9q /tmp/deploy_gcp/function-source.zip .
cd /workspaces/multicloud-auto-deploy

# 4. GCS へアップロード（再開時は古い tracker files を先に削除）
rm -f ~/.config/gcloud/surface_data/storage/tracker_files/*
gcloud storage cp /tmp/deploy_gcp/function-source.zip \
  gs://ashnova-multicloud-auto-deploy-staging-function-source/function-source.zip

# 5. デプロイ
gcloud functions deploy multicloud-auto-deploy-staging-api \
  --gen2 --region=asia-northeast1 --runtime=python312 \
  --source=gs://ashnova-multicloud-auto-deploy-staging-function-source/function-source.zip \
  --entry-point=handler --project=ashnova --quiet
```

**重要ルール**:

- ZIP 内に `main.py` が**必須**。`--entry-point` が別関数でも、Cloud Build はこれが無いソースを拒否します。
- パッケージ前に必ず構文確認: `python3 -m py_compile services/api/app/backends/local_backend.py && echo OK`
- `gcloud run services update --update-env-vars` は URL 値に使えません（`:` でパースエラー）。`--env-vars-file` を使ってください。

---

## [RB-14] Azure Front Door 502 を修正する（Dynamic Consumption → FC1 FlexConsumption）

Dynamic Consumption（Y1）の Function App は定期的に再起動されます。AFD Standard は TCP 切断を検知できず、接続プールに古い接続が残って 502 を即時返すことがあります。
対策は、固定1インスタンスの **FC1 FlexConsumption** へ移行することです。

```bash
RG="multicloud-auto-deploy-production-rg"
FD="multicloud-auto-deploy-production-fd"
EP="mcad-production-diev0w"
OG="multicloud-auto-deploy-production-frontend-web-origin-group"
ORIGIN="multicloud-auto-deploy-production-frontend-web-origin"

# 1. FC1 FlexConsumption Function App を作成
az functionapp create \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --flexconsumption-location japaneast \
  --runtime python --runtime-version 3.13 \
  --storage-account mcadfuncdiev0w

# 2. インスタンス数を1に固定（再起動回避）
az functionapp scale config set \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --maximum-instance-count 1
az functionapp scale config always-ready set \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --settings "http=1"

# 3. x86_64 ZIP をデプロイ（事前に Docker --platform linux/amd64 でビルド）
az functionapp deployment source config-zip \
  --name multicloud-auto-deploy-production-frontend-web-v2 \
  --resource-group "$RG" \
  --src services/frontend_web/frontend-web-prod.zip

# 4. AFD origin を新しい Function App へ切り替え
az afd origin update \
  --resource-group "$RG" \
  --profile-name "$FD" \
  --origin-group-name "$OG" \
  --origin-name "$ORIGIN" \
  --host-name multicloud-auto-deploy-production-frontend-web-v2.azurewebsites.net \
  --origin-host-header multicloud-auto-deploy-production-frontend-web-v2.azurewebsites.net

# 5. 古い Y1 アプリを停止（AFD エッジ反映に約5分）
az functionapp stop \
  --name multicloud-auto-deploy-production-frontend-web \
  --resource-group "$RG"
```

**重要メモ**:

- `--consumption-plan-location` は Y1 Dynamic を作成するため誤り。FC1 には必ず `--flexconsumption-location` を使います。
- `az functionapp update --plan` は Linux→Linux のプラン移行をサポートしません。新規アプリ作成が必要です。
- AFD origin 更新は全エッジ反映まで最大5分程度かかります。
- `SCM_DO_BUILD_DURING_DEPLOYMENT` は Flex Consumption で `InvalidAppSettingsException` を起こすため設定しないでください。

---

## [RB-15] AWS CloudFront HTTPS 証明書エラーを修正する（ERR_CERT_COMMON_NAME_INVALID）

`customDomain` / `acmCertificateArn` を設定せずに `pulumi up --stack production` を実行すると、
CloudFront が `CloudFrontDefaultCertificate: true` に戻り、カスタムドメインの HTTPS が壊れます。

```bash
# 1. 現在の distribution 設定と ETag を取得
aws cloudfront get-distribution-config --id E214XONKTXJEJD > /tmp/cf-config.json
# 応答内 ETag を控える（例: E13V1IB3VIYZZH）

# 2. JSON を修正（Python ワンライナー）
python3 - <<'EOF'
import json
with open('/tmp/cf-config.json') as f:
    data = json.load(f)
cfg = data['DistributionConfig']
cfg['Aliases'] = {'Quantity': 1, 'Items': ['www.aws.ashnova.jp']}
cfg['ViewerCertificate'] = {
    'ACMCertificateArn': 'arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5',
    'SSLSupportMethod': 'sni-only',
    'MinimumProtocolVersion': 'TLSv1.2_2021',
    'CertificateSource': 'acm'
}
with open('/tmp/cf-config-updated.json', 'w') as f:
    json.dump(cfg, f, indent=2)
print('Done')
EOF

# 3. 更新を適用（<ETAG> は手順1の値に置換）
aws cloudfront update-distribution \
  --id E214XONKTXJEJD \
  --distribution-config file:///tmp/cf-config-updated.json \
  --if-match <ETAG>

# 4. 反映待ちして検証
aws cloudfront wait distribution-deployed --id E214XONKTXJEJD
curl -sI https://www.aws.ashnova.jp | head -3
```

**再発防止** — `pulumi up --stack production` の前に必ず設定:

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn \
  arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 \
  --stack production
```

**ACM 証明書**（production）: ARN `914b86b1` — ドメイン `www.aws.ashnova.jp`、有効期限 2027-03-12。

---

## [RB-16] Azure FC1 InaccessibleStorageException を修正する（デプロイ用ストレージアカウント削除時）

**発生条件:** `az functionapp deployment source config-zip` が即時失敗し、
`InaccessibleStorageException: BlobUploadFailedException: Name or service not known (xxxxx.blob.core.windows.net:443)` が出る。

**根本原因:** FC1 Function App に紐づく `functionAppConfig.deployment.storage` のストレージアカウントが削除されている。
Kudu の `StorageAccessibleCheck` が通らないため、**すべての** zip deploy がブロックされる。

```bash
RESOURCE_GROUP="multicloud-auto-deploy-staging"   # or -production
FUNCTION_APP="multicloud-auto-deploy-staging-func"
LOCATION="japaneast"

# 1. Function App に設定されている storage endpoint を確認
DEPLOY_STORAGE_URL=$(az rest --method GET \
  --url "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${FUNCTION_APP}?api-version=2023-12-01" \
  | jq -r '.properties.functionAppConfig.deployment.storage.value // empty')
echo "Deployment storage URL: $DEPLOY_STORAGE_URL"

# 2. URL からストレージアカウント名を抽出（形式: https://<name>.blob.core.windows.net/...）
STORAGE_ACCT=$(echo "$DEPLOY_STORAGE_URL" | sed 's|https://||; s|\.blob\.core.*||')
echo "Storage account name: $STORAGE_ACCT"

# 3. アカウント存在確認
if ! az storage account show --name "$STORAGE_ACCT" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  echo "Storage account missing — recreating..."
  az storage account create \
    --name "$STORAGE_ACCT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --allow-blob-public-access false
fi

# 4. connection string を取得し、Kudu が使う app setting を更新
CONN_STR=$(az storage account show-connection-string \
  --name "$STORAGE_ACCT" \
  --resource-group "$RESOURCE_GROUP" \
  --query connectionString --output tsv)

az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings "AzureWebJobsStorage=$CONN_STR"

# 5. さらに、デプロイ後 404 を防ぐため古い WEBSITE_RUN_FROM_PACKAGE を削除
az functionapp config appsettings delete \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --setting-names WEBSITE_RUN_FROM_PACKAGE 2>/dev/null || true

# 6. 設定反映のため Function App を再起動
az functionapp restart --name "$FUNCTION_APP" --resource-group "$RESOURCE_GROUP"
sleep 30

# 7. zip deploy を再実行
az functionapp deployment source config-zip \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --src <path/to/package.zip>
```

**検証:**

```bash
curl -s "https://<func-hostname>/api/HttpTrigger/health" | jq .
# 期待値: {"status":"ok","provider":"azure","version":"X.Y.Z"}
```

**予防策:**

- `deploy-azure.yml` には、毎回このロジックを実行する「Ensure deployment storage account exists」ステップが入っています。
- FC1 Function App と同一リソースグループ内のストレージアカウントを削除する前に、依存関係を必ず確認してください。

---

## [RB-17] マルチクラウドのコスト監視

### ターミナルでフルレポートを出す

```bash
cd /workspaces/multicloud-auto-deploy

# 3クラウド + GitHub の当月コストを表示（デフォルト: 過去3ヶ月）
python3 scripts/cost_report.py

# オプション
python3 scripts/cost_report.py --months 6        # 過去6ヶ月
python3 scripts/cost_report.py --json            # JSON 出力（jq と組み合わせ可）
python3 scripts/cost_report.py --aws-only        # AWS のみ
python3 scripts/cost_report.py --azure-only      # Azure のみ
```

**出力例（2026-02）**

```
 ★ Multi-Cloud Cost Report
────────────────────────────────────────────────────────────
Provider               Period               Cost  Note
────────────────────────────────────────────────────────────
  AWS                  2026-02    ¥18,040 (JPY)  $115.41 × ¥156
  Azure                2026-02   ¥6,970 (JPY)   JPY 建て請求
  GCP                  2026-02         N/A       BQ billing export 参照
  GitHub Actions       2026-02         N/A       1298 runs / cache 1.49 GB
────────────────────────────────────────────────────────────
  TOTAL USD                               0.0000
  TOTAL JPY                              ¥25,010  (円建ての請求)
```

### 認証情報の設定

`scripts/mac-widget/.env` が自動で参照されます（無ければ `scripts/mac-widget/cost-monitor.env.sample` をコピー）。

```bash
cp scripts/mac-widget/cost-monitor.env.sample scripts/mac-widget/.env
# 必要な値を記入
```

| 環境変数                | 用途                      | 取得方法                          |
| ----------------------- | ------------------------- | --------------------------------- |
| `AZURE_SUBSCRIPTION_ID` | Azure Cost Management API | `az account show --query id`      |
| `GCP_BILLING_ACCOUNT`   | GCP Billing               | `gcloud billing accounts list`    |
| `GCP_PROJECT_ID`        | GCP プロジェクト          | `gcloud config get-value project` |
| `GITHUB_TOKEN`          | GitHub Actions 使用量     | `gh auth token`                   |
| `GH_ORG` or `GH_REPO`   | GitHub 対象               | Org 名 or `owner/repo`            |

AWS は `aws configure` 済みのデフォルトプロファイルを使用します（追加設定不要）。

### 為替レート

AWS は USD 建てのため、[open.er-api.com](https://open.er-api.com/v6/latest/USD) からリアルタイムの USD/JPY レートを取得して円換算します。API 障害時は **¥150 固定** にフォールバックします。

### macOS メニューバーウィジェット（xbar）

xbar（<https://xbarapp.com>）を使うと、メニューバーに常時表示できます。

```bash
# 1. xbar をインストール
brew install --cask xbar

# 2. インストール（シンボリックリンク作成 + .env 初期化）
bash scripts/mac-widget/install.sh

# 3. .env に認証情報を記入
open -e scripts/mac-widget/.env
```

**メニューバー表示例**:

```
☁ ¥25,010
────────────────
🟠 AWS    ¥18,040  ($115.41 × ¥156)
🔵 Azure  ¥6,970
🟡 GCP    N/A  [請求先アカウント]
⚫ GitHub   N/A  1298 runs / cache 1.49 GB
────────────────
TOTAL  ¥25,010
```

- 更新間隔: **1時間ごと**（ファイル名 `cost-monitor.1h.py` の `.1h.` で制御）
- 金額の色: `green` < ¥750（$5相当）/ `orange` < ¥4,500（$30相当）/ `red` それ以上
- クリックで各コンソールへ直接遷移

### ファイル構成

| ファイル                                     | 役割                                                       |
| -------------------------------------------- | ---------------------------------------------------------- |
| `scripts/cost_report.py`                     | ターミナル用の月次レポート（`--months N` / `--json` 対応） |
| `scripts/mac-widget/cost-monitor.1h.py`      | xbar プラグイン本体                                        |
| `scripts/mac-widget/cost-monitor.env.sample` | 認証情報テンプレート                                       |
| `scripts/mac-widget/install.sh`              | xbar セットアップスクリプト                                |
| `scripts/mac-widget/.env`                    | 認証情報（**git 管理外**）                                 |

---

## 次のセクション

→ [08 — Security](AI_AGENT_08_SECURITY.md)
