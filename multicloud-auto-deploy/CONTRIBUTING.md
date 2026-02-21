# コントリビューティングガイド

Multi-Cloud Auto Deploy Platform へのコントリビューションをありがとうございます！

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

- GitHub Discussions
- Issues
- メール: support@example.com
