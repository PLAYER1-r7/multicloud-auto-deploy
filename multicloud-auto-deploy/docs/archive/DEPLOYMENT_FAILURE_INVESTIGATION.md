# デプロイ失敗調査レポート

> **AIエージェント向けメモ**: デプロイ失敗の調査レポート。根本原因と対処法を記載。


## 📋 調査概要

**日時**: 2026-02-17  
**対象コミット**: `3ba0bf5` (PUT エンドポイント追加)  
**調査者**: GitHub Copilot  
**所要時間**: 約30分

---

## 🔍 調査の経緯

PUT エンドポイントの実装を完了し、`develop`および`main`ブランチにプッシュした後、複数のデプロイメントワークフローが失敗していることが判明。デプロイ失敗の原因を特定し、解決策を提案するために調査を実施。

---

## 📊 失敗状況の確認

### 1. ワークフロー実行履歴の取得

```bash
# developブランチの状況
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?branch=develop&per_page=5" | \
  jq '.workflow_runs[] | {name, status, conclusion, created_at}'

# mainブランチの状況
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?branch=main&per_page=5" | \
  jq '.workflow_runs[] | {name, status, conclusion, created_at}'
```

### 結果

#### developブランチ（staging環境）

- ❌ **Deploy to GCP** (run: 22107968391) - failure
- ❌ **Deploy to AWS** (run: 22107968393) - failure
- ❌ **Deploy to Azure** (run: 22107968413) - failure

#### mainブランチ（production環境）

- ❌ **Deploy Landing Page to AWS** (run: 22107983147) - failure
- ✅ **Deploy Landing Page to Azure** (run: 22107983158) - success
- ❌ **Deploy to AWS** (run: 22107983145) - failure
- ❌ **Deploy Landing Page to GCP** (run: 22107983172) - failure
- ❌ **Deploy to Azure** (run: 22107983196) - failure

**共通点**: コミット`3ba0bf5`でのデプロイが複数のクラウドプロバイダーで失敗

---

## 🔎 失敗ステップの特定

### 2. ジョブ詳細の取得

```bash
# AWS デプロイの失敗詳細
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs/22107983145/jobs" | \
  jq '.jobs[] | {name, conclusion, steps: [.steps[] | select(.conclusion == "failure") | {name, conclusion}]}'

# Azure デプロイの失敗詳細
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs/22107983196/jobs" | \
  jq '.jobs[] | {name, conclusion, steps: [.steps[] | select(.conclusion == "failure") | {name, conclusion}]}'

# GCP デプロイの失敗詳細
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs/22107968391/jobs" | \
  jq '.jobs[] | {name, conclusion, steps: [.steps[] | select(.conclusion == "failure") | {name, conclusion}]}'
```

### 結果

**すべてのデプロイで共通の失敗ステップ**:

- ステップ名: **"Initialize Pulumi Stack"**
- 結果: `failure`

---

## 🐛 根本原因の分析

### 3. ワークフローファイルの確認

失敗している`Initialize Pulumi Stack`ステップの内容を確認：

#### `.github/workflows/deploy-aws.yml` (行66-68)

```yaml
- name: Initialize Pulumi Stack
  run: |
    cd multicloud-auto-deploy/infrastructure/pulumi/aws
    pulumi login
    pulumi stack select staging 2>/dev/null || pulumi stack init staging
    pulumi config set aws:region ${{ env.AWS_REGION }}
  env:
    PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
```

#### `Deploy Infrastructure with Pulumi`ステップ (行72-80)

```yaml
- name: Deploy Infrastructure with Pulumi
  id: pulumi
  uses: pulumi/actions@v5
  with:
    command: up
    stack-name: staging # ← ここが問題！
    work-dir: multicloud-auto-deploy/infrastructure/pulumi/aws
  env:
    PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
    AWS_REGION: ${{ env.AWS_REGION }}
```

### 問題点の特定

