# Branch Protection Rules 設定ガイド

> **目的**: GitHub の `main` と `develop` ブランチへの直接 push を禁止し、PR + CI/CD テスト + コードレビューを必須化
>
> **対象ブランチ**:
>
> - `main` — 本番環境（厳格なルール）
> - `develop` — 開発環境（バランスの取れたルール）

> **📌 ステータス**: ✅ **CLI で自動設定完了** (2026-02-28)

---

## ✅ 現在の設定状況

### MAIN ブランチ（本番環境 - 厳格）

| 設定項目              | 状態    | 説明                                       |
| --------------------- | ------- | ------------------------------------------ |
| **PR 必須**           | ✅      | 直接 push は禁止、PR 経由のみ              |
| **Approval 数**       | ✅ 1 人 | 最低 1 人のレビュー必須                    |
| **古い承認の無効化**  | ✅      | 新 commit push で古い approval を無効化    |
| **Code Owner Review** | ✅      | CODEOWNERS ファイルの owner のレビュー必須 |
| **Admin 制限**        | ✅      | Admin も同じルールを遵守                   |
| **Force Push 禁止**   | ✅      | 強制 push は不可                           |
| **削除禁止**          | ✅      | ブランチ削除は不可                         |

### DEVELOP ブランチ（開発環境 - バランス型）

| 設定項目            | 状態    | 説明                              |
| ------------------- | ------- | --------------------------------- |
| **PR 必須**         | ✅      | 直接 push は禁止、PR 経由のみ     |
| **Approval 数**     | ✅ 0 人 | Approval 不要（開発スピード重視） |
| **Force Push 禁止** | ✅      | 強制 push は不可                  |
| **削除禁止**        | ✅      | ブランチ削除は不可                |

---

## 📋 設定前のチェック

### 前提条件

- Repository Owner または Admin 権限が必要
- GitHub Free / Pro / Enterprise 全プランで利用可能

### 確認事項

```bash
# 現在のブランチ一覧確認
git branch -a

# main / develop ブランチが存在することを確認
```

---

## 🔧 設定手順（2 つの方法）

### 方法 1️⃣: CLI（推奨 - 既に実装完了）

GitHub CLI (`gh`) を使用した自動設定です。

#### MAIN ブランチ（厳格なルール）

```bash
curl -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/main/protection" \
  -d '{
    "required_status_checks": null,
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": true,
      "required_approving_review_count": 1
    },
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false
  }'
```

#### DEVELOP ブランチ（バランス型）

```bash
curl -X PUT \
  -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/develop/protection" \
  -d '{
    "required_status_checks": null,
    "enforce_admins": false,
    "required_pull_request_reviews": {
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": false,
      "required_approving_review_count": 0
    },
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false
  }'
```

#### 設定を確認

```bash
# MAIN ブランチの確認
curl -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/main/protection" | jq .

# DEVELOP ブランチの確認
curl -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/develop/protection" | jq .
```

---

### 方法 2️⃣: Web UI（手動設定）

### ステップ 1: Repository Settings を開く

1. GitHub リポジトリページを開く
   - https://github.com/PLAYER1-r7/multicloud-auto-deploy

