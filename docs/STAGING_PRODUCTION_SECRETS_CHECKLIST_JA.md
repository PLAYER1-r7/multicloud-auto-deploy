# staging/production シークレット整備チェック手順

最終更新: 2026-03-05

## 目的

`staging` / `production` の GitHub Environments で、デプロイに必要なシークレット不足を事前検知し、
`azure/login` のような認証エラーを防ぐ。

## 対象ワークフロー

- `.github/workflows/deploy-sns-aws.yml`
- `.github/workflows/deploy-exam-solver-aws.yml`
- `.github/workflows/deploy-sns-azure.yml`
- `.github/workflows/deploy-exam-solver-azure.yml`
- `.github/workflows/deploy-sns-gcp.yml`
- `.github/workflows/deploy-exam-solver-gcp.yml`

## 必須シークレット（APIデプロイ最小セット）

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `GCP_CREDENTIALS`

> 注記: GitHub Actions は `environment` 指定ジョブで **Environment Secret** を優先し、
> 無ければ Repository Secret を参照できる構成。運用は Environment Secret を推奨。

## 1) 事前準備

```bash
gh auth status
```

未ログイン時:

```bash
gh auth login
```

## 2) 不足シークレットを自動チェック

追加済みスクリプト:

- `scripts/check-github-env-secrets.sh`

実行:

```bash
bash scripts/check-github-env-secrets.sh
```

フロントエンド用も含める場合:

```bash
bash scripts/check-github-env-secrets.sh --include-frontend
```

## 3) 不足分を投入

### staging へ設定

```bash
printf '%s' "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID --env staging
printf '%s' "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY --env staging
printf '%s' "$AZURE_CLIENT_ID" | gh secret set AZURE_CLIENT_ID --env staging
printf '%s' "$AZURE_TENANT_ID" | gh secret set AZURE_TENANT_ID --env staging
printf '%s' "$AZURE_SUBSCRIPTION_ID" | gh secret set AZURE_SUBSCRIPTION_ID --env staging
printf '%s' "$GCP_CREDENTIALS_JSON" | gh secret set GCP_CREDENTIALS --env staging
```

### production へ設定

```bash
printf '%s' "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID --env production
printf '%s' "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY --env production
printf '%s' "$AZURE_CLIENT_ID" | gh secret set AZURE_CLIENT_ID --env production
printf '%s' "$AZURE_TENANT_ID" | gh secret set AZURE_TENANT_ID --env production
printf '%s' "$AZURE_SUBSCRIPTION_ID" | gh secret set AZURE_SUBSCRIPTION_ID --env production
printf '%s' "$GCP_CREDENTIALS_JSON" | gh secret set GCP_CREDENTIALS --env production
```

`GCP_CREDENTIALS` をファイルから設定する場合:

```bash
gh secret set GCP_CREDENTIALS --env staging < gcp-sa-staging.json
gh secret set GCP_CREDENTIALS --env production < gcp-sa-production.json
```

## 4) 再チェック

```bash
bash scripts/check-github-env-secrets.sh
```

期待値: `staging` / `production` ともに `✅ Required secrets are available`。

## 5) ワークフロー実行で最終確認

例: Exam Solver (Azure)

```bash
gh workflow run deploy-exam-solver-azure.yml -f environment=staging
gh run watch
```

認証エラーが解消されていれば、`Configure Azure Credentials` ステップを通過する。

## よくある失敗と対処

- `Login failed ... Not all values are present`（Azure）
  - 原因: `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` の欠落
  - 対処: 対象 environment（`staging` / `production`）に3点を設定

- `Invalid value for [--runtime]`（GCP）
  - 原因: ランタイム指定値の不一致
  - 対処: ワークフローでサポート済みランタイム表記を使用（現行は `python312`）