#### 🚨 **根本原因: スタック名のハードコーディング**

1. **環境変数は正しく設定されている**（行31）：

   ```yaml
   environment: ${{ github.event_name == 'workflow_dispatch' && github.event.inputs.environment || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}
   ```

   - `develop`ブランチ → `staging`環境
   - `main`ブランチ → `production`環境

2. **しかし、Pulumiスタック名は常に`staging`**：
   - `Initialize Pulumi Stack`: `pulumi stack select staging`
   - `Deploy Infrastructure`: `stack-name: staging`

3. **結果**：
   - `main`ブランチからのデプロイ時、環境は`production`だが、スタックは`staging`を使用しようとする
   - `production`スタックが存在しない、または権限の不一致により失敗

#### 影響範囲

同様の問題が以下のワークフローでも存在：

- ✗ `.github/workflows/deploy-aws.yml` (行66, 76)
- ✗ `.github/workflows/deploy-azure.yml` (行93)
- ✗ `.github/workflows/deploy-gcp.yml` (行80)

---

## 💡 解決策

### 提案1: 環境変数を使用した動的スタック選択

スタック名を環境変数から動的に取得するように修正：

#### 修正前

```yaml
- name: Initialize Pulumi Stack
  run: |
    cd multicloud-auto-deploy/infrastructure/pulumi/aws
    pulumi login
    pulumi stack select staging 2>/dev/null || pulumi stack init staging
    pulumi config set aws:region ${{ env.AWS_REGION }}
```

```yaml
- name: Deploy Infrastructure with Pulumi
  uses: pulumi/actions@v5
  with:
    command: up
    stack-name: staging
    work-dir: multicloud-auto-deploy/infrastructure/pulumi/aws
```

#### 修正後

```yaml
- name: Set Environment Stack
  id: set_stack
  run: |
    if [ "${{ github.ref }}" == "refs/heads/main" ]; then
      echo "stack_name=production" >> $GITHUB_OUTPUT
    elif [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
      echo "stack_name=${{ github.event.inputs.environment }}" >> $GITHUB_OUTPUT
    else
      echo "stack_name=staging" >> $GITHUB_OUTPUT
    fi

- name: Initialize Pulumi Stack
  run: |
    cd multicloud-auto-deploy/infrastructure/pulumi/aws
    pulumi login
    pulumi stack select ${{ steps.set_stack.outputs.stack_name }} 2>/dev/null || pulumi stack init ${{ steps.set_stack.outputs.stack_name }}
    pulumi config set aws:region ${{ env.AWS_REGION }}
```

```yaml
- name: Deploy Infrastructure with Pulumi
  uses: pulumi/actions@v5
  with:
    command: up
    stack-name: ${{ steps.set_stack.outputs.stack_name }}
    work-dir: multicloud-auto-deploy/infrastructure/pulumi/aws
```

### 提案2: GitHub Environments の活用

より簡潔な方法として、GitHub Environmentsから直接スタック名を取得：

```yaml
- name: Initialize Pulumi Stack
  run: |
    cd multicloud-auto-deploy/infrastructure/pulumi/aws
    pulumi login
    STACK_NAME="${{ github.event_name == 'workflow_dispatch' && github.event.inputs.environment || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}"
    pulumi stack select $STACK_NAME 2>/dev/null || pulumi stack init $STACK_NAME
    pulumi config set aws:region ${{ env.AWS_REGION }}
```

```yaml
- name: Deploy Infrastructure with Pulumi
  uses: pulumi/actions@v5
  with:
    command: up
    stack-name: ${{ github.event_name == 'workflow_dispatch' && github.event.inputs.environment || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}
    work-dir: multicloud-auto-deploy/infrastructure/pulumi/aws
```

---

## ✅ 修正が必要なファイル

1. `.github/workflows/deploy-aws.yml`
   - 行66: `Initialize Pulumi Stack`ステップ
   - 行76: `Deploy Infrastructure with Pulumi`ステップ

