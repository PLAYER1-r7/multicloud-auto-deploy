# コマンドエラー対応システム実装ガイド

> コマンドエラーを体系的に記録・管理するための標準プロセスが実装されました

---

## 📋 実装内容の一覧

このスクリーンショットで示される3つの重要な変更が加えられました：

| #   | ファイル                                                                                             | 説明                                             | 用途                                                |
| --- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------- |
| 1️⃣  | [`docs/AI_AGENT_ERROR_DOCUMENTATION_RULE.md`](docs/AI_AGENT_ERROR_DOCUMENTATION_RULE.md)             | コマンドエラー報告・ドキュメント化の標準プロセス | **AIエージェント＆チーム向け** — 何をすべきかが明確 |
| 2️⃣  | [`.github/ISSUE_TEMPLATE/command-error-report.yml`](.github/ISSUE_TEMPLATE/command-error-report.yml) | GitHub Issue テンプレート（コマンドエラー専用）  | **ユーザー向け** — エラー報告が簡単・一貫性を保証   |
| 3️⃣  | [`scripts/validate-commands.sh`](scripts/validate-commands.sh)                                       | コマンド実行環境の自動検証スクリプト             | **自動化** — エラー予防と環境確認を自動実行         |
| 4️⃣  | [`CONTRIBUTING.md`](CONTRIBUTING.md) — 新規セクション追加                                            | コマンドエラー報告ルール                         | **開発者向け** — プロセスの簡潔な説明               |

---

## 🎯 それぞれの役割

### 1️⃣ AI_AGENT_ERROR_DOCUMENTATION_RULE.md

**用途**: コマンドエラー報告・管理の標準プロセス定義

**内容**:

- ✅ エラー報告 → ドキュメント化 → テスト → CI/CD 統合の完全フロー
- ✅ 優先度判定フロー（どのドキュメントに追記するか）
- ✅ エラーID 命名規則（ERROR-001, ERROR-205 など）
- ✅ 運用スケジュール（日次・週次・月次の責務分け）
- ✅ ドキュメント参照ガイド

**参照される場面**:

- コマンドエラーが発生した開発者が「何をすればいいか」を確認
- チーム全体の標準プロセス理解

---

### 2️⃣ command-error-report.yml

**用途**: GitHub Issue テンプレート（フォーム化）

**入力項目**:

- 実行したコマンド（必須）
- エラーメッセージ（必須）
- 現在のディレクトリ（必須）
- OS・Python・Node.js バージョン
- 発生原因の推測
- 試したこと
- スクリーンショット・ログ（任意）

**効果**:

- 📌 **統一性**: すべてのエラー報告が同じ形式
- 📌 **完全性**: 重要な情報が漏れない
- 📌 **追跡可能性**: ラベル自動付与（`type:command-error`）で GitHub Issues から簡単に検索可能

**使い方**:

```bash
# GitHub Web で新規 Issue 作成
# → "コマンドエラー報告" テンプレートを選択
# → フォームを埋める
# → Submit
```

---

### 3️⃣ validate-commands.sh

**用途**: ローカル環境チェック＆自動修正スクリプト

**チェック項目** (10項目):

1. ディレクトリ構造（api, frontend_react など）
2. Node.js インストール
3. Python 環境（仮想環境の有無）
4. npm パッケージ（node_modules）
5. pip パッケージ（fastapi など）
6. AWS CLI 認証
7. Azure CLI 認証
8. gcloud CLI 認証
9. Docker インストール＆起動確認
10. Git hooks 設定

**使い方**:

```bash
# 環境をチェック
./scripts/validate-commands.sh

# 自動修正を試みる
./scripts/validate-commands.sh --fix

# 厳密モード（1つのエラーで即終了）
./scripts/validate-commands.sh --strict
```

**効果**:

- ⚠️ エラーを事前に発見（問題が起きる前に）
- 🔧 自動修正（一般的な環境セットアップはスクリプトで自動）
- 📊 環境レポート（何が足りていないかが一目瞭然）

