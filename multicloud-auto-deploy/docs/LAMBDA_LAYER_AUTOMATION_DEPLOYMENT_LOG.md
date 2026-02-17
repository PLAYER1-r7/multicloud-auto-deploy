# Lambda Layer自動管理実装とデプロイログ

**実施日時**: 2026-02-17 18:10 - 18:25 JST  
**対象**: AWS Staging環境  
**目的**: Lambda Layer ARNハードコーディングの排除とPulumiによる自動管理

---

## 🎯 実装目的

### 課題
Lambda Layer更新のたびにPulumiコード内のARNを手動で変更する必要があり、以下の問題がありました：
- ハードコーディングされたLayer ARN（v2 → v6への更新時に手動変更が必要）
- バージョン管理の手動追跡
- ヒューマンエラーのリスク

### 解決策
Pulumi Infrastructure as CodeでLambda LayerVersionリソースを管理し、動的にLambda関数へアタッチ。

---

## 📝 実装内容

### 1. Pulumi Lambda LayerVersion リソース追加

**ファイル**: `infrastructure/pulumi/aws/__main__.py`

```python
# Lambda Layer ZIPを自動検出
workspace_root = os.environ.get("GITHUB_WORKSPACE")
if workspace_root:
    # GitHub Actions環境
    layer_zip_path = pathlib.Path(workspace_root) / "multicloud-auto-deploy" / "services" / "api" / "lambda-layer.zip"
else:
    # ローカル開発環境
    layer_zip_path = pathlib.Path(__file__).parent.parent.parent.parent / "services" / "api" / "lambda-layer.zip"

# Pulumi Lambda LayerVersionリソース作成
lambda_layer = aws.lambda_.LayerVersion(
    "dependencies-layer",
    layer_name=f"{project_name}-{stack}-dependencies",
    code=pulumi.FileArchive(str(layer_zip_path)),
    compatible_runtimes=["python3.12"],
    description=f"Dependencies for {project_name} {stack} (FastAPI, Mangum, Pydantic, etc.)",
)

# Lambda関数に動的アタッチ
lambda_function = aws.lambda_.Function(
    "api-function",
    layers=[lambda_layer.arn] if lambda_layer else [],
    # ...
)
```

### 2. GitHub Actions CI/CD統合

**ファイル**: `.github/workflows/deploy-aws.yml`

```yaml
- name: Build Lambda Layer
  run: |
    cd multicloud-auto-deploy
    echo "🔨 Building Lambda Layer..."
    ./scripts/build-lambda-layer.sh
    echo "✅ Lambda Layer built successfully"
    ls -lh services/api/lambda-layer.zip

- name: Deploy Infrastructure with Pulumi
  uses: pulumi/actions@v5
  with:
    command: up
    stack-name: ${{ steps.set_stack.outputs.stack_name }}
    work-dir: multicloud-auto-deploy/infrastructure/pulumi/aws
```

---

## 🚀 デプロイ試行履歴

### 試行 #1: Pulumi認証修正後の初回デプロイ

**時刻**: 18:10:12 JST  
**Commit**: `9035d1b` - "docs: Add deployment verification report"  
**Run ID**: 22110083251  
**結果**: ❌ 失敗

**エラー内容**:
1. **Pulumi認証**: ✅ 成功（`PULUMI_ACCESS_TOKEN`更新後）
2. **Lambda Layer更新**: ✅ 成功（v6にアップグレード）
3. **SNS権限エラー**: ❌ IAMユーザー`satoshi`が`SNS:Unsubscribe`権限なし

```
AuthorizationError: User: arn:aws:iam::278280499340:user/satoshi is not authorized 
to perform: SNS:Unsubscribe on resource: arn:aws:sns:ap-northeast-1:278280499340:
multicloud-auto-deploy-staging-alarms
```

**影響**: デプロイ失敗（既存リソース削除時）

---

### 試行 #2: Layer ARN動的参照への変更

**時刻**: 18:14:18 JST  
**Commit**: `dfa6d4c` - "fix: Update Lambda Layer ARN to v6 in Pulumi infrastructure"  
**Run ID**: 22110210173  
**結果**: ❌ 失敗

