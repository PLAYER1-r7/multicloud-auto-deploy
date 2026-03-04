# コマンドエラーレジストリ＆ドキュメント化ルール

> コマンド実行時のエラーを体系的に記録・解決するための標準プロセス

---

## 概要

このドキュメントは、以下を実現するためのルールです：

✅ **エラー発生時** → 正しい使用方法をドキュメント化
✅ **再発防止** → 同じエラーが繰り返されないよう管理
✅ **知識共有** → AIエージェント・開発者が参照できる一元管理
✅ **自動検証** → CI/CD でコマンドの妥当性をチェック

---

## プロセス概要

### 1️⃣ コマンドエラーが発生

```bash
# 例：誤ったディレクトリでコマンド実行
cd services/frontend    # ❌ ディレクトリが存在しない
npm install
# Error: ENOENT: no such file or directory
```

### 2️⃣ GitHub Issue で報告（テンプレート使用）

- **テンプレート**: `.github/ISSUE_TEMPLATE/command-error-report.yml`
- **タイトル**: `[Command Error] <コマンド名> - <エラーメッセージ>　`
- **ラベル**: `type:command-error` 自動付与

```yaml
title: "[Command Error] npm install - ENOENT"
labels: ["type:command-error"]
```

### 3️⃣ ドキュメント化

**更新対象ドキュメント**（優先順）：

| 優先度 | ドキュメント                                         | 対象                                      |
| ------ | ---------------------------------------------------- | ----------------------------------------- |
| 🔴 高  | `docs/AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md` | **よくあるエラー集** にエラーケースを追加 |
| 🟡 中  | `docs/AI_AGENT_COMMAND_ERROR_REGISTRY.md`            | **新規エラーパターン**を詳細記録          |
| 🟢 低  | `TROUBLESHOOTING.md`                                 | 運用レベルのエラー対応                    |

### 4️⃣ テストと検証

- `scripts/validate-commands.sh` でコマンド妥当性を自動チェック
- CI/CD ワークフローで定期実行

### 5️⃣ Close Issue

- Issue をクローズする際、PR でドキュメント更新をリンク
- ドキュメント確認後にマージ

---

## 詳細プロセス

### ステップA: Issue テンプレート入力

GitHub Issue 作成時に以下を記入：

```
【コマンド実行内容】
cd services/api
pip install -r requirements.txt

【エラーメッセージ】
ERROR: Could not find a version that satisfies the requirement fastapi==0.109.0

【実行環境】
OS: Ubuntu 24.04
Python: 3.13
仮想環境: .venv

【発生原因（推測）】
PyPI レジストリに旧バージョンが登録されていない可能性
または仮想環境が正しく有効化されていない

【試したこと】
- pip cache clean --force
- requirements.txt のバージョン指定変更
```

### ステップB: ドキュメント更新ルール

#### パターン A: 既存エラーの場合

`docs/AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md` の **「よくあるエラーと解決策」** セクションに追記：

````markdown
## 🔴 Error: `fastapi==0.109.0 not found in PyPI`

**原因**: パッケージバージョンが古いか、レジストリに登録されていない

**解決策**:

1. pip キャッシュをクリア
   ```bash
   pip cache clean --force
   ```
````

2. インストール可能なバージョン確認
   ```bash
   pip index versions fastapi
   ```
3. requirements.txt を最新バージョンに更新
   ```bash
   fastapi==0.115.0  # 例：最新バージョン
   ```
4. 再度インストール
   ```bash
   pip install -r requirements.txt
   ```

