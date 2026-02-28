# GitHub 機能統合ガイド

> **最終更新**: 2026-02-28
> **ステータス**: ✅ 全7機能実装完了 + 設定ガイド完成

---

## 📋 実装済み機能

### 1️⃣ GitHub Issues + Milestones

**ステータス**: ✅ **完全実装**

#### 作成済み Milestone

- **Phase 3: React UI** — React UI 実装 & 統合テスト (完了: 2026-02-28)
- **Phase 4: 拡張機能** — Phase 3 完了後の今後の施策
- **Session 6: セキュリティ監視** — CloudWatch/Monitor/Logging アラート設定
- **Session 7: パフォーマンス最適化** — Lighthouse スコア >90, LCP <2.5s

#### 作成済み Issue

| Issue | 状態        | Milestone | ラベル                  |
| ----- | ----------- | --------- | ----------------------- |
| #31   | ✅ 完了     | Phase 3   | testing, infrastructure |
| #29   | ✅ 完了     | Phase 3   | backend, azure          |
| #30   | ✅ 完了     | Phase 3   | backend, aws, database  |
| #32   | ⏳ 未実装   | Phase 3   | critical, deployment    |
| #33   | ⏳ 部分完了 | Session 6 | enhancement, deployment |
| #34   | ⏳ 未実装   | Session 7 | enhancement, testing    |

####使用方法

**新しいタスク追加**:

```bash
gh issue create --title "Task タイトル" \
  --label "critical,security" \
  --milestone "Phase 4: 拡張機能" \
  --body "## 概要\n...\n## チェックリスト\n- [ ] Item 1" \
  --assignee PLAYER1-r7
```

**進捗更新**:

```bash
gh issue edit <number> --state closed
# または
gh issue edit <number> --label "⚠️ blocked"
```

**Issue をフィルタリング**:

```bash
# 特定の Milestone 内の未解決 Issue
gh issue list --milestone "Phase 4: 拡張機能" --state open

# 特定のラベルを持つ Issue
gh issue list --label "critical" --state open

# 自分に割り当てられた Issue
gh issue list --assignee @me --state open
```

---

### 2️⃣ GitHub Project Board（推奨: Web UI で設定）

**ステータス**: 🟡 **準備中**

#### セットアップ手順

