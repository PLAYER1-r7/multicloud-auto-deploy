# デプロイメント エラー分析と解決策

## 問題の状況

### エラーの証拠
```
AWS:   HTTP 500 - Internal Server Error
Azure: HTTP 503 - ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
GCP:   HTTP 200 - ✅ 正常に動作
```

### 根本原因

PR #61（`deploy-aws.yml` に `.github/config/aws*.env` paths を追加）がマージされましたが、pydantic-core がデプロイされていません。

理由：
1. PR #60 のマージ時点では、古い `deploy-aws.yml` 定義が使用されました
2. PR #61 の変更（新しい paths filter）は、次のプッシュイベント以降に効果を発揮します
3. その後、`.github/config/aws*.env` をトリガーとして変更していないため、新しいワークフロー定義が実行されていません

### GitHub Actions ワークフロー実行フロー

```
PR #60 マージ (2026-03-04 20:00)
↓
deploy-aws.yml トリガー（古い定義：config path なし）
↓
ワークフロー実行が失敗または不完全

PR #61 マージ (2026-03-04 20:21)
↓
deploy-aws.yml トリガー（... でも古い定義で実行される）
↓
新しい paths filter は反映されない

→ pydantic-core デプロイなし
```

## 解決策

### ステップ 1: PR #62 を作成・マージ

ブランチ `force/redeploy-pydantic` が既に作成されています。

**GitHub web UI から以下を実行してください：**

1. https://github.com/PLAYER1-r7/multicloud-auto-deploy/pull/new/force/redeploy-pydantic にアクセス
2. PR を作成（タイトル例: "fix: Trigger pydantic-core deployment with updated workflow"）
3. CI チェックスが合格するまで待機
4. PR をマージ

### ステップ 2: デプロイメント完了待機

マージ後、以下を実行してデプロイ完了を確認：

```bash
# 10-15分後に実行
curl https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com/health
curl https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api/health
```

**期待される結果：**
```json
{
  "status": "ok",
  "provider": "aws" or "azure",
  "version": "...（最新バージョン）"
}
```

### ステップ 3: 全環境確認

```bash
# AWS
curl -s https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com/health | jq .

# Azure  
curl -s https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api/health | jq .

# GCP (既に ✅ OK)
curl -s https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app/health | jq .
```

全て HTTP 200 かつ `"status": "ok"` が返れば成功です。

## 技術的詳細

### ワークフロー トリガー メカニズム

`deploy-aws.yml` の `on.push.paths`:
```yaml
paths:
  - "services/**"
  - "infrastructure/pulumi/aws/**"
  - ".github/config/aws*.env"        # ← PR #61 で追加
  - ".github/workflows/deploy-aws.yml"
```

**重要：** Workflow 定義ファイルの変更は、変更がマージされた直後のプッシュイベントでは、古い定義で実行されます。新しい定義は次のプッシュイベント以降に適用されます。

### なぜこの問題が発生したか

1. PR #60: CloudTrail disable → `.github/config/aws.production.env` 変更
   - ワークフロー実行 ✓
   - デプロイできないはず（config paths filter がまだない）

2. PR #61: `deploy-aws.yml` 修正（paths filter 追加）
   - ワークフロー実行 ✓（`.github/workflows/deploy-aws.yml` が paths に含まれている）
   - **しかし** 実行時は古い定義で実行される（新しい filter はまだ無効）

3. その後、config ファイルに変更がない
   - 新しい paths filter が有効になっているが、トリガーがない
   - 別のファイル（requirements.txt など）を変更する必要があります

## 参考情報

- **PR #56**: pydantic-core==2.23.2 を requirements.txt に明示的に追加
- **PR #59**: CloudTrail 有効化（IAM 権限不足で失敗）
- **PR #60**: CloudTrail 無効化（短期的な回避策）
- **PR #61**: ワークフロー trigger paths 修正（このブランチで config 変更を含める）

## 追加対応

PR #62 をマージした後、以下の確認を推奨します：

- [ ] AWS Lambda health endpoint が HTTP 200 を返す
- [ ] Azure Function App health endpoint が HTTP 200 を返す
- [ ] `/posts` エンドポイントが正常に動作する
- [ ] PR #58（LocalBackend delete_post 修正）をマージ
- [ ] CloudTrail IAM 権限設定を調査・実施