**参考**: [GitHub Issue #<番号>](https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues/XXX)

````

#### パターン B: 新規エラーの場合

`docs/AI_AGENT_COMMAND_ERROR_REGISTRY.md` に新しいセクションを追加：

```markdown
## ERROR-###: <エラーカテゴリ名>

**ID**: ERROR-001（連番）
**初出日**: 2026-03-04
**関連Issue**: #XXX
**重大度**: Low / Medium / High

### 症状
```bash
# エラーが発生するコマンド例
command_name <args>
# Error: <メッセージ>
````

### 根本原因

- 原因の詳細説明

### 解決策

1. ステップA
2. ステップB
3. ステップC

### 予防策

- チェックリスト項目
- 自動検証方法

### 関連エラー

- ERROR-002
- ERROR-003

````

### ステップC: 検証スクリプト更新

同じエラーが再発しないよう、`scripts/validate-commands.sh` に検証ロジックを追加：

```bash
# 例：パッケージバージョン検証
check_pip_package_version() {
    local package=$1
    local min_version=$2

    echo "✓ Checking $package version..."
    pip index versions "$package" > /dev/null 2>&1 || {
        echo "❌ $package not found in PyPI"
        return 1
    }
}

# 実行例
check_pip_package_version "fastapi" "0.109.0"
````

### ステップD: CI/CD 統合

`.github/workflows/` に定期検証ワークフロー `command-validation.yml` を作成：

```yaml
name: Validate Commands
on:
  schedule:
    - cron: "0 0 * * 0" # 週1回（日曜日）
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run command validation
        run: ./scripts/validate-commands.sh
      - name: Report errors
        if: failure()
        run: |
          echo "⚠️ コマンド検証に失敗しました"
          echo "GitHub Issues で報告してください"
```

---

## 実装チェックリスト

コマンドエラーが発生した場合の対応フロー：

### 🔵 実行者の責務

- [ ] エラーが発生したコマンド、引数、ディレクトリを記録
- [ ] `git log --oneline -5` でコミット履歴を確認
- [ ] GitHub Issue テンプレート「Command Error Report」で報告
  - テンプレート位置: `.github/ISSUE_TEMPLATE/command-error-report.yml`
- [ ] タイトルフォーマット: `[Command Error] <コマンド> - <エラー要約>`
- [ ] ラベル `type:command-error` が自動付与されることを確認

### 🟢 ドキュメント更新者の責務

- [ ] Issue を読んで原因を特定
- [ ] 適切なドキュメント（AI_AGENT_14 or ERROR_REGISTRY）を選択
- [ ] エラーケース、原因、解決策を記載
- [ ] 実際に解決策を実行してテスト
- [ ] PR でドキュメント更新をコミット（Issue リンク付き）
- [ ] Review 後マージ
- [ ] Issue をクローズ（PR へのリンク付き）

### 🟠 CI/CD チェック実行者の責務

- [ ] 毎週 CI でコマンド検証を実行
- [ ] エラーが検出される場合は Issue を自動生成
- [ ] GitHub Issues ボード で優先度付け

---

## ドキュメント更新の優先度判定フロー

```
コマンドエラー発生
  ↓
エラーの種類を判定
  ├─ 旧バージョン・廃止コマンド？
  │   └─ 「よくあるエラー」セクションに追加（AI_AGENT_14）
  │
  ├─ パス誤り（ディレクトリ名など）？
  │   └─ 「パス指定の正しい方法」セクションに追加（AI_AGENT_14）
  │
  ├─ 環境変数・設定漏れ？
  │   └─ 「環境変数の設定」セクションに追加（AI_AGENT_14）
  │
  └─ 新種の非常に複雑なエラー？
      └─ 新規エラーパターンを ERROR_REGISTRY に記録（ERROR-### として ID 付与）
```

---

## エラーID の命名規則

```
ERROR-<番号>: <エラーカテゴリ>

番号の振り方：
- 001-099: パス・ディレクトリ関連
- 100-199: 環境変数・設定関連
- 200-299: パッケージ・依存関係関連
- 300-399: クラウドサービス API 関連
- 400-499: デプロイ・インフラ関連
- 500-599: その他
```

### 例

| ID        | エラー                           | 関連                                            |
| --------- | -------------------------------- | ----------------------------------------------- |
| ERROR-001 | フロントエンドディレクトリ名誤り | `services/frontend` → `services/frontend_react` |
| ERROR-002 | Lambda 関数名誤り                | 関数名スペル間違い                              |
| ERROR-205 | pip パッケージバージョン未登録   | PyPI に旧バージョンなし                         |
| ERROR-310 | AWS CLI 未認証                   | `aws sts get-caller-identity` が失敗            |

---

## テンプレート参照

### GitHub Issue テンプレート

位置: `.github/ISSUE_TEMPLATE/command-error-report.yml`

以下は自動生成されます：

```yaml
name: コマンドエラー報告
description: コマンド実行時のエラーを報告
labels: ["type:command-error"]
body:
  - type: markdown
    attributes:
      value: |
        # コマンドエラー報告フォーム
        エラーが発生したコマンドの詳細を記入してください

  - type: textarea
    id: command
    attributes:
      label: 実行したコマンド
      description: エラーが発生した完全なコマンドを記入
      placeholder: |
        cd services/api
        pip install -r requirements.txt
    validations:
      required: true

  - type: textarea
    id: error_message
    attributes:
      label: エラーメッセージ
      description: ターミナルに表示されたエラーメッセージをコピー＆ペースト
      placeholder: |
        ERROR: Could not find a version that satisfies the requirement fastapi==0.109.0
    validations:
      required: true

  - type: input
    id: os
    attributes:
      label: OS
      placeholder: Ubuntu 24.04 / macOS 14 / Windows 11
    validations:
      required: true

  - type: input
    id: python_version
    attributes:
      label: Python バージョン
      placeholder: "3.13"
    validations:
      required: true

  - type: textarea
    id: diagnosis
    attributes:
      label: 発生原因（推測）
      description: 自分で思い当たる原因があれば記入
      placeholder: パッケージが古いか、PyPI に登録されていない可能性

  - type: textarea
    id: tried_solutions
    attributes:
      label: 試したこと
      placeholder: |
        - pip cache clean --force
        - requirements.txt 更新
```

---

## 運用スケジュール

| 頻度       | 実施内容                                   | 責任者         |
| ---------- | ------------------------------------------ | -------------- |
| **毎日**   | Issue コメント監視、緊急コマンドエラー対応 | 開発者         |
| **毎週**   | CI でコマンド検証実行                      | GitHub Actions |
| **毎月**   | ERROR_REGISTRY レビュー、ドキュメント整理  | 技術リード     |
| **四半期** | 旧エラーの削除、新しい検証ルール追加       | チーム         |

---

## 関連ドキュメント

- 📖 [AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md](AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md) — 日常的なコマンド使用法
- 📋 [CONTRIBUTING.md](../CONTRIBUTING.md) — 開発ガイド
- 🐛 [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) — トラブルシューティング

---

**更新日**: 2026-03-04
**バージョン**: 1.0.0
**対象**: AIエージェント、開発者向け標準プロセス