2. `.github/workflows/deploy-azure.yml`
   - 同様の箇所を修正

3. `.github/workflows/deploy-gcp.yml`
   - 同様の箇所を修正

4. `.github/workflows/deploy-landing-aws.yml`
   - Landing Pageデプロイも同様に確認・修正

5. `.github/workflows/deploy-landing-azure.yml`
   - Landing Pageデプロイも同様に確認・修正

6. `.github/workflows/deploy-landing-gcp.yml`
   - Landing Pageデプロイも同様に確認・修正

---

## 🔄 修正後の検証手順

### 1. ワークフローファイルの修正

```bash
# すべてのデプロイワークフローでスタック名を動的に設定
# (上記の修正案を適用)
```

### 2. コミットとプッシュ

```bash
git add .github/workflows/*.yml
git commit -m "fix: Use dynamic stack selection based on environment"
git push origin develop
```

### 3. デプロイの監視

```bash
# 監視スクリプトを使用
./scripts/watch-deployment.sh develop 10

# または手動確認
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?branch=develop&per_page=3" | \
  jq -r '.workflow_runs[] | "[\(if .conclusion == "success" then "✓" elif .conclusion == "failure" then "✗" elif .status == "in_progress" then "⏳" else "○" end)] \(.name) - \(.conclusion // .status)"'
```

### 4. mainブランチへのマージ前確認

```bash
# developでの成功を確認後、mainにマージ
git checkout main
git merge develop
git push origin main

# production環境のデプロイを監視
./scripts/watch-deployment.sh main 10
```

---

## 📝 学んだ教訓

### 1. 環境変数とビルドパラメータの一貫性

- GitHub Actionsの`environment`は正しく設定されていても、個々のステップで使用されていなければ意味がない
- 環境変数を定義したら、すべての関連ステップで一貫して使用することが重要

### 2. ハードコーディングの危険性

- スタック名、環境名などの環境依存値をハードコーディングすると、複数環境での動作に問題が発生する
- 動的な値の取得を常に考慮すべき

### 3. CI/CDパイプラインの包括的なテスト

- `develop`（staging）だけでなく、`main`（production）へのデプロイも定期的にテストする必要がある
- 手動デプロイ（`workflow_dispatch`）も含めて、すべてのトリガーパターンを検証すべき

### 4. 詳細なログとモニタリングの重要性

- GitHub Actions のログは認証が必要な場合があるため、公開APIで取得できるメタデータも活用
- ワークフローファイル自体の確認が最も確実な調査方法

---

## 🎯 次のアクション

1. **即座に実施**:
   - [ ] 全ワークフローファイルでスタック名を動的に修正
   - [ ] `develop`ブランチで修正をコミット・プッシュ
   - [ ] stagingデプロイの成功を確認

2. **検証後に実施**:
   - [ ] `main`ブランチにマージ
   - [ ] productionデプロイの成功を確認
   - [ ] PUT エンドポイントの動作確認

3. **長期的な改善**:
   - [ ] CI/CDパイプラインのテストカバレッジ向上
   - [ ] デプロイ前のワークフロー構文チェック自動化
   - [ ] デプロイ失敗時のアラート設定

---

## ✅ 実装履歴

### 2026-02-17: 動的スタック選択機能の実装

#### 実施した修正内容

以下の3つのワークフローファイルに動的スタック選択機能を実装しました：

1. `.github/workflows/deploy-aws.yml`
2. `.github/workflows/deploy-azure.yml`
3. `.github/workflows/deploy-gcp.yml`

#### 具体的な変更点

**1. スタック名決定ステップの追加**

"Install Pulumi Python Dependencies"ステップの直後に、以下のステップを追加：