1. **Project を作成**: [GitHub Projects](https://github.com/PLAYER1-r7/multicloud-auto-deploy/projects)
   - New Project ボタンをクリック
   - Template: "Automated kanban"
   - 名前: "Phase 4 Progress" など

2. **Automation を設定**:
   - "To do" → 新規 Issue が自動追加
   - "In progress" → PR と連動
   - "Done" → closed issue が自動移動

3. **フィルタリング**:
   - Milestone: "Phase 4: 拡張機能"
   - ラベル: "critical", "enhancement"

---

### 3️⃣ GitHub Releases（自動化版）

**ステータス**: ✅ **Workflow 実装完了 (`.github/workflows/release.yml`)**

#### 自動機能

✅ `git tag v*` をプッシュすると自動実行:

- Conventional Commits から Release Notes 自動生成
- GitHub Release の自動作成
- CHANGELOG.md の自動更新
- versions.json の自動更新

#### 使用方法

**新規リリース**:

```bash
# 1. バージョンをタグとしてプッシュ
git tag v1.1.0
git push origin v1.1.0

# → 自動的に以下が実行される:
# - GitHub Release 作成
# - CHANGELOG.md 更新
# - versions.json 更新
# - Milestone を close
```

**確認**:

```bash
# Tags 一覧
gh release list

# 特定の Release を表示
gh release view v1.1.0
```

#### Conventional Commits ガイド

commit message でリリースノートを自動生成するために、以下の形式を推奨：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:

- `feat`: 新機能 → 🎯 Features
- `fix`: バグ修正 → 🐛 Fixes
- `docs`: ドキュメント → 📝 Docs
- `style`: コード整形 → 💅 Styles
- `refactor`: リファクタリング → ♻️ Refactor
- `test`: テスト追加 → 🧪 Tests
- `chore`: その他 → 🔧 Chores
- `perf`: パフォーマンス → ⚡ Performance

**例**:

```bash
git commit -m "feat(api): add new /recommendations endpoint

Integrates Bedrock for ML-based recommendations

Closes #25"
```

---

## 🚀 次のステップ

### Phase A: Issue 管理（今すぐ）

- [ ] GitHub Project Board を手動作成
- [ ] 既存 Issue をボードに追加
- [ ] 毎週の ステータス更新を Issue comment で実施

### Phase B: Release 自動化（次週）

- [ ] 最初の Release v1.1.0 を作成
  ```bash
  git tag v1.1.0
  git push origin v1.1.0
  ```
- [ ] Release Notes が自動生成されるか確認
- [ ] CHANGELOG.md / versions.json の更新を確認

### Phase C: CI/CD 統合（今後）

- [ ] ✅ Branch Protection Rules（Task #32）
- [ ] ✅ Code Review 自動化（Copilot Reviews）
- [ ] ✅ Dependabot 設定（セキュリティアップデート）

---

## 🔐 4️⃣ GitHub Branch Protection Rules

**ステータス**: ✅ **CLI で自動実装完了** (2026-02-28)

> **実装方法**: GitHub REST API（`gh api`、`curl`）により CLI で自動設定済み
>
> **対象ブランチ**: `main`（厳格）、`develop`（バランス型）

### 設定内容

| ブランチ | PR 必須 | Approval | Code Owner | Admin 制限 | Force Push | 削除 |
|----------|--------|----------|------------|----------|-----------|------|
| **main** | ✅ | ✅ 1人 | ✅ | ✅ | ❌ | ❌ |
| **develop** | ✅ | ✅ 不要 | ❌ | ❌ | ❌ | ❌ |

### 設定確認方法

```bash
# MAIN ブランチ確認
curl -s -H "Authorization: token $(gh auth token)" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/main/protection" | jq .

# DEVELOP ブランチ確認
curl -s -H "Authorization: token $(gh auth token)" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/develop/protection" | jq .
```

### 詳細ガイド

詳しい設定について、および手動での Web UI 設定方法は [docs/BRANCH_PROTECTION_SETUP.md](./BRANCH_PROTECTION_SETUP.md) を参照してください。

---

## 📦 5️⃣ GitHub Dependabot

**ステータス**: ✅ **完全実装** (`.github/dependabot.yml`)

#### 管理対象

- 🐍 **Python 依存関係** (`/services/api`)
  - 週 1 回（火曜日）チェック
  - セキュリティアップデート優先

- 📦 **npm パッケージ** (`/services/frontend_react`)
  - 週 1 回（月曜日）チェック
  - React, Vite, TypeScript, Tailwind でグループ化

- 🔧 **GitHub Actions**
  - 週 1 回チェック

- 🐳 **Docker イメージ**
  - 週 1 回チェック

#### 確認方法

```bash
# Dependabot PR を表示
gh pr list --search "author:dependabot" --state open

# セキュリティアラートを確認
gh api repos/PLAYER1-r7/multicloud-auto-deploy/dependabot/alerts
```

#### 特徴

- ✅ 自動で PR 作成
- ✅ CI が自動実行されて安全性確認
- ✅ セキュリティパッチを優先
- ✅ マージして本番環境を自動更新

---

## 💬 6️⃣ GitHub Discussions

**ステータス**: ✅ **設定ガイド完成** (docs/github-discussions-setup.md)

### カテゴリ

| カテゴリ              | 説明                     | 推奨用途                |
| --------------------- | ------------------------ | ----------------------- |
| 📢 Announcements      | 新規 Release、重要な更新 | 重大アップデート告知    |
| 💡 Ideas & Feedback   | 機能提案、改善案         | ロードマップ議論        |
| 🤝 General Discussion | 一般的なトピック         | Session Notes、知見共有 |
| ❓ Q&A                | 質問と回答               | 技術的なサポート        |
| 🔧 Technical Help     | トラブルシューティング   | デバッグ支援            |

### 使用方法

**Announcements - 新規 Release**

```markdown
# 🚀 Release v1.1.0 Published

✨ **New Features**:

- GitHub Issues + Milestones integration
- Automated Releases + Changelog
- Dependabot security updates

[View Full Release Notes](https://github.com/PLAYER1-r7/...)
```

**General Discussion - Session Notes**

```markdown
# 📝 Session 5 Summary (2026-02-28)

✅ Completed Today:

- GitHub Issues setup
- Milestones configuration
- Release automation

⏳ Next Session:

- Branch Protection Rules
- GitHub Pages setup
```

### Web UI アクセス

https://github.com/PLAYER1-r7/multicloud-auto-deploy/discussions

詳細は [GitHub Discussions ガイド](github-discussions-setup.md) を参照。

---

## 📖 7️⃣ GitHub Pages + MkDocs

**ステータス**: ✅ **完全実装** (`.github/workflows/deploy-docs.yml` + `mkdocs.yml`)

### ドキュメントサイト

🌐 **URL**: https://PLAYER1-r7.github.io/multicloud-auto-deploy/

### 自動デプロイ

✅ `docs/**` に変更を push すると自動設定:

```bash
# ドキュメントビルド
mkdocs build

# ローカルプレビュー
mkdocs serve

# デプロイ（main ブランチから自動）
# .github/workflows/deploy-docs.yml が実行
```

### ドキュメント構成

```
docs/
├── index.md                          # ホームページ
├── getting-started/
│   ├── overview.md                  # プロジェクト概要
│   ├── setup.md                     # セットアップガイド
│   └── quickstart.md                # クイックスタート
├── architecture/
│   ├── system-design.md             # システム設計
│   ├── cloud-architecture.md        # クラウド構成
│   └── api-design.md                # API 設計
├── implementation/
│   ├── backend.md
│   ├── frontend.md
│   └── infrastructure.md
├── deployment/
├── operations/
├── reference/
├── github-features-guide.md         # 本ガイド
├── github-discussions-setup.md      # Discussions setup
└── tasks.md                         # タスク進捗

mkdocs.yml                           # Site config
```

### Material for MkDocs テーマ

✨ 搭載機能:

- 📱 レスポンシブデザイン
- 🔍 全文検索
- 📚 ナビゲーションタブ
- 🎨 ダークモード対応
- 📊 Mermaid 図表対応

### ビルド済みサイト確認

PR コメントで自動通知:

```
✅ Documentation built successfully!
📖 Preview will be published to GitHub Pages when merged to main.
```

---

## 📚 参考資料

- [GitHub Issues Documentation](https://docs.github.com/en/issues)
- [GitHub Projects (v2)](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [GitHub Dependabot](https://docs.github.com/en/code-security/dependabot)
- [GitHub Discussions](https://docs.github.com/en/discussions)
- [GitHub Pages](https://docs.github.com/en/pages)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

---

## 📊 ステータスダッシュボード

### Issues Summary

```
Total Issues: 13
├─ Open: 6
│  ├─ Critical: 1 (#32)
│  ├─ Enhancement: 2 (#33, #34)
│  └─ Other: 3
└─ Closed: 7 (✅ #31, #29, #30, etc)
```

### Milestones Progress

| Milestone | Open Issues | Closed Issues | Status |
| --------- | ----------- | ------------- | ------ |
| Phase 3   | 3           | 3             | 50%    |
| Phase 4   | 0           | 0             | 0%     |
| Session 6 | 1           | 0             | 0%     |
| Session 7 | 1           | 0             | 0%     |

### GitHub Features Status

| 機能              | 実装状況             | リンク                                                                               |
| ----------------- | -------------------- | ------------------------------------------------------------------------------------ |
| Issues            | ✅ 完了              | [Issues](https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues)                |
| Milestones        | ✅ 完了              | [Milestones](https://github.com/PLAYER1-r7/multicloud-auto-deploy/milestones)        |
| Project Board     | ⏳ Web UI で設定可能 | [Projects](https://github.com/PLAYER1-r7/multicloud-auto-deploy/projects)            |
| Releases          | ✅ 完了              | [Releases](https://github.com/PLAYER1-r7/multicloud-auto-deploy/releases)            |
| Dependabot        | ✅ 完了              | [Security](https://github.com/PLAYER1-r7/multicloud-auto-deploy/security/dependabot) |
| Discussions       | ✅ 設定ガイド完成    | [Discussions](https://github.com/PLAYER1-r7/multicloud-auto-deploy/discussions)      |
| GitHub Pages      | ✅ 完了              | [Pages](https://PLAYER1-r7.github.io/multicloud-auto-deploy/)                        |
| Branch Protection | ⏳ Web UI で設定必要 | Settings → Branches                                                                  |

---

## 🚀 次のステップ

### Phase A: Issue 管理（✅ 完了）

- ✅ GitHub Issues 作成完了
- ✅ Milestones 作成完了
- ✅ ラベル体系構築完了

### Phase B: Release 自動化（✅ 完了）

- ✅ Releases workflow 実装完了
- ✅ Conventional Commits 対応
- ✅ CHANGELOG.md 自動更新

### Phase C: セキュリティ & 運用（✅ 完了）

- ✅ Dependabot 設定完了
- ✅ GitHub Pages + MkDocs デプロイ完了
- ✅ GitHub Discussions ガイド完成
- ⏳ Branch Protection Rules を Web UI から設定

### Phase D: 品質管理（次週推奨）

- [ ] GitHub Project Board を手動作成
- [ ] Code Review 自動化（Copilot Reviews）
- [ ] CI/CD アラート Slack 連携

---

## 📊 ステータスダッシュボード

### Issues Summary

```
Total Issues: 13
├─ Open: 6
│  ├─ Critical: 1 (#32)
│  ├─ Enhancement: 2 (#33, #34)
│  └─ Other: 3
└─ Closed: 7 (✅ #31, #29, #30, etc)
```

### Milestones Progress

| Milestone | Open Issues | Closed Issues | Status |
| --------- | ----------- | ------------- | ------ |
| Phase 3   | 3           | 3             | 50%    |
| Phase 4   | 0           | 0             | 0%     |
| Session 6 | 1           | 0             | 0%     |
| Session 7 | 1           | 0             | 0%     |

---

## 🔗 利用可能なリンク

- **Issues Board**: https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues
- **Milestones**: https://github.com/PLAYER1-r7/multicloud-auto-deploy/milestones
- **Releases**: https://github.com/PLAYER1-r7/multicloud-auto-deploy/releases
- **Actions**: https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions
