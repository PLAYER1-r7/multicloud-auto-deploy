# 00 — 重要ルール：最初に必ず読むこと

> **このドキュメントはリポジトリ内の他のドキュメントを読む前に必ず読むこと。**
> データロス・本番環境障害・数時間のデバッグを招く最小限のルールセットが含まれている。
> ここに書かれたすべての項目は過去のインシデントから学んだ教訓である。

---

## このドキュメントを読んだ後

以下の14個のルールをすべて読んだら、この順序で続行する：

```
1. AI_AGENT_01_CONTEXT.md   ← プロジェクトの概要、ライブエンドポイント、使用技術（5分）
2. AI_AGENT_02_ARCHITECTURE.md ← ディレクトリツリー、各ファイルの配置（5分）
3. AI_AGENT_03_API.md ← システムトポロジー、ストレージパスレイアウト（5分）
4. AI_AGENT_06_STATUS.md     ← 3つのクラウド環境すべての現在の健全性
5. AI_AGENT_09_TASKS.md      ← 優先度付きバックログ — 次に何をするか
```

タスクで必要な場合だけこれらを読む：

```
AI_AGENT_04_INFRA.md    ← エンドポイント仕様、リクエスト/レスポンススキーマ、データモデル
AI_AGENT_05_CICD.md     ← Pulumiスタック、リソース名、設定キー、スタック出力
AI_AGENT_07_RUNBOOKS.md ← GitHub Actionsワークフロー、必要なシークレット、トリガー条件
AI_AGENT_08_SECURITY.md ← ステップバイステップ：Lambda デプロイ、React デプロイ、GCP Cloud Run など
```

---

## ルール0 — すべてのドキュメントは日本語版と英語版を併記

すべてのソースコードコメント、コミットメッセージ、プルリクエスト説明、GitHub Actionsワークフローコメント、Pulumiスタックコメント、ドキュメントファイルは **英語で記述しなければならない**（本版）。

このマルチクラウドインフラプロジェクトは異なるチームのエンジニアがレビューする可能性がある。英語での一貫性により、すべての自動ツール（検索、grep、AIエージェント）がコンテンツを正しく処理できる。

ただし、日本語ユーザー向けの解説書や日本語訳ドキュメント（このファイルなど）は日本語で記述してもよい。

---

## ルール1 — ファイル操作：単一バッチで大量のファイルを作成・編集しない

単一のツール呼び出しバッチで大量のファイルを作成・編集すると、ネットワークエラーやタイムアウトが発生する可能性がある。部分的な結果が無声のうちに破損し、デバッグが非常に困難になる。

**常に段階的に作業する：**

1. **一度に数個のファイル**だけを作成または編集する。
2. 各ステップを検証してから続行する（コンパイルチェック、構文チェック、テスト）。
3. 途中でネットワークエラーが発生した場合、既に作成されたものを確認してから再試行する。

---

## ルール2 — Dev Container は ARM (aarch64) で実行；本番では x86_64

VS Code dev containerは `linux/aarch64` 用に構築されている。すべてのクラウドランタイム（Lambda、Azure Functions、Cloud Run、Cloud Functions）は `linux/amd64` で実行される。**aarch64上でネイティブにコンパイルされたPythonパッケージはバイナリ互換性がなく、実行時に `.so` インポートエラーでクラッシュする。**

**デプロイ用にPythonパッケージをインストールする場合、常にDocker を使用し、ターゲットプラットフォームを明示的に設定する：**

```bash
docker run --rm --platform linux/amd64 \
  -v /tmp/deploy:/out python:3.12-slim \
  bash -c "pip install --no-cache-dir --target /out -r requirements.txt -q"
```

これは以下に適用される：

- Lambda ZIP パッケージング（`requirements-aws.txt`, `requirements-layer.txt`）
- GCP Cloud Functions ZIP パッケージング（`requirements-gcp.txt`）
- Azure Functions デプロイ（`requirements-azure.txt`）