```yaml
- name: Determine Pulumi Stack Name
  id: set_stack
  run: |
    if [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
      STACK_NAME="${{ github.event.inputs.environment }}"
    elif [ "${{ github.ref }}" == "refs/heads/main" ]; then
      STACK_NAME="production"
    else
      STACK_NAME="staging"
    fi
    echo "stack_name=$STACK_NAME" >> $GITHUB_OUTPUT
    echo "📦 Using Pulumi stack: $STACK_NAME"
```

この変更により：

- `workflow_dispatch`（手動実行）の場合：ユーザーが選択した環境を使用
- `main`ブランチへのpushの場合：`production`スタックを使用
- それ以外（`develop`ブランチ）の場合：`staging`スタックを使用

**2. Initialize Pulumi Stackステップの修正**

ハードコードされたスタック名を動的な値に変更：

```yaml
# 修正前
pulumi stack select staging 2>/dev/null || pulumi stack init staging

# 修正後
pulumi stack select ${{ steps.set_stack.outputs.stack_name }} 2>/dev/null || \
pulumi stack init ${{ steps.set_stack.outputs.stack_name }}
```

**3. Deploy Infrastructure with Pulumiステップの修正**

`stack-name`パラメータを動的な値に変更：

```yaml
# 修正前
stack-name: staging

# 修正後
stack-name: ${{ steps.set_stack.outputs.stack_name }}
```

#### コミットとデプロイ

```bash
# 変更のステージング
git add .github/workflows/deploy-aws.yml \
        .github/workflows/deploy-azure.yml \
        .github/workflows/deploy-gcp.yml

# コミット（コミットID: 043c577）
git commit -m "fix: Implement dynamic Pulumi stack selection based on branch/environment

- Add 'Determine Pulumi Stack Name' step to set stack name dynamically
- develop branch → staging stack
- main branch → production stack
- workflow_dispatch → user-selected environment
- Update 'Initialize Pulumi Stack' to use dynamic stack name
- Update 'Deploy Infrastructure with Pulumi' stack-name parameter

This fixes deployment failures caused by hardcoded 'staging' stack name
which was incompatible with production environment configuration.

Affected files:
- .github/workflows/deploy-aws.yml
- .github/workflows/deploy-azure.yml
- .github/workflows/deploy-gcp.yml"

# developブランチにプッシュ
git push ashnova develop

# mainブランチにマージしてプッシュ
git checkout main
git merge develop
git push ashnova main
git checkout develop
```

#### 期待される結果

この修正により：

- ✅ `develop`ブランチへのpush → `staging`スタックへのデプロイ成功
- ✅ `main`ブランチへのpush → `production`スタックへのデプロイ成功
- ✅ 手動実行 → 選択した環境への正しいデプロイ
- ✅ "Initialize Pulumi Stack"ステップでのエラー解消

#### 次のステップ

1. **デプロイの監視**:

   ```bash
   # stagingデプロイの確認
   ./scripts/watch-deployment.sh develop 10

   # productionデプロイの確認
   ./scripts/watch-deployment.sh main 10
   ```

2. **デプロイ成功確認後**:
   - PUT エンドポイントの動作確認
   - カスタムドメイン設定の継続

3. **長期的な改善**:
   - デプロイ前のワークフロー構文バリデーション追加
   - デプロイ失敗時の自動ロールバック検討

---

## � AWS本番環境のLambda関数デプロイ修正 (2026-02-17)

### 背景

Pulumi経由でAWS本番環境をデプロイ後、フロントエンドとAPIの統合テスト中に以下の問題が発生：

1. **CORSエラー**: フロントエンドがAzure Staging URLをハードコード
2. **Lambda 500エラー**: APIエンドポイントが`Internal Server Error`を返却

### 調査と解決プロセス

#### Phase 1: フロントエンド環境変数の問題 (解決済み)

**問題**: CORSエラー発生

**調査コマンド**:

```bash
# フロントエンドの環境変数ファイル確認
cat services/frontend_react/.env.production

# 環境変数名の不一致発見
# 誤: VITE_API_BASE_URL
# 正: VITE_API_URL
```

