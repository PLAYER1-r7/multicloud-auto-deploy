# コントリビューティングガイド

Multi-Cloud Auto Deploy Platform へのコントリビューションをありがとうございます！

> **🤖 AI エージェント向けガイド**: 本リポジトリで作業を行う前に、以下のドキュメントを**必ず**読んでください：
>
> 1. **最初に必ず読むこと**（重要ルール）: [docs/AI_AGENT_00_CRITICAL_RULES_JA.md](docs/AI_AGENT_00_CRITICAL_RULES_JA.md)
> 2. **このドキュメント**: 開発環境セットアップ、GitHub ワークフロー、GitHub Features の使い方
> 3. **GitHub Features の使用方法**: [docs/GITHUB_FEATURES_GUIDE.md](docs/GITHUB_FEATURES_GUIDE.md)
> 4. **プロジェクト全体概要**: [docs/AI_AGENT_01_CONTEXT_JA.md](docs/AI_AGENT_01_CONTEXT_JA.md)
>
> **GitHub Features を積極活用すること**（ルール16参照）：
> - 🐛 バグ発見 → `gh issue create` で Issue を作成
> - ✨ 機能改善 → `gh issue create` で提案を Issue に記録
> - 📝 出力結果 → `gh issue comment` で Issue に進捗コメント
> - 🔀 コード変更 → Pull Request 経由（`main` への直接 push は禁止）
> - ⚙️ 必要なツール → 自由にインストール OK（ルール17参照）

---

## 開発環境のセットアップ

> **推奨環境**: VS Code Dev Container（`.devcontainer/`）を使用してください。  
> ホストマシン: **ARM (Apple Silicon M-series Mac)** 対応済み。

1. **リポジトリをフォーク**

2. **クローン**

```bash
git clone https://github.com/YOUR_USERNAME/multicloud-auto-deploy.git
cd multicloud-auto-deploy
```

3. **Dev Container で開く**（推奨）
   - VS Code で `Reopen in Container` を実行
   - または GitHub Codespaces で開く
   - 初回は `.devcontainer/setup.sh` が自動で実行されます

4. **ローカルで実行**

```bash
# Docker Compose で全サービス起動
docker compose up -d

# 確認
curl http://localhost:8000/health    # API
open http://localhost:3000/sns/      # SNS フロントエンド
```

> ⚠️ **ARM (Apple Silicon) 注意事項**
>
> - ローカル docker compose はネイティブ ARM で動作します
> - Lambda 向けビルドは `--platform linux/amd64` が必要（CI/CD で自動処理）
> - GCP Cloud Run ビルドは Cloud Build で行うため ARM 問題なし

## ブランチ戦略

- `main`: 本番環境
- `develop`: 開発環境
- `feature/*`: 新機能
- `bugfix/*`: バグ修正
- `hotfix/*`: 緊急修正

## コミットメッセージ

Conventional Commitsに従ってください：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### タイプ

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: コードスタイル
- `refactor`: リファクタリング
- `test`: テスト
- `chore`: その他

### 例

```
feat(frontend): Add message filtering

- Add filter by date
- Add filter by cloud provider
- Update UI components

Closes #123
```

## プルリクエスト

1. **最新のmainから作業ブランチを作成**

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature
```

2. **変更を加える**

3. **テストを実行**

```bash
# Frontend
cd services/frontend
npm test

# Backend
cd services/backend
pytest
```

4. **コミットしてプッシュ**

```bash
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature
```

5. **PRを作成**
   - わかりやすいタイトルと説明
   - 関連するイシューを参照
   - スクリーンショット（UI変更の場合）

```bash
# GitHub CLI で PR を作成（推奨）
gh pr create --base develop --head feature/your-feature \
  --title "feat: your feature description" \
  --body "詳細説明

Closes #123
Reviewers: @PLAYER1-r7"
```

6. **Branch Protection Rules に従う**
   - `develop` → PR 必須、CI テスト自動実行
   - `main` → PR 必須、1 approval 必須、Code Owner review 必須
   - 詳細: [docs/BRANCH_PROTECTION_SETUP.md](docs/BRANCH_PROTECTION_SETUP.md)

7. **GitHub Issues と連携**
   - PR 説明に `Closes #<ISSUE_NUMBER>` を記載すると、マージ時に自動クローズ
   - `gh pr comment` で PR にコメントを追加し、進捗を共有
   - レビューコメントには `gh pr review` で対応