dev container 内で `pip install` をホストマシンで実行してデプロイアーティファクトを生成しない。

---

## ルール3 — `main` ブランチ = 即座に本番環境にデプロイされる

```
develop  →  staging（ステージング）
main     →  production（本番）← push後すぐに本番環境で実行される
```

本番環境にすぐにデプロイするつもりがない限り、`main` に直接プッシュしない。
常に `develop`（またはフィーチャーブランチ）で作業し、ステージングが成功したことを確認してから `main` にマージする。

---

## ルール4 — `AUTH_DISABLED` はステージングと本番環境では常に `false` でなければならない

環境変数 `AUTH_DISABLED` は常に `false` でなければならない。過去のインシデントでは、誤って `true` に設定されていたため、すべてのAPIエンドポイントに対して認証なしでアクセスできていた。

CI ワークフロー、Pulumi 設定、`.env` ファイルのどこでも `AUTH_DISABLED=true` を見つけた場合、重大なバグとして扱い、直ちに修正する。

---

## ルール5 — Lambda / Cloud Run の環境変数は Pulumi 出力から取得し、GitHub シークレットから取得しない

過去のバグにより、対応する GitHub シークレットが本番環境に存在しなかったため、`API_GATEWAY_ENDPOINT` 値が無声のうちに空になった。

**従うべきパターン**（`deploy-*.yml` 内）：

```yaml
- name: Get Pulumi outputs
  run: |
    cd infrastructure/pulumi/aws
    echo "API_URL=$(pulumi stack output api_url --stack $STACK)" >> $GITHUB_ENV
```

`pulumi stack output` から導出できる値には `${{ secrets.API_GATEWAY_ENDPOINT }}` のような GitHub シークレットを決して使用しない。シークレットが存在しない場合、変数は無声のうちに空の文字列になり、Lambda/Function はハードコードされたフォールバック（しばしば `localhost:8000`）を使用して起動する。

---

## ルール6 — AWS ステージングフロントエンドは `VITE_BASE_PATH=/sns/` でビルドしなければならない

SNS React アプリは `s3://bucket/sns/` にデプロイされる。`VITE_BASE_PATH=/sns/` なしでビルドすると、すべての JS/CSS アセットが `/assets/...` を参照し、404 が発生する。CloudFront はすべてのアセットリクエストに対して `Content-Type: text/html` で `index.html` を配信し、MIME タイプエラーでアプリ全体が破損する。

```bash
cd services/frontend_react
set -a && source .env.aws.staging && set +a
VITE_BASE_PATH=/sns/ npm run build
```

CloudFront カスタムエラーページも `/sns/index.html` を指す必要があり、`/index.html` ではない。

---

## ルール7 — S3 画像バケットはプライベート：常に署名付き GET URL を返す

`multicloud-auto-deploy-staging-images` はすべてのパブリックアクセスがブロックされている。バックエンドはフロントエンドに投稿を返す前に `_resolve_image_urls()` を呼び出す必要がある。これは保存された S3 キー（`imageKeys`）を有効期限1時間の署名付き GET URL に変換する。

生の S3 キーを返すか、署名付き URL をデータベースにキャッシュすると、1時間後に破損した画像リンクが得られる。

---

## ルール8 — AWS 本番環境 CloudFront：任意の `pulumi up` の前に Pulumi 設定を指定する

以下の設定がないと、`pulumi up --stack production` は CloudFront をデフォルト証明書に戻し、すべての HTTPS ビジターに対して `NET::ERR_CERT_COMMON_NAME_INVALID` が発生する。

```bash
cd infrastructure/pulumi/aws
pulumi config set customDomain www.aws.ashnova.jp --stack production
pulumi config set acmCertificateArn \
  arn:aws:acm:us-east-1:278280499340:certificate/914b86b1-4c10-4354-91cf-19c4460dcde5 \
  --stack production
```

