# 10 — AI エージェント向けプロジェクト管理（Backlog と実行運用）

> Part III — 運用 | 親: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
> 目的: 本リポジトリでAIエージェントが計画・実行・進捗更新・優先順位付けを一貫運用するための標準を定義する。

---

## スコープ

本ドキュメントは以下を対象に、AI主導のプロジェクト管理手順を定義する：

- Backlog 受付とトリアージ（Issues）
- 実装とレビュー（Pull Requests）
- デプロイ前後の安全確認（Actions + Status ドキュメント）
- 運用レポート（生成ダッシュボード）

関連ドキュメント：

- [AI_AGENT_00_CRITICAL_RULES_JA.md](AI_AGENT_00_CRITICAL_RULES_JA.md)
- [AI_AGENT_06_STATUS_JA.md](AI_AGENT_06_STATUS_JA.md)
- [AI_AGENT_07_RUNBOOKS_JA.md](AI_AGENT_07_RUNBOOKS_JA.md)
- [AI_AGENT_09_GITHUB_INTEGRATION_JA.md](AI_AGENT_09_GITHUB_INTEGRATION_JA.md)

---

## 戦略

### S1. 正本を一本化する

- GitHub Issues を正本 Backlog とする。
- 優先度とリリース意図は labels + milestones で管理する。
- 環境の事実情報は Issue コメントではなく [AI_AGENT_06_STATUS_JA.md](AI_AGENT_06_STATUS_JA.md) に保持する。

### S2. カデンスで回す

- 日次: 新規 Issue トリアージ、優先度再評価、blocked 解除。
- 週次: スプリント候補確定、上位優先課題の固定。
- リリース前: CI 健全性 + 本番リスクを確認して `main` マージ可否を判断。

### S3. リスク先行で優先順位付け

優先順：

1. セキュリティ・認証回帰
2. 本番障害
3. リリース信頼性を下げる staging ブロッカー
4. 機能開発・リファクタ

### S4. 根本原因のクローズ

- ルール0.5に従い、可能な限り根本対策を採用する。
- 暫定対応時は期限と恒久対応Issueを必ず残す。

---

## 必要ツール

## 必須

| ツール | 用途 |
| --- | --- |
| GitHub Issues | backlog、トリアージ、担当管理 |
| GitHub Pull Requests | 実装レビュー、マージゲート |
| GitHub Actions | CI/CD 健全性、デプロイ状態 |
| GitHub Labels | 優先度、クラウド範囲、作業種別 |
| GitHub Milestones | リリース単位の束ね |
| `gh` CLI | issues/PR/workflow の自動取得 |
| `scripts/agent_pm_sync.py` | PMスナップショット/ダッシュボード生成 |

## 任意

| ツール | 用途 |
| --- | --- |
| GitHub Projects | ボード管理（必要時） |
| `scripts/monitor-cicd.sh` | CI失敗の詳細監視 |

---

## 認証リクエスト方針

`gh`・`aws`・`az`・`gcloud`・レジストリ・外部APIなどで認証が必要な場合、AIエージェントは以下を必須とする：

1. 認証不足を早期検出する（無駄な再試行を繰り返さない）。
2. ただちにユーザーへ認証を依頼し、実行コマンドまたは最小手順を提示する。
3. 何の作業が認証待ちで止まっているかを明示する。
4. 認証完了後は処理を再開する。

認証を完了できない場合は、当該作業を認証待ちとして停止し、再度認証を依頼する。原則として代替手段や縮退運用へ勝手に切り替えない（ユーザーが明示的に代替を指示した場合のみ実施する）。

`gh` を使うPM運用での標準依頼コマンド：

```bash
gh auth login
```

---

## ラベルと命名規約

推奨ラベル：

- 種別: `bug`, `feature`, `refactor`, `docs`
- 範囲: `aws`, `azure`, `gcp`, `all`
- 優先度: `priority:critical`, `priority:high`, `priority:low`
- 状態: `blocked`

ブランチ命名：

- `feature/issue-{id}-{short-desc}`
- `bugfix/issue-{id}-{short-desc}`
- `refactor/issue-{id}-{short-desc}`
- `docs/issue-{id}-{short-desc}`

---

## 運用モデル

## 日次 AI PM ループ

0. 当該タスクに必要な認証状態（`gh` など）を最初に確認する。
1. `project-management: sync` を実行して最新化。
2. 優先度上位 Issue を確認。
3. blocked または滞留 Issue に next action を記載。
4. 最上位の未着手・未blocked Issue を実装対象に選定。
5. マージ前に CI 傾向を確認。

## 週次 AI PM ループ

1. 14日以上未完了 Issue を再評価。
2. 本番・staging リスクに応じて優先度を更新。
3. milestone を再整列。
4. 週次サマリを共有。

---

## 生成ファイル

PM同期で以下を生成する：

- `docs/generated/project-management/snapshot.json`
- `docs/generated/project-management/dashboard.md`

生成ファイルは手編集せず、同期コマンドを再実行する。

GitHub Actions による自動更新も設定する：

- Workflow: `.github/workflows/project-management-sync.yml`
- 実行時刻: 毎日 09:15 JST（00:15 UTC）
- 自動更新対象: `docs/generated/project-management/snapshot.json`, `docs/generated/project-management/dashboard.md`

## ブランチ保護の基準（1人開発向け）

`main` の推奨設定（ソロ開発）：

- PR経由マージ必須: 有効
- 必須承認数: `0`
- 必須ステータスチェック: 有効（`strict: true`）
  - `CodeQL — javascript-typescript`
  - `CodeQL — python`

運用確認手順：

1. workflow更新PRを `main` にマージする。
2. `Project Management Sync` を手動実行する。
3. 最新runと `sync` ジョブが `completed/success` であることを確認する。

---

## プロジェクト管理の Done 定義

Issue は次を満たしたとき運用上 Done：

- 必須チェック通過済みPRがマージ済み
- ブランチ規約（`develop`/`main`）に従ってデプロイ確認済み
- 関連ドキュメント更新済み（`STATUS` / Runbook / Feature reference）
- 根本原因の要約付きで Issue クローズ済み

---

## 実行コマンド

```bash
# AI PM ダッシュボードを生成/更新
python3 scripts/agent_pm_sync.py

# VS Code task から実行する場合
# タスク名: project-management: sync
```

```bash
# GitHub Actions を手動実行
gh workflow run "Project Management Sync"
```