```bash
# Issue へのコメント（進捗更新）
gh issue comment 123 --body "WIP: API エンドポイント実装中"

# PR への approval
gh pr review <PR_NUMBER> --approve

# PR をマージ
gh pr merge <PR_NUMBER> --squash --delete-branch
```

---

## コーディング規約

### Python (Backend)

- **Formatter**: Black
- **Linter**: Flake8
- **Type Hints**: 使用必須

```bash
black src/
flake8 src/
mypy src/
```

### TypeScript (Frontend)

- **Style Guide**: Airbnb
- **Linter**: ESLint
- **Formatter**: Prettier

```bash
npm run lint
npm run format
```

## テスト

### Frontend

```bash
cd services/frontend
npm test              # Unit tests
npm run test:e2e      # E2E tests
npm run test:coverage # Coverage
```

### Backend

```bash
cd services/backend
pytest                    # All tests
pytest tests/test_main.py # Specific file
pytest --cov=src          # With coverage
```

## ドキュメント

- コードにコメントを追加
- READMEを更新
- 新機能にはドキュメントページを追加

## レビュープロセス

1. 自動チェック（CI）が通過
2. コードレビュー
3. 承認後にマージ

## イシューの報告

バグを見つけた場合：

1. 既存のイシューを確認
2. 新しいイシューを作成
3. 以下を含める：
   - 明確な説明
   - 再現手順
   - 期待される動作
   - スクリーンショット/ログ
   - 環境情報

## ライセンス

コントリビューションはMITライセンスの下で公開されます。

## 質問？

- GitHub Discussions: https://github.com/PLAYER1-r7/multicloud-auto-deploy/discussions
- Issues: https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues
- メール: support@example.com

---

## 📚 GitHub Features リソース

このプロジェクトでは、GitHub の機能を積極的に活用しています。以下のドキュメントで詳細を確認してください：

| 機能 | 説明 | 詳細ドキュメント |
|------|------|-----------------|
| **GitHub Issues** | タスク管理、バグ報告、機能提案 | [docs/GITHUB_FEATURES_GUIDE.md](docs/GITHUB_FEATURES_GUIDE.md) |
| **Pull Requests** | コード変更の審査・マージ | [docs/BRANCH_PROTECTION_SETUP.md](docs/BRANCH_PROTECTION_SETUP.md) |
| **Branch Protection** | `main`/`develop` ブランチの保護ルール設定 | [docs/BRANCH_PROTECTION_SETUP.md](docs/BRANCH_PROTECTION_SETUP.md) |
| **GitHub Releases** | Version タグ付けとリリースノート自動生成 | [docs/GITHUB_FEATURES_GUIDE.md](docs/GITHUB_FEATURES_GUIDE.md) |
| **Dependabot** | 依存関係の自動更新と脆弱性検査 | [docs/GITHUB_FEATURES_GUIDE.md](docs/GITHUB_FEATURES_GUIDE.md) |
| **GitHub Discussions** | Q&A、知見共有、アナウンス | [docs/github-discussions-setup.md](docs/github-discussions-setup.md) |
| **GitHub Pages** | ドキュメント自動公開 | [docs/index.md](docs/index.md) |

### よく使うコマンド

```bash
# Issue の作成
gh issue create --title "タイトル" --body "説明" --label bug

# Issue へのコメント
gh issue comment <ISSUE_NUMBER> --body "コメント"

# PR の作成
gh pr create --base develop --title "タイトル"

# PR の確認・マージ
gh pr view <PR_NUMBER>
gh pr merge <PR_NUMBER> --squash

# Discussions の確認（Web UI）
open https://github.com/PLAYER1-r7/multicloud-auto-deploy/discussions
```

### 重要なルール

- ✅ **GitHub Features を活用する**: Issues, PR, Discussions で全て記録を残す
- ✅ **議論は GitHub で**: コード・設計・プロセスについての議論は Issues/Discussions/PR comments で可視化
- ✅ **必要なツールはインストール OK**: dev container で Python、Node.js、サードパーティ CLI など自由にインストール可能

詳細は [docs/AI_AGENT_00_CRITICAL_RULES_JA.md](docs/AI_AGENT_00_CRITICAL_RULES_JA.md)（ルール16・17）を参照。