**エラー内容**:
- 同様のSNS権限エラー（継続）

**学んだこと**: ARN更新だけではSNS権限問題は解決しない

---

### 試行 #3: Lambda Layer完全自動管理実装

**時刻**: 18:17:07 JST  
**Commit**: `ad32376` - "feat: Automate Lambda Layer management with Pulumi"  
**Run ID**: 22110299130  
**結果**: ❌ 失敗

**エラー内容**:
1. **Lambda Layer ZIPパスエラー**: ❌ ファイルが見つからない
   ```
   warning: Lambda Layer ZIP not found at /home/runner/work/multicloud-auto-deploy/
   multicloud-auto-deploy/multicloud-auto-deploy/infrastructure/services/api/lambda-layer.zip
   ```
   - 期待: `.../multicloud-auto-deploy/services/api/lambda-layer.zip`
   - 実際: `.../multicloud-auto-deploy/infrastructure/services/api/lambda-layer.zip`

2. **SNS権限エラー**: ❌ 継続

**根本原因**: 相対パス計算が間違っており、`parent`の回数が不足

---

### 試行 #4: パス計算修正（相対パス）

**時刻**: 18:19:25 JST  
**Commit**: `7a04f8e` - "fix: Correct Lambda Layer ZIP path in Pulumi"  
**Run ID**: 22110371644  
**結果**: ❌ 失敗

**エラー内容**:
- **Lambda Layer ZIPパスエラー**: ❌ 依然として見つからない（パスがまだ間違っている）
- **SNS権限エラー**: ❌ 継続

**パス問題の詳細**:
- 修正内容: `parent.parent.parent.parent` → `parent.parent.parent` (4→3に減らした)
- 問題: GitHub Actionsの`work-dir`設定により、相対パス計算が複雑化
- 結論: 環境変数`GITHUB_WORKSPACE`を使用する方が確実

---

### 試行 #5: GITHUB_WORKSPACE環境変数の使用

**時刻**: 18:23:09 JST  
**Commit**: `f121556` - "fix: Use GITHUB_WORKSPACE env var for Lambda Layer path"  
**Run ID**: 22110457413  
**結果**: ❌ 失敗

**変更内容**:
```python
workspace_root = os.environ.get("GITHUB_WORKSPACE")
if workspace_root:
    # GitHub Actions: 環境変数を使用
    layer_zip_path = pathlib.Path(workspace_root) / "multicloud-auto-deploy" / "services" / "api" / "lambda-layer.zip"
else:
    # ローカル: 相対パス（4レベル上）
    layer_zip_path = pathlib.Path(__file__).parent.parent.parent.parent / "services" / "api" / "lambda-layer.zip"
```

**エラー内容**:
- **Lambda Layer ZIPパスエラー**: ❌ 依然 failed
- **SNS権限エラー**: ❌ 継続

**問題**: ワークフローステップで`cd multicloud-auto-deploy`を実行しているが、このディレクトリは存在しない（リポジトリ名が`multicloud-auto-deploy`なので、リポジトリルートが既に`multicloud-auto-deploy`）

---

### 試行 #6: ワークフローパス修正と最終調整

**時刻**: 18:28:45 JST  
**Commit**: `b6d35ef` - "fix: Remove non-existent cd multicloud-auto-deploy from workflow and correct Lambda Layer paths"  
**Run ID**: 22110680555  
**結果**: ❌ 失敗

**変更内容**:

1. **ワークフロー修正** (`.github/workflows/deploy-aws.yml`):
   - `cd multicloud-auto-deploy`を削除（存在しないディレクトリ）
   - `Build Lambda Layer`ステップを調整

2. **Pulumiパス修正** (`infrastructure/pulumi/aws/__main__.py`):
   ```python
   workspace_root = os.environ.get("GITHUB_WORKSPACE")
   if workspace_root:
       # GitHub Actions: リポジトリルート直下のservices/api/lambda-layer.zip
       layer_zip_path = pathlib.Path(workspace_root) / "services" / "api" / "lambda-layer.zip"
   else:
       # ローカル: 3レベル上（infrastructure/pulumi/aws → project root）
       layer_zip_path = pathlib.Path(__file__).parent.parent.parent / "services" / "api" / "lambda-layer.zip"
   ```