---

### 4️⃣ CONTRIBUTING.md 更新

**セクション名**: 🔴 コマンドエラー報告ルール

**内容**:

- エラー発生時の4ステップフロー
- テンプレート使用方法
- ドキュメント優先度表
- チェックリスト

**効果**:

- 🎯 プロセスが一ページで理解可能
- 🔗 AI_AGENT_ERROR_DOCUMENTATION_RULE.md への参照リンク

---

## 🔄 エラー報告プロセスの全体像

### ユーザーの視点（簡潔フロー）

```
1. コマンドエラー発生
   ↓
2. ./scripts/validate-commands.sh 実行
   ↓
3. GitHub Issue 作成（command-error-report テンプレート）
   ↓
4. チームが対応 → ドキュメント更新 → Issue クローズ
   ↓
5. 同じエラー再発防止 ✅
```

### チームの視点（詳細フロー）

```
GitHub Issue 受取
  ↓
AI_AGENT_ERROR_DOCUMENTATION_RULE.md に従って優先度判定
  ├─ パス誤り？
  │   └─ AI_AGENT_14 の「よくあるエラー」に追加
  │
  ├─ 環境変数未設定？
  │   └─ AI_AGENT_14 の「環境変数の設定」に追加
  │
  ├─ 複雑な新規エラー？
  │   └─ AI_AGENT_COMMAND_ERROR_REGISTRY.md に ERROR-### として記録
  │
  └─ 本番環境特有？
      └─ TROUBLESHOOTING.md に追加

  ↓
エラー ID 割り当て（ERROR-205 など）
  ↓
ドキュメント更新 + PR 作成
  ↓
validate-commands.sh 更新（再発防止用チェック追加）
  ↓
PR マージ
  ↓
Issue クローズ
  ↓
CI で定期検証開始（毎週 validate-commands.sh 実行）
```

---

## 📋 ドキュメント別の役割分担

| ドキュメント                                      | 読者                                     | 更新頻度     | 含まれるエラー                |
| ------------------------------------------------- | ---------------------------------------- | ------------ | ----------------------------- |
| **AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md** | AIエージェント、新規開発者               | 毎月         | よくあるエラー（頻出5-10件）  |
| **AI_AGENT_COMMAND_ERROR_REGISTRY.md**            | テクニカルリード、拡張ドキュメント参照者 | 四半期       | 複雑な新規エラー（ERROR-###） |
| **TROUBLESHOOTING.md**                            | 運用・本番環境担当者                     | 必要に応じて | 本番環境特有のエラー          |
| **CONTRIBUTING.md**                               | 開発者                                   | 年1回        | プロセス理解・リンク先指定    |

---

## 🚀 実行方法

### 初回セットアップ

```bash
# リポジトリ最新化
cd /workspaces/multicloud-auto-deploy
git pull origin main

# スクリプト実行権限確認
ls -l scripts/validate-commands.sh
# -rwxr-xr-x ... validate-commands.sh

# 環境チェック（初回所要時間: 1-2分）
./scripts/validate-commands.sh

# 環境構築が不完全なら自動修正
./scripts/validate-commands.sh --fix
```

### 定期実行（CI/CD 統合予定）

```bash
# GitHub Actions ワークフロー (.github/workflows/command-validation.yml)：
# - 毎週日曜 0:00 UTC に自動実行
# - エラーが検出されると Issue 自動生成
# - チーム全体で進行状況を追跡可能
```

---

## 💡 使用例

### 例1: パス誤りが発生

```bash
cd services/frontend      # ❌ Error: no such directory

# GitHub Issue 作成
# → command-error-report テンプレート入力
# → タイトル: [Command Error] cd - no such directory

# チーム対応
# → AI_AGENT_14 セクション "よくあるエラー" に追記
# → ERROR-001 として記録
# → ドキュメント +PR マージ
# → Issue クローズ
```

**結果**: 次のユーザーが AI_AGENT_14 を読めば、同じエラーで困らない ✅