本番 AWS スタックで `pulumi up` を実行する前に、これら2つの設定値が存在することを常に確認する。

---

## ルール9 — Cognito `id_token` 検証：`verify_at_hash: False` を設定する

フロントエンドが `id_token` のみを送信する場合（エスコート `access_token` なし）、JWT ライブラリは `at_hash` を計算または検証できない。`jwt_verifier.py` への呼び出しは `verify_at_hash=False` を渡さなければならない。この設定を戻すと、すべての認証付き API 呼び出しが破損する。

参照：`services/api/app/jwt_verifier.py`

---

## ルール10 — GCP：デプロイ ZIP 内で常に `function.py` を `main.py` としてコピーする

`--entry-point` が別の関数に名前を付けている場合でも、Cloud Build は `missing main.py` で失敗する。修正方法はデプロイソースに `main.py` を含めることである：

```bash
cp services/api/function.py /tmp/deploy_gcp/.deployment/main.py
```

常に `function.py` と `main.py` の両方を ZIP に含める。これを怠ると、Cloud Build はソースを拒否し、関数は更新されない。

---

## ルール11 — GCP：`generate_signed_url()` は `service_account_email` + `access_token` が必要

Cloud Run と Cloud Functions は Compute Engine 認証情報を使用する（秘密鍵なしのアクセストークンのみ）。追加の引数なしで `blob.generate_signed_url()` を呼び出すと、以下が発生する：

```
AttributeError: you need a private key to sign credentials
```

正しい呼び出し：

```python
blob.generate_signed_url(
    expiration=3600,
    method="GET",
    service_account_email=settings.gcp_service_account,
    access_token=credentials.token,
)
```

サービスアカウントメールは Cloud Run サービスで環境変数 `GCP_SERVICE_ACCOUNT` を介して提供される。SA は `roles/iam.serviceAccountTokenCreator` も持つ必要がある。

---

## ルール12 — GCP：Firebase 認可ドメインは Identity Toolkit API を介して登録する必要がある

新しい Cloud Run URL またはカスタムドメインが追加される場合、Firebase Auth に明示的に登録する必要がある。Identity Toolkit Admin v2 `PATCH` エンドポイントをヘッダー `x-goog-user-project: PROJECT_ID` で使用する — このヘッダーを省略すると、有効な管理者トークンがあっても `403 PERMISSION_DENIED` が返される。

このステップは `deploy-gcp.yml`（`Update Firebase Authorized Domains`）で自動化されている。これを削除またはスキップしない。

---

## ルール13 — GCP：CDN は `Cross-Origin-Opener-Policy: same-origin-allow-popups` を送信する必要がある

このレスポンスヘッダーがないと、Firebase `signInWithPopup` は `popup.closed` をチェックできず、COOP 警告を繰り返し、厳格なブラウザー環境でのログインフローを潜在的に破損する。

これを CDN バックエンドバケットカスタムレスポンスヘッダーとして設定する（Pulumi または `gcloud` 経由）。
変更後、CDN キャッシュを無効化する：

```bash
gcloud compute url-maps invalidate-cdn-cache <URL_MAP_NAME> \
  --path "/*" --project ashnova
```

---

## ルール14 — Azure Functions：CORS は Python コードではなく、プラットフォームレベルで設定する必要がある

Azure Functions（Flex Consumption）は **Python ランタイムの前に Kestrel（.NET HTTP サーバー）を実行する**。Kestrel がすべての `OPTIONS` プリフライトリクエストを Python コードに到達する前に傍受する。FastAPI CORS ミドルウェアで `Access-Control-Allow-Origin` を設定しても、**効果がない** — Kestrel がミドルウェアに到達する前にレスポンスを返す。

**常に Azure CLI または Portal 経由で CORS を設定する：**

