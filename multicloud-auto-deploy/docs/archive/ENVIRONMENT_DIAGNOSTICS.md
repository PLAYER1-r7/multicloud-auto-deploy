# 環境診断とトラブルシューティングガイド

> **AIエージェント向けメモ**: 環境診断ガイド。デプロイ後の動作確認コマンド集。


最終更新: 2026-02-17

## 📋 概要

このドキュメントは、staging/production環境の診断とトラブルシューティングのための実践的なコマンド集です。

---

## 🔍 環境診断スクリプト

### 一括診断スクリプト

全環境を一度に診断するスクリプト：

```bash
#!/bin/bash
# 保存先: scripts/diagnose-environments.sh

echo "============================================"
echo "Multi-Cloud Environment Diagnostics"
echo "============================================"
echo ""

# AWS Staging
echo "🟧 AWS Staging Environment"
echo "-------------------------------------------"
echo "API Endpoint:"
curl -s -w "\nHTTP Status: %{http_code}\n" https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/ | head -5

echo -e "\nFrontend CloudFront:"
curl -s -I https://d1tf3uumcm4bo1.cloudfront.net/ | grep -E "HTTP|content-type" | head -2

echo -e "\nLambda Configuration:"
aws lambda get-function \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --query 'Configuration.{Runtime:Runtime,Handler:Handler,CodeSize:CodeSize,Layers:Layers}' 2>/dev/null

echo -e "\nLambda Recent Errors:"
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --since 10m \
  --format short \
  --filter-pattern "ERROR" 2>/dev/null | tail -5

echo ""
echo ""

# Azure Staging
echo "🟦 Azure Staging Environment"
echo "-------------------------------------------"
echo "API Endpoint:"
curl -s -w "\nHTTP Status: %{http_code}\n" https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/HttpTrigger/ | head -5

echo -e "\nFrontend Azure Front Door:"
curl -s -I https://multicloud-frontend-f9cvamfnauexasd8.z01.azurefd.net/ | grep -E "HTTP|content-type" | head -2

echo ""
echo ""

# GCP Staging
echo "🟩 GCP Staging Environment"
echo "-------------------------------------------"
echo "API Endpoint:"
curl -s -w "\nHTTP Status: %{http_code}\n" https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app/ | head -5

echo -e "\nFrontend Load Balancer:"
curl -s -I http://34.117.111.182/ | grep -E "HTTP|content-type" | head -2

echo ""
echo ""

# CI/CD Status
echo "🔄 CI/CD Workflow Status"
echo "-------------------------------------------"
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?per_page=5" | \
  jq -r '.workflow_runs[] | "\(.created_at | .[0:19]) - \(.name) [\(.head_branch)]: \(.conclusion // "running")"'

echo ""
echo "============================================"
echo "Diagnostics Complete"
echo "============================================"
```

### 使用方法

```bash
cd /workspaces/ashnova/multicloud-auto-deploy
chmod +x scripts/diagnose-environments.sh
./scripts/diagnose-environments.sh
```

---

## 🟧 AWS トラブルシューティング

### Lambda関数のエラー診断

#### 1. 最近のエラーログを確認

```bash
# 最近30分のエラーログ
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --since 30m \
  --format short \
  --filter-pattern "ERROR" | tail -20

# ImportModuleErrorの確認
aws logs tail /aws/lambda/multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --since 30m \
  --format short \
  --filter-pattern "ImportModuleError" | tail -10
```

#### 2. Lambda関数の設定確認

```bash
# 基本設定
aws lambda get-function \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --query 'Configuration.{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,CodeSize:CodeSize,Layers:Layers,Environment:Environment}'

# Layer情報の詳細
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --region ap-northeast-1 \
  --query 'Layers[*].{Arn:Arn,CodeSize:CodeSize}'
```

#### 3. Lambda Layerの確認

```bash
# 現在アタッチされているLayerのリスト
aws lambda list-layer-versions \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --region ap-northeast-1 \
  --query 'LayerVersions[*].{Version:Version,LayerVersionArn:LayerVersionArn,CreatedDate:CreatedDate}'
```

### Lambda Layerの手動デプロイ

#### ステップ1: Layerのビルド

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# 既存のビルドをクリーンアップ
rm -rf .build-layer lambda-layer.zip

# Layerをビルド
bash ../../scripts/build-lambda-layer.sh

# ビルド結果の確認
ls -lh lambda-layer.zip
```

#### ステップ2: Layerの公開

```bash
# Layerを公開
LAYER_VERSION_ARN=$(aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --description "Dependencies for FastAPI + Mangum + JWT (Python 3.12)" \
  --zip-file fileb://lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --region ap-northeast-1 \
  --query LayerVersionArn \
  --output text)

echo "✅ Layer published: $LAYER_VERSION_ARN"
```

#### ステップ3: Lambda関数にLayerをアタッチ

```bash
# Lambda関数の設定を更新
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --layers $LAYER_VERSION_ARN \
  --region ap-northeast-1

