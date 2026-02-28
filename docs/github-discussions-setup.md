# GitHub Discussions 設定ガイド

## 概要

GitHub Discussions は、プロジェクト内での非同期コミュニケーション、Q&A、アイディア共有に適しています。

## 有効化手順（Web UI）

### 1. Repository Settings から有効化

1. GitHub リポジトリを開く
2. **Settings** → **Features** セクション
3. **Discussions** のチェックボックスを ✅ 有効化
4. **Save** をクリック

### 2. Discussions のカテゴリを設定

**Settings** → **Discussions** → **Categories** を開いて以下を設定：

#### 📢 Announcements（発表）
```
Title: Announcements
Icon: 📢
Description: New releases, important updates, breaking changes
Allow answers: No (Q&A 無効)
Allow polls: No
```

#### 💡 Ideas & Feedback（意見・提案）
```
Title: Ideas & Feedback
Icon: 💡
Description: Feature requests, improvement suggestions, feedback
Allow answers: Yes
Allow polls: Yes
```

#### 🤝 General Discussion（一般情報交換）
```
Title: General Discussion
Icon: 🤝
Description: General topics, session notes, knowledge sharing
Allow answers: Yes
Allow polls: Yes
```

#### ❓ Q&A（質問）
```
Title: Q&A
Icon: ❓
Description: Questions and answers about the project
Allow answers: Yes (Q&A 有効)
Allow polls: No
```

#### 🔧 Technical Help（技術サポート）
```
Title: Technical Help
Icon: 🔧
Description: Troubleshooting, debugging, technical issues
Allow answers: Yes
Allow polls: No
```

## 推奨された使用方法

### 📢 Announcements

新規 Release やセキュリティアップデート、計画変更を発表：

```markdown
## 🚀 Release v1.1.0 Published

- ✨ New features:
  - GitHub Issues integration
  - Automated Releases
  - Dependabot security updates
- 🐛 Bug fixes: 3 issues
- 📝 Documentation: Updated

See [Release Notes](https://github.com/PLAYER1-r7/multicloud-auto-deploy/releases/tag/v1.1.0)
```

### 💡 Ideas & Feedback

新機能提案や改善案の議論：

```markdown
## Performance optimization for React SPA

Current Lighthouse score: 85  
Target: 95+

Proposed improvements:
- Code splitting
- Image optimization
- Lazy loading
```

### 🤝 General Discussion

Session 完了後のサマリーや知見共有：

```markdown
## Session 5 Summary (2026-02-28)

✅ Completed:
- GitHub Issues setup
- Milestones configuration
- Release automation
...
```

## GitHub CLI での操作（将来対応）

```bash
# Discussion を作成
gh discussion create \
  --title "New Feature Discussion" \
  --category "Ideas & Feedback" \
  --body "Discussion content..."

# Discussion 一覧
gh discussion list --category "Q&A"
```

## ベストプラクティス

1. **定期的なアナウンス**
   - 新規 Release
   - セキュリティアラート
   - 計画変更

2. **非同期での情報共有**
   - Session Notes
   - トラブルシューティング
   - 知見蓄積

3. **ラベルの活用**
   - パフォーマンス
   - セキュリティ
   - ドキュメント

4. **アーカイブと参照**
   - 過去の Discussion から学習
   - FAQ セクション立ち上げ

## 関連リンク

- [GitHub Discussions Docs](https://docs.github.com/en/discussions)
- [Repository Discussions](https://github.com/PLAYER1-r7/multicloud-auto-deploy/discussions)