```bash
# Function App CORS（ブラウザからの API コールを制御）
az functionapp cors add \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins "https://your.domain.com"

# 最初にワイルドカードを削除する（ワイルドカードは個別オリジンを抑制する）
az functionapp cors remove \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --allowed-origins '*'
```

**Azure Blob Storage CORS は Function App CORS から完全に独立している**。
画像アップロードは SAS URL 経由で Blob Storage に直接移動する（Function App をバイパス）。
Blob Storage CORS は別途設定する必要がある：

```bash
az storage cors add \
  --account-name "$STORAGE_ACCOUNT" \
  --services b \
  --methods GET POST PUT DELETE OPTIONS \
  --origins "https://your.domain.com" \
  --allowed-headers "*" \
  --exposed-headers "*" \
  --max-age 3600
```

また：`SCM_DO_BUILD_DURING_DEPLOYMENT` は Flex Consumption では **サポートされていない** — `InvalidAppSettingsException` をトリガーする。常に Docker を使用してパッケージをローカルでビルドしてからデプロイする。

---

## ルール15 — Azure Functions：`host.json` は `routePrefix: ""` を設定する必要がある

Azure Functions は デフォルトで `routePrefix: "api"`に設定されており、すべての HTTP トリガーに `/api/` のプリフィックスを付ける。フロントエンドは `/api/` プリフィックスなしで `/posts`、`/health` のようなパスを呼び出す。
この修正がないと、すべての API エンドポイントが 404 を返す。

**必須の `host.json` コンテンツ：**

```json
{
  "version": "2.0",
  "extensions": {
    "http": {
      "routePrefix": ""
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

また：Azure AD `post_logout_redirect_uri` はアプリの `redirect_uris` に明示的に登録する必要がある。`/sns/auth/callback` コールバック URL のみを登録することは不十分 — ログアウトリターン URL（例：`/sns/`）も追加する必要がある：

```bash
az ad app update \
  --id "$AD_APP_ID" \
  --web-redirect-uris \
    "https://your.domain.com/sns/auth/callback" \
    "https://your.domain.com/sns/"
```

---

## ルール16 — GitHub Features を積極的に活用する

このプロジェクトは GitHub の機能を最大限に活用するように設計されている。タスク実行時は以下を活用すること：

### GitHub Issues

- 新しいタスク・バグ・改善案を見つけたら、必ず `gh issue create` で GitHub Issue を作成する
- 既存の Issue へのコメント、進捗更新は `gh issue comment` で行い、Issue にコンテキストを残す
- Issue にラベル（`bug`, `enhancement`, `documentation`, `security` など）を付与して分類する

```bash
# Issue を作成
gh issue create --title "タイトル" --body "説明" --label bug,high-priority

# Issue をコメント更新
gh issue comment <ISSUE_NUMBER> --body "進捗: ..."

# Issue にラベルを追加
gh issue edit <ISSUE_NUMBER> --add-label enhancement
```

### Pull Requests

- コード変更は常に Pull Request（PR）経由で行う（`main` への直接 push は禁止 — ルール3参照）
- PR 作成時は以下を含める：
  - 明確なタイトル（Conventional Commits 形式：`feat(api): ...`, `fix(ui): ...` など）
  - 変更内容の説明
  - 関連する Issue 番号（`Closes #123`)
  - レビュー必須者（`@PLAYER1-r7` など）

```bash
# 機能ブランチを作成とPRを同時に作成
git checkout -b feature/new-endpoint develop
git push origin feature/new-endpoint
gh pr create --base develop --title "feat(api): add /posts endpoint" \
  --body "Closes #25"
```

### GitHub Releases と CHANGELOG

- Version タグは `v1.2.3` 形式で付与する
- Release 作成は自動化ワークフロー（`.github/workflows/release.yml`）に任せる
- Release Notes と CHANGELOG.md は自動で生成される

```bash
# Version タグを打つ（Release 自動生成がトリガーされる）
git tag v1.1.0
git push origin v1.1.0
```