echo "✅ Layer attached to Lambda function"

# 設定が反映されるまで待機（約10秒）
sleep 10
```

#### ステップ4: 動作確認

```bash
# ヘルスチェック
echo "Testing API endpoint..."
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/ | jq '.'

# メッセージ一覧取得
curl -s https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com/api/messages/ | jq '.'
```

### Lambda関数コードの再デプロイ

#### パッケージの作成と更新

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# コードのパッケージング
rm -rf .build lambda.zip
mkdir -p .build/package

# アプリケーションコードのみコピー（依存関係はLayerから）
cp -r app .build/package/
cp index.py .build/package/

# ZIPファイルの作成
cd .build/package
zip -r ../../lambda.zip .
cd ../..

# Lambda関数の更新
aws lambda update-function-code \
  --function-name multicloud-auto-deploy-staging-api \
  --zip-file fileb://lambda.zip \
  --region ap-northeast-1

echo "✅ Lambda function code updated"
```

---

## 🟦 Azure トラブルシューティング

### Function Appのエラー診断

#### 1. Function Appのログストリーミング

```bash
# リアルタイムログの表示
az functionapp log tail \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg
```

#### 2. Function Appの設定確認

```bash
# 基本設定
az functionapp show \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg \
  --query '{name:name,state:state,runtime:siteConfig.linuxFxVersion,location:location}'

# 環境変数の確認
az functionapp config appsettings list \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg
```

#### 3. Function Appの再起動

```bash
# Function Appを再起動
az functionapp restart \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg

echo "✅ Function App restarted"
```

### Function Appの手動デプロイ

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# デプロイパッケージの作成
rm -rf .deploy-azure function-app.zip
mkdir -p .deploy-azure

# ファイルのコピー
cp -r app .deploy-azure/
cp function_app.py .deploy-azure/
cp host.json .deploy-azure/
cp requirements-azure.txt .deploy-azure/requirements.txt

# ZIPファイルの作成
cd .deploy-azure
zip -r ../function-app.zip .
cd ..

# Azureへデプロイ
az functionapp deployment source config-zip \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging-rg \
  --src function-app.zip