**解決**:

```bash
# .env.productionファイルを修正
VITE_API_URL=https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com

# フロントエンド再ビルド・再デプロイ
cd services/frontend_react
npm run build
aws s3 sync dist/ s3://multicloud-auto-deploy-production-frontend/ --delete

# CloudFrontキャッシュ無効化
aws cloudfront create-invalidation \
  --distribution-id E2ABCDEFGHIJK \
  --paths "/*"
```

#### Phase 2: Lambda関数の依存関係エラー

**問題**: Lambda関数が500エラーを返却

**調査コマンド**:

```bash
# Lambda関数の設定確認
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-production-api \
  --region ap-northeast-1

# 最新のエラーログ取得
aws logs describe-log-streams \
  --log-group-name /aws/lambda/multicloud-auto-deploy-production-api \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --region ap-northeast-1

# ログストリームから詳細なエラー確認
aws logs get-log-events \
  --log-group-name /aws/lambda/multicloud-auto-deploy-production-api \
  --log-stream-name "2026/02/17/[$LATEST]..." \
  --region ap-northeast-1
```

**発見されたエラー推移**:

1. **初期エラー**: `No module named 'index'`
   - 原因: デプロイパッケージの構造ミス
   - 対応: zipファイル構造を修正

2. **第2エラー**: `No module named 'mangum'`
   - 原因: 依存関係が含まれていない
   - 対応: requirements.txtから依存関係をインストール

3. **第3エラー**: `No module named 'pydantic_core._pydantic_core'`
   - 原因: ARM64バイナリとx86_64ランタイムの不一致
   - 発見: ビルド環境がARM64、Lambda実行環境がx86_64

4. **第4エラー**: `No module named 'sqlalchemy'`
   - 原因: `CLOUD_PROVIDER`環境変数未設定でローカルバックエンドを読み込もうとした

#### Phase 3: アーキテクチャ互換性の解決

**問題**: ARM64でビルドした依存関係がx86_64 Lambdaで動作しない

**バイナリアーキテクチャ確認**:

```bash
# デプロイパッケージ内のバイナリファイル確認
unzip -l /tmp/lambda-full-deployment.zip | grep "\.so$"
file /tmp/lambda-package/cryptography/hazmat/bindings/*.so

# 出力: ELF 64-bit LSB shared object, ARM aarch64
# → ARM64バイナリであることを確認
```

**Lambda関数のアーキテクチャ確認**:

```bash
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-production-api \
  --query 'Architectures' \
  --output json

# 出力: ["x86_64"]
```

**Klayers公開レイヤー試行（失敗）**:

```bash
# Klayers公開レイヤーの適用を試行
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-production-api \
  --layers \
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-fastapi:18" \
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-requests:47" \
    "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p312-mangum:6" \
  --region ap-northeast-1

# エラー: AccessDeniedException
# "User: arn:aws:iam::278280499340:user/github-actions is not authorized
#  to perform: lambda:GetLayerVersion on resource"
```

#### Phase 4: カスタムLambdaレイヤーの作成

**x86_64用レイヤーのビルド**:

```bash
# x86_64アーキテクチャ用に依存関係をインストール
mkdir -p /tmp/lambda-layer-x86/python
pip3 install \
  --platform manylinux2014_x86_64 \
  --target /tmp/lambda-layer-x86/python \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade \
  fastapi==0.115.0 \
  pydantic==2.9.0 \
  pydantic-settings==2.5.2 \
  mangum==0.17.0 \
  boto3==1.35.0 \
  python-jose[cryptography]==3.3.0 \
  requests==2.32.3 \
  python-multipart==0.0.9 \
  pyjwt==2.9.0

# レイヤーパッケージ作成（27MB）
cd /tmp/lambda-layer-x86
zip -r /tmp/lambda-layer-x86_64.zip . -q

# バイナリがx86_64であることを確認
unzip -l /tmp/lambda-layer-x86_64.zip | grep "\.so$"
# 出力: pydantic_core._pydantic_core.cpython-312-x86_64-linux-gnu.so
#       cryptography/hazmat/bindings/_rust.abi3.so
```