### Branch Protection Rules

- `main` ブランチは厳格なルール下で保護されている（PR 必須、approval 必須、Code Owner review 必須）
- `develop` ブランチは PR 必須で動作効率とセキュリティのバランスを取っている
- 詳細は [docs/BRANCH_PROTECTION_SETUP.md](./BRANCH_PROTECTION_SETUP.md) を参照

### GitHub Discussions

- 質問、提案、知見共有は GitHub Discussions を使う
- カテゴリ：📢 Announcements, 💡 Ideas & Feedback, 🤝 General Discussion, ❓ Q&A, 🔧 Technical Help

```bash
# Discussions は Web UI から https://github.com/PLAYER1-r7/multicloud-auto-deploy/discussions で作成
```

**GitHub Features の活用により、以下が実現できる：**
- 🔄 プロジェクト進捗の自動可視化
- 📊 タスク管理と GitHub Issues の一元化
- 🚀 Release 自動化 + CHANGELOG 自動生成
- 🛡️ PR ベースの code review の強制化
- 📚 GitHub Pages による自動ドキュメント公開

---

## ルール17 — 必要なアプリケーションはインストール可能

Dev Container 環境では、タスク実行に必要なアプリケーション（ツール、ライブラリ、CLI など）は自由にインストール可能である。

### インストール許可リスト

**常にインストール OK：**

- Python パッケージ（`pip install`）
- Node.js パッケージ（`npm install`）
- Docker イメージ（`docker pull`）
- 開発ツール（`git`, `curl`, `jq`, `terraform`, `pulumi`, `aws`, `az`, `gcloud` など）
- システムパッケージ（`apt install` など必要に応じて）

**記載事項：**

1. インストールしたツールは `apt`, `pip`, `npm` でインストールし、記録に残す
2. インストール後は動作確認を行う（`--version` など）
3. 重要なツール（新規言語ランタイムなど）は CONTRIBUTING.md に記載する必要がある

```bash
# Python パッケージをインストール（推奨）
pip install --upgrade pandas requests

# AWS CLI をアップグレード
aws --version && pip install --upgrade awscli

# システムパッケージをインストール（必要に応じて）
apt-get update && apt-get install -y jq curl

# インストール後は検証
python3 --version
terraform -version
```

### パッケージのアップグレード

Dependabot が週次で依存関係をチェックし、セキュリティアップデートが自動 PR として提案される（[docs/GITHUB_FEATURES_GUIDE.md](./GITHUB_FEATURES_GUIDE.md) 参照）。

---

## クイックリファレンス：何がどこにあるか

| トピック                       | ファイル                                                   |
| ------------------------------ | ---------------------------------------------------------- |
| ライブエンドポイント URL       | [AI_AGENT_01_CONTEXT.md](AI_AGENT_01_CONTEXT.md)           |
| リポジトリディレクトリツリー   | [AI_AGENT_01_CONTEXT.md](AI_AGENT_01_CONTEXT.md)           |
| システムアーキテクチャ         | [AI_AGENT_02_ARCHITECTURE.md](AI_AGENT_02_ARCHITECTURE.md) |
| API ルート & データモデル      | [AI_AGENT_03_API.md](AI_AGENT_03_API.md)                   |
| Pulumi / IaC                   | [AI_AGENT_04_INFRA.md](AI_AGENT_04_INFRA.md)               |
| CI/CD パイプライン             | [AI_AGENT_05_CICD.md](AI_AGENT_05_CICD.md)                 |
| 現在の環境健全性               | [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md)             |
| ステップバイステップランブック | [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md)         |
| セキュリティ設定               | [AI_AGENT_08_SECURITY.md](AI_AGENT_08_SECURITY.md)         |
| 残りのタスク / バックログ      | [AI_AGENT_09_TASKS.md](AI_AGENT_09_TASKS.md)               |
| すべて — エントリーポイント    | [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)                     |
