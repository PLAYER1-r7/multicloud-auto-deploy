# デプロイ監視ガイド

> **AIエージェント向けメモ**: デプロイ状況の監視コマンドと確認手順。


GitHub Actionsのデプロイワークフローを監視する方法を説明します。

## 📋 目次

- [ブラウザで監視](#ブラウザで監視)
- [GitHub CLIで監視](#github-cliで監視)
- [curlとGitHub APIで監視](#curlとgithub-apiで監視)
- [リアルタイム監視スクリプト](#リアルタイム監視スクリプト)
- [トラブルシューティング](#トラブルシューティング)
- [デプロイ失敗調査](#デプロイ失敗調査)

> 💡 **関連ドキュメント**: デプロイ失敗の詳細な調査方法は [デプロイ失敗調査レポート](./DEPLOYMENT_FAILURE_INVESTIGATION.md) を参照してください。

---

## 🌐 ブラウザで監視

最も簡単な方法です。

### 手順

1. **GitHub Actionsページを開く**

```bash
# ブラウザで開く
$BROWSER https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions
```

2. **ワークフローを選択**
   - 左サイドバーから監視したいワークフローを選択
     - `Deploy to AWS`
     - `Deploy to Azure`
     - `Deploy to GCP`

3. **実行中のジョブをクリック**
   - リアルタイムでログが表示されます
   - 各ステップの実行時間が確認できます

---

## 💻 GitHub CLIで監視

コマンドラインから詳細情報を取得できます。

### 前提条件

GitHub CLIの認証が必要です：

```bash
# 認証状態を確認
gh auth status

# 未認証の場合はログイン
gh auth login
```

### 基本コマンド

#### 1. ワークフロー実行一覧を表示

```bash
# mainブランチの最新5件
gh run list --branch main --limit 5

# developブランチの最新5件
gh run list --branch develop --limit 5

# 特定のワークフローのみ表示
gh run list --workflow="Deploy to AWS" --limit 5
```

**出力例**:

```
STATUS  TITLE                    WORKFLOW         BRANCH  EVENT  ID          ELAPSED  AGE
✓       Merge develop into main  Deploy to AWS    main    push   22107983145  2m 45s   10m
✓       Fix PUT endpoint         Deploy to AWS    develop push   22107968393  2m 30s   15m
```

#### 2. 特定のワークフロー実行を監視

```bash
# 最新のワークフロー実行を監視（リアルタイム更新）
gh run watch

# 特定のRun IDを監視
gh run watch 22107983145

# ブランチを指定して最新を監視
gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId' | xargs gh run watch
```

#### 3. ワークフロー実行の詳細を表示

```bash
# 最新の実行情報
gh run view

# 特定のRun IDの詳細
gh run view 22107983145

# ログを表示
gh run view 22107983145 --log
```

#### 4. 失敗したワークフローのみ表示

```bash
gh run list --status failure --limit 10
```

#### 5. ワークフローを手動実行

```bash
# 特定のワークフローを実行
gh workflow run "Deploy to AWS"

# パラメータを指定して実行
gh workflow run "Deploy to AWS" -f environment=production
```

---

## 🔧 curlとGitHub APIで監視

GitHub CLIなしでも監視できます（公開リポジトリの場合）。

### リポジトリ情報

```bash
REPO_OWNER="PLAYER1-r7"
REPO_NAME="multicloud-auto-deploy"
```

### 1. 最新のワークフロー実行を取得

```bash
curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?branch=main&per_page=5" \
  | jq -r '.workflow_runs[] | "\(.id) | \(.status) | \(.conclusion // "running") | \(.name) | \(.created_at)"'
```

**出力例**:

```
22107983147 | completed | failure | Deploy Landing Page to AWS | 2026-02-17T17:06:16Z
22107983158 | completed | success | Deploy Landing Page to Azure | 2026-02-17T17:06:16Z
22107983145 | completed | failure | Deploy to AWS | 2026-02-17T17:06:16Z
```

### 2. 特定のワークフローの最新実行を取得

```bash
curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?branch=main&per_page=10" \
  | jq -r '.workflow_runs[] | select(.name == "Deploy to AWS") | "\(.id) | \(.status) | \(.conclusion // "running") | \(.created_at) | \(.html_url)"' \
  | head -1
```

### 3. ワークフロー実行の詳細情報

```bash
RUN_ID="22107983145"

curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${RUN_ID}" \
  | jq -r '"Run ID: \(.id)\nStatus: \(.status)\nConclusion: \(.conclusion // "running")\nWorkflow: \(.name)\nBranch: \(.head_branch)\nCommit: \(.head_sha[0:7])\nCreated: \(.created_at)\nURL: \(.html_url)"'
```

**出力例**:

```
Run ID: 22107983145
Status: completed
Conclusion: failure
Workflow: Deploy to AWS
Branch: main
Commit: 3ba0bf5
Created: 2026-02-17T17:06:16Z
URL: https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions/runs/22107983145
```

### 4. ワークフロージョブの取得

```bash
RUN_ID="22107983145"

curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${RUN_ID}/jobs" \
  | jq -r '.jobs[] | "Job: \(.name)\nStatus: \(.status)\nConclusion: \(.conclusion // "running")\nStarted: \(.started_at)\n---"'
```

### 5. 実行中のワークフローのみ取得

```bash
curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?status=in_progress&per_page=10" \
  | jq -r '.workflow_runs[] | "\(.name) | \(.status) | Branch: \(.head_branch)"'
```

---

## 🔄 リアルタイム監視スクリプト

### 自動リロードスクリプト

`scripts/watch-deployment.sh`:

```bash
#!/bin/bash
set -euo pipefail

REPO_OWNER="PLAYER1-r7"
REPO_NAME="multicloud-auto-deploy"
BRANCH="${1:-main}"
INTERVAL="${2:-10}"

echo "🔍 Watching deployments on branch: $BRANCH"
echo "🔄 Refresh interval: ${INTERVAL}s"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "═══════════════════════════════════════════════════════"
    echo "   Multi-Cloud Deployment Monitor"
    echo "   Branch: $BRANCH | $(date '+%Y-%m-%d %H:%M:%S')"
    echo "═══════════════════════════════════════════════════════"
    echo ""

    # 最新5件のワークフロー実行を取得
    curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?branch=${BRANCH}&per_page=5" \
        | jq -r '.workflow_runs[] | "[\(.status | if . == "completed" then "✓" elif . == "in_progress" then "⏳" else "⏸" end)] \(.name)\n   Status: \(.status) | Result: \(.conclusion // "running")\n   Commit: \(.head_sha[0:7]) | \(.created_at)\n   URL: \(.html_url)\n"'

    echo "═══════════════════════════════════════════════════════"
    sleep $INTERVAL
done
```

### 使用方法

```bash
# mainブランチを監視
./scripts/watch-deployment.sh main

# developブランチを監視（5秒間隔）
./scripts/watch-deployment.sh develop 5

# 実行可能にする
chmod +x scripts/watch-deployment.sh
```

---

## 📊 ワンライナー集

### mainブランチの最新デプロイ状況

```bash
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?branch=main&per_page=3" \
  | jq -r '.workflow_runs[] | "[\(.conclusion // .status)] \(.name) - \(.created_at)"'
```

### 失敗したワークフローのURL取得

```bash
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?status=failure&per_page=5" \
  | jq -r '.workflow_runs[] | "\(.name): \(.html_url)"'
```

### 実行中のワークフローを確認

```bash
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?status=in_progress" \
  | jq -r '.workflow_runs[] | "\(.name) on \(.head_branch) - Started: \(.created_at)"'
```

### 最新のAWSデプロイ結果

```bash
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?branch=main&per_page=20" \
  | jq -r '.workflow_runs[] | select(.name == "Deploy to AWS") | "[\(.conclusion // .status)] Commit: \(.head_sha[0:7]) - \(.created_at)"' \
  | head -1
```

---

## 🔍 トラブルシューティング

### GitHub API Rate Limit

**問題**: API呼び出しが制限される

```bash
# Rate limit状況を確認
curl -s "https://api.github.com/rate_limit" | jq '.rate'
```

**解決策**:

- GitHub Personal Access Tokenを使用して認証

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs"
```

### jqがインストールされていない

```bash
# Debian/Ubuntu
sudo apt-get install jq

# macOS
brew install jq

# または、jq なしでパース
curl -s "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/actions/runs?per_page=3" \
  | python3 -m json.tool
```

### GitHub CLIの認証エラー

```bash
# 再認証
gh auth logout
gh auth login

# トークンを使用
gh auth login --with-token < token.txt
```

---

## � デプロイ失敗調査

デプロイが失敗した場合の調査手順については、詳細な調査レポートを参照してください：

📄 **[デプロイ失敗調査レポート](./DEPLOYMENT_FAILURE_INVESTIGATION.md)**

主な内容：

- 失敗状況の確認手順
- 失敗ステップの特定方法
- 根本原因の分析
- 解決策の提案
- 修正後の検証手順

---

## �📚 参考リンク

- [GitHub Actions API Documentation](https://docs.github.com/en/rest/actions)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## 🎯 次のステップ

デプロイが完了したら：

1. **動作確認**: [ENDPOINTS.md](ENDPOINTS.md) のエンドポイントをテスト
2. **ログ確認**: 失敗した場合はログを確認
3. **再デプロイ**: 必要に応じて修正してプッシュ

---

**最終更新**: 2026-02-17