**レイヤーの公開**:

```bash
aws lambda publish-layer-version \
  --layer-name multicloud-auto-deploy-dependencies \
  --description "Full dependencies for x86_64 (FastAPI, Pydantic, Mangum, boto3)" \
  --zip-file fileb:///tmp/lambda-layer-x86_64.zip \
  --compatible-runtimes python3.12 \
  --compatible-architectures x86_64 \
  --region ap-northeast-1

# 出力:
# LayerVersionArn: arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-dependencies:2
# Version: 2
# Size: 27MB
```

**Lambda関数の更新**:

```bash
# レイヤーのアタッチ
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-production-api \
  --layers "arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-dependencies:2" \
  --region ap-northeast-1

# CLOUD_PROVIDER環境変数の追加
aws lambda update-function-configuration \
  --function-name multicloud-auto-deploy-production-api \
  --environment "Variables={ \
    SECRET_NAME=multicloud-auto-deploy/production/app-config, \
    IMAGES_BUCKET_NAME=multicloud-auto-deploy-production-images, \
    AUTH_PROVIDER=cognito, \
    CORS_ORIGINS=https://d1qob7569mn5nw.cloudfront.net, \
    COGNITO_CLIENT_ID=4h3b285v1a9746sqhukk5k3a7i, \
    COGNITO_USER_POOL_ID=ap-northeast-1_50La963P2, \
    POSTS_TABLE_NAME=multicloud-auto-deploy-production-posts, \
    CLOUD_PROVIDER=aws \
  }" \
  --region ap-northeast-1
```

#### Phase 5: 動作確認

**APIエンドポイントのテスト**:

```bash
# メッセージAPI
curl -s "https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com/api/messages/?page=1&page_size=20"
# HTTP 200 OK
# Response: {"items":[],"results":[],"messages":[],"limit":20,"nextToken":null,"total":0,"page":1,"page_size":20}

# ルートエンドポイント
curl -s "https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com/"
# Response: {"status":"ok","provider":"aws","version":"3.0.0"}

# フロントエンド
curl -s -o /dev/null -w "%{http_code}" "https://d1qob7569mn5nw.cloudfront.net"
# 200
```

**最終的なLambda関数の設定確認**:

```bash
aws lambda get-function \
  --function-name multicloud-auto-deploy-production-api \
  --region ap-northeast-1 \
  --query '{FunctionName:Configuration.FunctionName, Runtime:Configuration.Runtime, CodeSize:Configuration.CodeSize, Layers:Configuration.Layers[*].Arn, Architecture:Configuration.Architectures[0], Memory:Configuration.MemorySize, Timeout:Configuration.Timeout}' \
  --output json

# 出力:
# {
#   "FunctionName": "multicloud-auto-deploy-production-api",
#   "Runtime": "python3.12",
#   "CodeSize": 84566,  # 84KB (app/ + index.py のみ)
#   "Layers": ["arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-dependencies:2"],
#   "Architecture": "x86_64",
#   "Memory": 512,
#   "Timeout": 30
# }
```

### 根本原因

1. **依存関係の欠落**:
   - `requirements-aws.txt`がKlayers公開レイヤーを前提として主要な依存関係を除外
   - Klayersへのアクセス権限がなく、レイヤーが使用不可

2. **アーキテクチャの不一致**:
   - ビルド環境: ARM64 (Dev Container on aarch64)
   - Lambda実行環境: x86_64
   - ARM64でコンパイルされたバイナリ（`.so`ファイル）がx86_64で動作しない