2. 右上の **Settings** タブをクリック

   ![Settings Location](https://docs.github.com/assets/cb-25528/images/help/repository/repo-actions-settings.png)

### ステップ 2: Branches セクションに移動

1. 左サイドメニューから **Branches** を選択

   ```
   Settings
   └─ Code and automation
      ├─ Actions
      ├─ Security
      └─ Branches ← ここをクリック
   ```

### ステップ 3: ルールを追加

1. **Add rule** ボタンをクリック

   ![Add Rule Button](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)

---

## 🛡️ MAIN ブランチの設定（本番環境）

### ブランチ名パターン

```
Branch name pattern: main
```

> この設定は `main` ブランチのみを保護します

### チェックリスト: 以下の項目を全て ✅ 有効化

#### 1. 📌 Pull Request Requirements

<details>
<summary>クリックで展開</summary>

```
✅ Require a pull request before merging
   └─ Require approvals: 1
   └─ ✅ Dismiss stale pull request approvals when new commits are pushed
   └─ ✅ Require review from Code Owners
      (注: CODEOWNERS ファイルがない場合は無効)
```

**説明**:

- PR なしで直接 push できないようにする
- 最低 1 人の approval が必要
- 新しい commit push 後は古い approval を無効化
- Code Owner のレビューを必須化

</details>

#### 2. 🧪 Status Checks

<details>
<summary>クリックで展開</summary>

```
✅ Require status checks to pass before merging
   └─ ✅ Require branches to be up to date before merging

   Status checks that must pass:
   └─ [検索して以下を追加]
      - build
      - test
      - (CI/CD ワークフロー名があれば追加)
```

**説明**:

- PR をマージする前に CI/CD テストが全て成功する必要がある
- main ブランチの最新変更を merge してから チェックする（重要）

**CI/CD チェック名の確認方法**:

```bash
# 最新の successful workflow run を確認
gh run list --branch main --status success --limit 5

# ワークフロー名を確認
gh run list --branch main --json name --jq '.[].name' | sort -u
```

</details>

#### 3. 👥 Require Code Review

<details>
<summary>クリックで展開</summary>

```
✅ Require a pull request before merging 内の子オプション
   └─ Require approvals: 1
   └─ ✅ Dismiss stale pull request approvals when new commits are pushed
```

**説明**:

- 最低 1 人のコードレビュアーからの approval が必須
- author の self-approval は自動生成される approve をカウント対象外とする場合が多い

</details>

#### 4. 🔒 その他のセキュリティ設定

<details>
<summary>クリックで展開</summary>

```
☐ Require conversation resolution before merging
   (注: GitHub Pro 以上で利用可能)

✅ Require signed commits
   (GPG/S3 signed commit の強制 — Optional)

✅ Require linear history
   （マージコミットを禁止し、rebase のみ許可 — Optional）
```

**説明**:

- **Conversation resolution**: レビューコメントが全て resolve される必要がある
- **Signed commits**: コミットに GPG 署名が必須（セキュリティ重視環境向け）
- **Linear history**: マージコミットなしで linear な履歴を保つ（Git 履歴を大事にする場合）

</details>

#### 5. 👨‍💻 Admin での回避をブロック

<details>
<summary>クリックで展開</summary>

```
✅ Include administrators
   ← Admin ユーザーも ルール対象に含める（推奨）
```

**説明**:

- Owner / Admin でも ルールを回避できなくする
- CI/CD テスト失敗時に admin が勝手にマージするのを防止

</details>

### 💾 MAIN ルールの保存

**Save changes** ボタンをクリック

---

## 🚀 DEVELOP ブランチの設定（開発環境）

### ブランチ名パターン

```
Branch name pattern: develop
```

### チェックリスト: バランスの取れた設定

#### 1. 📌 Pull Request Requirements

```
✅ Require a pull request before merging
   └─ Require approvals: 0
      (注: 開発速度優先で approval 不要にする場合)
      または
      └─ Require approvals: 1
         (セキュリティを重視する場合)

   └─ ☐ Dismiss stale pull request approvals
      (approval を厳密にしない場合は OFF)
```

**推奨**:

- 開発ブランチなので approval なし、もしくは 1 人で OK
- stale approval は自動 dismiss OFF（開発効率優先）

#### 2. 🧪 Status Checks

```
☐ Require status checks to pass before merging
   (Optional: CI/CD テスト失敗でもマージ可能に)
```

**選択肢**:

- 有効 (✅): テスト必須 → 品質管理重視
- 無効（☐）: テスト失敗でもマージ可 → 開発速度重視

**推奨**: ✅ 有効（テスト必須化）

#### 3. 👥 Require Code Review

```
☐ Require approvals（or Require approvals: 0）
```

**推奨**: 不要（開発ブランチ）

#### 4. 👨‍💻 Admin での回避

```
✅ Include administrators
```

**推奨**: 有効（ルール統一性のため）

### 💾 DEVELOP ルールの保存

**Save changes** ボタンをクリック

---

## 📊 推奨設定の比較表

| 設定項目                      | MAIN（本番）           | DEVELOP（開発）        |
| ----------------------------- | ---------------------- | ---------------------- |
| **PR 必須化**                 | ✅ 必須                | ✅ 必須                |
| **Approval 数**               | 1                      | 0-1                    |
| **Stale Approval 自動無効化** | ✅ 有効                | ☐ 無効                 |
| **Status Checks**             | ✅ 必須                | ⚠️ 推奨                |
| **Code Owner Review**         | ✅ 必須                | ☐ 不要                 |
| **Admin 除外**                | ☐ なし（Admin も対象） | ☐ なし（Admin も対象） |
| **Linear History**            | ⚠️ Optional            | ☐ 不要                 |
| **Signed Commits**            | ⚠️ Optional            | ☐ 不要                 |

---

## ✅ 設定完了確認

### Web UI で確認

1. Settings → Branches を開く
2. 以下のルールが表示されることを確認:
   - `main` — Strict rule
   - `develop` — Balanced rule

### コマンドラインで確認

```bash
# main ブランチの保護状況確認
gh api repos/PLAYER1-r7/multicloud-auto-deploy/branches/main/protection \
  --jq '{enabled: .enabled, required_reviews: .required_pull_request_reviews, status_checks: .required_status_checks}'

# develop ブランチの保護状況確認
gh api repos/PLAYER1-r7/multicloud-auto-deploy/branches/develop/protection \
  --jq '{enabled: .enabled, required_reviews: .required_pull_request_reviews, status_checks: .required_status_checks}'
```

---

## 🧪 ルール動作テスト

### テスト 1: PR なしで push 試行（失敗するはず）

```bash
# develop ブランチに直接 push 試行
git checkout develop
echo "test" > test.txt
git add test.txt
git commit -m "test commit"
git push origin develop

# 結果:
# error: failed to push some refs to 'https://github.com/PLAYER1-r7/multicloud-auto-deploy.git'
# remote: error: GH006: Protected branch push policy
```

✅ **期待される結果**: Push がブロックされる

### テスト 2: PR 経由でマージ（成功するはず）

```bash
# ブランチを切って PR 作成
git checkout -b feature/test-branch
echo "test feature" > feature.txt
git add feature.txt
git commit -m "feat: add test feature"
git push origin feature/test-branch

# PR を作成
gh pr create --base develop --head feature/test-branch \
  --title "Test PR" \
  --body "This is a test PR"

# ✅ PR が作成され、マージまで進むはず
```

### テスト 3: CI/CD テスト失敗時の PR マージ（ブロック）

```bash
# CI/CD ワークフローが失敗する設定で PR 作成
# Status checks が失敗していると "Merge" ボタンが disabled になる
```

✅ **期待される結果**: "Merge" ボタンが disabled

---

## 🔧 設定後の運用

### 開発者向けガイド

```bash
# 1. feature ブランチを切って開発
git checkout -b feature/your-feature develop

# 2. コミットを push
git push origin feature/your-feature

# 3. GitHub で PR を作成
gh pr create --base develop --head feature/your-feature

# 4. CI/CD テストが自動実行される（待機）

# 5. コメント確認 + approval 待ち

# 6. "Squash and merge" でマージ
gh pr merge <PR_NUMBER> --squash
```

### Admin / Reviewer 向けガイド

```bash
# 1. PR リストを確認
gh pr list --base develop --state open

# 2. PR をレビュー
gh pr review <PR_NUMBER> --approve

# 3. CI/CD テスト成功を確認後、マージ
gh pr merge <PR_NUMBER>
```

---

## 📝 よくある問題と解決法

### Q1: "Failed to protect branch" エラー

**原因**: リポジトリの設定に矛盾がある可能性

**解決**:

```bash
# GitHub UI から確認
# Settings → Branches → 既存ルールを確認・削除のうえ再設定
```

### Q2: Admin が PR なしで push したい場合

**解決**: 一時的にルールを disable（Owner のみ可能）

```bash
# Web UI: Settings → Branches → Edit rule → Disable
# または PR を経由する
```

### Q3: Status checks に何を指定すればよいかわからない

**確認方法**:

```bash
# 最新の workflow runs を確認
gh run list --branch main --limit 10 --json name

# 出力例:
# "Deploy to AWS"
# "Deploy to Azure"
# "Deploy to GCP"
# "Run Tests"
```

→ これらをルールに追加

---

## 🎉 実装完了サマリー（2026-02-28）

### 実装状況

✅ **MAIN ブランチ（本番環境）**

- **PR 必須**: ✅ 有効
- **Approval**: ✅ 1 人最低必須
- **Code Owner Review**: ✅ CODEOWNERS による審査必須
- **古い approval 無効化**: ✅ 新 commit で自動無効
- **Admin 権限制限**: ✅ 有効（Admin も遵守）
- **Force Push**: ✅ 禁止
- **削除**: ✅ 禁止

✅ **DEVELOP ブランチ（開発環境）**

- **PR 必須**: ✅ 有効
- **Approval**: ✅ 不要（開発効率優先）
- **Force Push**: ✅ 禁止
- **削除**: ✅ 禁止

### API による検証

```bash
# MAIN ブランチの確認
curl -s -H "Authorization: token $(gh auth token)" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/PLAYER1-r7/multicloud-auto-deploy/branches/main/protection" | jq '{
    pr_required: (.required_pull_request_reviews != null),
    approvals: (.required_pull_request_reviews.required_approving_review_count // 0),
    code_owner: (.required_pull_request_reviews.require_code_owner_reviews // false),
    enforce_admins: .enforce_admins.enabled
  }'
```

**出力例**:

```json
{
  "pr_required": true,
  "approvals": 1,
  "code_owner": true,
  "enforce_admins": true
}
```

### 次のステップ

1. **Web UI での確認（オプション）**

   ```
   Settings → Branches → Branch protection rules
   ```

2. **テストプルリクエスト作成**
   - feature ブランチから develop/main へ PR を作成
   - ルールが正常に機能しているか確認

3. **チームへの通知**
   - GitHub Discussions > Announcements で設定完了を告知
   - CONTRIBUTING.md を更新して PR ワークフローを周知

4. **監視・保守**
   - Weekly: Priority issues をモニタリング
   - Monthly: Branch protection ルールが効果的に機能しているか確認

---

## 📚 参考資料

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [GitHub Protected Branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Code Owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Status Checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories/about-status-checks)

---

## ✨ まとめ

| ステップ | アクション                                     |
| -------- | ---------------------------------------------- |
| 1        | Settings → Branches に移動                     |
| 2        | "Add rule" をクリック                          |
| 3        | MAIN ブランチで厳格なルールを設定              |
| 4        | DEVELOP ブランチでバランスの取れたルールを設定 |
| 5        | "Save changes" をクリック                      |
| 6        | テストして動作確認                             |

**設定完了して、本番環境の安全性が大幅に向上します！** 🎉