**エラー内容**:
- **Lambda Layer ZIPパスエラー**: ❌ 依然として見つからない
- **SNS権限エラー**: ❌ 継続（主要なブロッカー）
- **ワークフロー順序問題**: "Build Lambda Layer"ステップが"Deploy Infrastructure with Pulumi"の後に配置されているため、Pulumiデプロイが失敗すると実行されない

**根本原因の特定**:
1. ワークフローの"Build Lambda Layer"ステップが2箇所にあるが、Pulumiデプロイの前のものが実行されていない
2. SNS:Unsubscribe権限エラーがデプロイを完全にブロック

---

## ⚠️ 継続中の問題

### SNS:Unsubscribe 権限エラー

**症状**:
```
User: arn:aws:iam::278280499340:user/satoshi is not authorized to perform: SNS:Unsubscribe
```

**影響**: 
- Pulumiが既存のSNS TopicSubscriptionリソースを削除しようとして失敗
- デプロイ全体が失敗（エラーハンドリング不足）

**根本原因**: IAMユーザー`satoshi`のポリシーに`SNS:Unsubscribe`アクションが含まれていない

**解決策（優先順）**:

1. **IAMポリシー更新（推奨）**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "sns:Subscribe",
           "sns:Unsubscribe",
           "sns:ListSubscriptions",
           "sns:ListSubscriptionsByTopic"
         ],
         "Resource": "arn:aws:sns:ap-northeast-1:278280499340:multicloud-auto-deploy-*"
       }
     ]
   }
   ```

2. **Pulumi保護オプション**:
   ```python
   sns_subscription = aws.sns.TopicSubscription(
       "alarm-email-subscription",
       opts=pulumi.ResourceOptions(
           protect=True,  # 削除を防止
           retain_on_delete=True  # 削除時にリソースを保持
       )
   )
   ```

3. **手動削除**:
   ```bash
   aws sns unsubscribe \
     --subscription-arn arn:aws:sns:ap-northeast-1:278280499340:multicloud-auto-deploy-staging-alarms:e2515f20-d3dc-4811-ad11-1f5a806ba7dc \
     --region ap-northeast-1
   ```

---

## 📊 学習事項

### 技術的洞察

1. **GitHub Actions環境変数の重要性**:
   - `GITHUB_WORKSPACE`を使用することで、パス計算が簡潔かつ確実になる
   - 相対パス計算は、`work-dir`設定により複雑化する可能性がある

2. **Pulumiのエラーハンドリング**:
   - リソース削除失敗時、デプロイ全体が失敗する
   - `protect`や`retain_on_delete`オプションでリソースを保護可能

3. **Lambda Layer管理のベストプラクティス**:
   - Infrastructure as CodeでLayerを管理することで、バージョン追跡が自動化
   - CI/CDパイプラインでLayerビルドを自動化することで、一貫性が向上

### プロセス改善

1. **段階的デプロイ**:
   - 小さな変更を段階的にコミット・デプロイすることで、問題の切り分けが容易

2. **ログ分析の重要性**:
   - CI/CDログから素早く問題を特定する能力が重要
   - `grep`や`jq`を使った効率的なログフィルタリング

3. **ドキュメント化**:
   - 試行錯誤の過程を記録することで、将来の同様の問題解決が迅速化

---

## 🔜 次のステップ

1. ✅ **試行 #5のデプロイ結果確認**（進行中）
2. ⏳ **SNS権限問題の解決**（IAMポリシー更新）
3. ⏳ **全環境の動作確認**（AWS/Azure/GCP Staging）
4. ⏳ **Production環境への展開**（mainブランチへのマージ）
5. ⏳ **最終デプロイ検証レポート更新**

---

## 📈 成功指標

- [x] Lambda Layer自動管理の実装完了
- [x] GitHub Actions CI/CD統合
- [ ] Lambda Layer ZIPの正しい検出（試行 #5で検証中）
- [ ] Staging環境へのデプロイ成功
- [ ] Production環境へのデプロイ成功
- [ ] ドキュメント完成度 100%