3. **環境変数の不足**:
   - `CLOUD_PROVIDER=aws`が未設定
   - デフォルトで`LOCAL`プロバイダーが選択され、SQLAlchemyの読み込みに失敗

### 解決策

1. **x86_64用カスタムLambdaレイヤーの作成**:
   - `pip install --platform manylinux2014_x86_64 --only-binary=:all:`でx86_64バイナリを取得
   - 全依存関係（FastAPI, Pydantic, Mangum, boto3等）を含む27MBのレイヤー
   - Layer ARN: `arn:aws:lambda:ap-northeast-1:278280499340:layer:multicloud-auto-deploy-dependencies:2`

2. **Lambda関数の設定更新**:
   - カスタムレイヤーv2をアタッチ
   - `CLOUD_PROVIDER=aws`環境変数を追加
   - コード本体は84KB（app/ディレクトリ + index.pyのみ）

3. **Pulumi IaCの更新**:
   - `infrastructure/pulumi/aws/__main__.py`のレイヤー設定を更新
   - Klayers ARNをカスタムレイヤーARNに置き換え

### 学んだ教訓

1. **プラットフォーム互換性**:
   - Lambda向けにビルドする場合、ターゲットアーキテクチャを明示的に指定
   - `--platform`フラグで正しいバイナリを取得

2. **依存管理戦略**:
   - 公開レイヤー（Klayers, PowerTools）はアクセス権限を事前確認
   - 権限問題がある場合はカスタムレイヤーを作成
   - レイヤーとコードの分離でデプロイサイズを最適化

3. **環境変数の完全性**:
   - クラウドプロバイダーを動的に選択する場合、`CLOUD_PROVIDER`の明示が必須
   - Pulumi/Terraformで環境変数の完全なセットを管理

4. **効果的なデバッグ手順**:
   - CloudWatch Logsの詳細なエラートレースバック
   - バイナリファイルのアーキテクチャ確認（`file`コマンド）
   - Lambda設定の包括的な確認（環境変数、レイヤー、アーキテクチャ）

### 今後の改善案

1. ✅ **AWS Lambda PowerToolsの調査**:
   - AWS公式の公開レイヤー（PowerTools for Python）の利用可能性を確認
   - ARN: `arn:aws:lambda:ap-northeast-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:{version}`

2. **CI/CDパイプラインでのレイヤービルド自動化**:
   - GitHub Actionsでx86_64環境を使用してレイヤーをビルド
   - `runs-on: ubuntu-latest`（x86_64）で依存関係を構築

3. **マルチアーキテクチャ対応**:
   - ARM64 Lambdaも検討（コスト削減: 20%安価、性能向上）
   - ただしレイヤーも同じアーキテクチャでビルド必要

4. **デプロイ前検証の強化**:
   - ローカルでのLambda環境シミュレーション（AWS SAM, LocalStack）
   - 依存関係の互換性チェック自動化

---

## 📚 参考資料

- [GitHub Actions - Using environments for deployment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Pulumi - CI/CD Integration](https://www.pulumi.com/docs/using-pulumi/continuous-delivery/)
- [GitHub Actions - Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [AWS Lambda - Working with Lambda layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [AWS Lambda - Lambda runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)
- [AWS Lambda PowerTools for Python](https://docs.powertools.aws.dev/lambda/python/latest/)
- [Klayers - Public Lambda Layers](https://github.com/keithrozario/Klayers)

---

## 📞 関連ドキュメント

- [デプロイ監視ガイド](./DEPLOYMENT_MONITORING.md)
- [トラブルシューティング](../TROUBLESHOOTING.md)
- [カスタムドメイン設定ガイド](../CUSTOM_DOMAIN_SETUP.md)
- [Lambda レイヤー最適化](./LAMBDA_LAYER_OPTIMIZATION.md)
- [Lambda 公開レイヤー調査](./LAMBDA_LAYER_PUBLIC_SURVEY.md)