echo "✅ Function App deployed"
```

---

## 🟩 GCP トラブルシューティング

### Cloud Runのエラー診断

#### 1. Cloud Runのログ確認

```bash
# 最近のログを表示
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=multicloud-auto-deploy-staging-api" \
  --limit 50 \
  --format json \
  --project ashnova | jq -r '.[] | "\(.timestamp) [\(.severity)] \(.textPayload // .jsonPayload)"'

# エラーログのみ表示
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=multicloud-auto-deploy-staging-api AND severity>=ERROR" \
  --limit 20 \
  --format json \
  --project ashnova
```

#### 2. Cloud Runサービスの設定確認

```bash
# サービスの詳細
gcloud run services describe multicloud-auto-deploy-staging-api \
  --region asia-northeast1 \
  --project ashnova

# 環境変数の確認
gcloud run services describe multicloud-auto-deploy-staging-api \
  --region asia-northeast1 \
  --project ashnova \
  --format="value(spec.template.spec.containers[0].env)"
```

#### 3. リビジョン情報の確認

```bash
# 最新のリビジョン
gcloud run revisions list \
  --service multicloud-auto-deploy-staging-api \
  --region asia-northeast1 \
  --project ashnova \
  --limit 5
```

### Cloud Runサービスの手動デプロイ

#### Dockerイメージのビルドとプッシュ

```bash
cd /workspaces/ashnova/multicloud-auto-deploy/services/api

# Artifact Registryの認証
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# イメージのビルド
docker build --platform linux/amd64 \
  -t asia-northeast1-docker.pkg.dev/ashnova/mcad-staging-repo/multicloud-auto-deploy-api:latest \
  -f Dockerfile.gcp .

# イメージのプッシュ
docker push asia-northeast1-docker.pkg.dev/ashnova/mcad-staging-repo/multicloud-auto-deploy-api:latest

echo "✅ Docker image pushed"
```

#### Cloud Runサービスの更新

```bash
# 新しいイメージでサービスを更新
gcloud run deploy multicloud-auto-deploy-staging-api \
  --image asia-northeast1-docker.pkg.dev/ashnova/mcad-staging-repo/multicloud-auto-deploy-api:latest \
  --region asia-northeast1 \
  --project ashnova \
  --allow-unauthenticated

echo "✅ Cloud Run service updated"
```

---

## 🔄 CI/CD トラブルシューティング

### ワークフロー実行状況の確認

#### 最新のワークフロー実行

```bash
# 最新10件の実行状況
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?per_page=10" | \
  jq -r '.workflow_runs[] | "\(.created_at | .[0:19]) - \(.name) [\(.head_branch)]: \(.status) - \(.conclusion // "running")"'
```

#### 特定のワークフロー実行の詳細

```bash
# 実行IDを指定して詳細を取得
RUN_ID=22107983145
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs/$RUN_ID" | \
  jq '{id, name, status, conclusion, head_branch, head_sha, created_at, updated_at}'
```

#### 失敗したステップの特定

```bash
# 失敗したステップの情報を取得
RUN_ID=22107983145
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs/$RUN_ID/jobs" | \
  jq -r '.jobs[0] | {name, conclusion, failed_steps: [.steps[] | select(.conclusion == "failure") | {step_name: .name, conclusion}]}'
```

### ワークフローの手動トリガー（要GitHub CLI認証）

```bash
# GitHub CLIでログイン
gh auth login

# AWSデプロイをstaging環境でトリガー
gh workflow run deploy-aws.yml --ref develop -f environment=staging

# Azureデプロイをstaging環境でトリガー
gh workflow run deploy-azure.yml --ref develop -f environment=staging

# GCPデプロイをstaging環境でトリガー
gh workflow run deploy-gcp.yml --ref develop -f environment=staging
```

---

## 📝 診断チェックリスト

### AWS Lambda

- [ ] Lambda関数が存在する
- [ ] Lambda Layerがアタッチされている
- [ ] Handler設定が正しい（index.handler）
- [ ] Runtime設定が正しい（python3.12）
- [ ] 環境変数が設定されている
- [ ] CloudWatch Logsにエラーがない
- [ ] API GatewayがLambda関数と統合されている

### Azure Function App

- [ ] Function Appが実行中（Running状態）
- [ ] Runtimeバージョンが正しい（Python 3.12）
- [ ] requirements.txtの依存関係がインストールされている
- [ ] 環境変数が設定されている
- [ ] HTTPトリガーが正しく設定されている
- [ ] ログストリームにエラーがない

### GCP Cloud Run

- [ ] Cloud Runサービスがデプロイされている
- [ ] 最新のリビジョンがアクティブ
- [ ] コンテナイメージが正しい
- [ ] 環境変数が設定されている
- [ ] IAM権限が正しく設定されている（allUsersにinvoker）
- [ ] Cloud Loggingにエラーがない
- [ ] Firestoreデータベースが有効

### CI/CD

- [ ] GitHub Secretsが正しく設定されている
- [ ] Pulumiスタックが存在する
- [ ] ワークフローファイルの構文が正しい
- [ ] ブランチ保護ルールが適切
- [ ] 依存関係のビルドステップが成功している

---

## 🚨 よくある問題と解決策

### 問題: Lambda "No module named 'mangum'" エラー

**原因**: Lambda Layerがアタッチされていない、または依存関係が含まれていない

**解決策**:

1. Lambda Layerを再ビルドして公開
2. Lambda関数にLayerをアタッチ
3. 関数を再デプロイ

👉 [AWS トラブルシューティング > Lambda Layerの手動デプロイ](#lambda-layerの手動デプロイ)

---

### 問題: GCP Cloud Run /api/messages/ が500エラー

**原因**: Firestoreの接続エラー、またはルーティングの問題

**解決策**:

1. Cloud Runのログを確認
2. Firestore IAM権限を確認
3. 環境変数（GOOGLE_CLOUD_PROJECT）を確認

```bash
# ログの確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=multicloud-auto-deploy-staging-api AND severity>=ERROR" \
  --limit 20 \
  --project ashnova

# 環境変数の確認
gcloud run services describe multicloud-auto-deploy-staging-api \
  --region asia-northeast1 \
  --project ashnova \
  --format="value(spec.template.spec.containers[0].env)"
```

---

### 問題: CI/CD "Initialize Pulumi Stack" 失敗

**原因**: スタック名のハードコーディング、またはPULUMI_ACCESS_TOKEN無効

**解決策**:

1. GitHub SecretsのPULUMI_ACCESS_TOKENを確認
2. ワークフローファイルのスタック名設定を確認
3. Pulumiコンソールでスタックの存在を確認

```bash
# Pulumiスタックの確認
cd /workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/aws
pulumi stack ls
```

---

## 📚 関連ドキュメント

- [AWS Lambda Layer最適化戦略](./AWS_LAMBDA_LAYER_STRATEGY.md) ⭐ **NEW** - 依存関係管理のベストプラクティス
- [環境ステータスレポート](./ENVIRONMENT_STATUS.md)
- [デプロイ失敗調査レポート](./DEPLOYMENT_FAILURE_INVESTIGATION.md)
- [デプロイ監視ガイド](./DEPLOYMENT_MONITORING.md)
- [クイックリファレンス](./QUICK_REFERENCE.md)

---

## 🔄 更新履歴

- **2026-02-17**: 初版作成
  - 各クラウドプロバイダーの診断コマンドを追加
  - 一般的な問題と解決策を文書化
  - 診断スクリプトの追加