---

### 例2: 新規エラーが発生

```bash
pip install -r requirements.txt
# ERROR: Could not find a version that satisfies the requirement fastapi==0.109.0

# GitHub Issue 作成 → テンプレート入力

# チーム対応
# → 旧バージョン問題と判定
# → ERROR-205 として COMMAND_ERROR_REGISTRY に記録
# → validate-commands.sh に pip バージョン判定ロジック追加
# → ドキュメント + PR マージ

# 3週間後、CI/CD が validate-commands.sh を実行
# → 同じ環境指標が見つかる → 警告を表示
# → エラーが再発する前に予防 ✅
```

**結果**: 自動チェックにより、同じエラーが起きる前に検出できる ✅

---

## 📊 メリット

### 開発者向け

| メリット             | 具体例                                      |
| -------------------- | ------------------------------------------- |
| **エラー報告が簡単** | テンプレート使用で情報漏れなし              |
| **再発防止**         | 同じエラーはドキュメントで解決可能          |
| **自動チェック**     | `validate-commands.sh` で環境問題を事前発見 |
| **知識が蓄積**       | エラー記録がナレッジベースになる            |

### AIエージェント向け

| メリット       | 効果                                                    |
| -------------- | ------------------------------------------------------- |
| **エラー予測** | AI_AGENT_14 を参照して間違ったコマンドを避ける          |
| **自動修正**   | validate-commands.sh で環境を自動修復                   |
| **確実な対応** | AI_AGENT_ERROR_DOCUMENTATION_RULE.md で標準プロセス理解 |

### チーム向け

| メリット       | 効果                              |
| -------------- | --------------------------------- |
| **一元管理**   | GitHub Issues + ドキュメント連携  |
| **優先度付け** | ERROR-### ID で複雑なエラーを分類 |
| **運用効率化** | CI/CD で定期検証、エラー自動報告  |
| **品質向上**   | 同じバグの繰り返し減少            |

---

## 📚 参照フロー

新しい開発者やAIエージェントが、コマンドエラーで困ったときの参照順序：

```
1. エラーが発生
   ↓
2. ./scripts/validate-commands.sh 実行（すぐに解決できるか確認）
   ↓
3. docs/AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md
   → 「よくあるエラーと解決策」セクション確認
   ↓
4. GitHub Issues 検索（command-error ラベル）
   → 同じエラー報告はないか確認
   ↓
5. 上記で見つからなければ GitHub Issue 新規作成
   → command-error-report テンプレート使用
```

---

## ✅ 次のステップ

1. **即実装**:
   - ✅ `docs/AI_AGENT_ERROR_DOCUMENTATION_RULE.md` 作成完了
   - ✅ `.github/ISSUE_TEMPLATE/command-error-report.yml` 作成完了
   - ✅ `scripts/validate-commands.sh` 作成完了
   - ✅ `CONTRIBUTING.md` 更新完了

2. **今後自動実行（CI/CD）**:
   - `.github/workflows/command-validation.yml` を作成
   - 毎週日曜 0:00 UTC に `validate-commands.sh` を実行
   - エラー検出時に Issue を自動生成

3. **定期メンテナンス**:
   - 毎月 AI_AGENT_14 更新
   - 四半期ごと ERROR_REGISTRY レビュー
   - 運用チームが TROUBLESHOOTING.md を更新

---

## 📖 関連ドキュメント

- 📋 **メインドキュメント**: [docs/AI_AGENT_ERROR_DOCUMENTATION_RULE.md](docs/AI_AGENT_ERROR_DOCUMENTATION_RULE.md)
- 🔴 **日常的コマンド参照**: [docs/AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md](docs/AI_AGENT_14_COMMAND_USAGE_AND_DIRECTORY_JA.md)
- 🐛 **トラブルシューティング**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 🤝 **コントリビューティング**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**実装日**: 2026-03-04
**バージョン**: 1.0.0
**対象**: AIエージェント・開発者・チーム全体
