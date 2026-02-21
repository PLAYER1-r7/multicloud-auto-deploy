# 11 — Workspace Migration & Repository Cleanup (2026-02-21)

> Parent: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)

---

## 概要

2026-02-21 に行ったリポジトリクリーンアップの記録。  
今後 `multicloud-auto-deploy/` を VS Code のルートフォルダとして開いて作業するための情報源。

---

## リポジトリ構造（移行後）

```
ashnova/                              ← git リポジトリルート
│
├── .devcontainer/                    ← ashnova全体を開く場合のdevcontainer設定
├── .github/
│   └── workflows/                   ← ★ GitHub Actions が読む唯一の場所
│       ├── deploy-aws.yml
│       ├── deploy-azure.yml
│       ├── deploy-gcp.yml
│       ├── deploy-landing-aws.yml
│       ├── deploy-landing-azure.yml
│       ├── deploy-landing-gcp.yml
│       ├── deploy-frontend-web-aws.yml
│       ├── deploy-frontend-web-azure.yml
│       └── deploy-frontend-web-gcp.yml
├── .gitignore
├── .vscode/                          ← ashnova全体を開く場合のVSCode設定（旧・不使用）
├── LICENSE
├── README.md
│
└── multicloud-auto-deploy/           ← ★ プロジェクトルート（ここを VS Code で開く）
    ├── .devcontainer/                ← VS Code devcontainer設定（multicloud-auto-deployを開く場合）
    ├── .gitignore
    ├── .vscode/
    │   └── settings.json            ← VS Code設定（Python venv、フォーマット等）
    ├── infrastructure/
    ├── services/
    ├── static-site/                  ← ★ ランディングページ（aws/azure/gcp サブディレクトリ含む）
    ├── scripts/
    ├── docs/
    └── ...
```

---

## `multicloud-auto-deploy/` を VS Code で開く際の注意事項

### `.github/workflows/` の場所

**GitHub Actions のワークフローは `ashnova/.github/workflows/` にしか存在しない。**  
`multicloud-auto-deploy/` を VS Code で開くと、ファイルツリーには `.github/workflows/` が表示されないが、  
git リポジトリのルートは依然として `ashnova/` であるため、  
**CI/CD は正常に動作する（GitHub 上で push すれば自動実行される）。**

ワークフローを編集する場合は、ターミナルから:

```bash
# devcontainer 内から
cd /workspaces/ashnova    # git ルートへ移動
code .github/workflows/deploy-aws.yml
```

または、GitHub 上でのブラウザ編集が確実。

### ワークフロー内のパス表記

ワークフローは **git リポジトリルートからの相対パス** でファイルを参照する。  
`multicloud-auto-deploy/` を起点として記述されているため、以下のようなパスが多用される:

```yaml
# ワークフロー内での記述例
working-directory: multicloud-auto-deploy/services/api
aws s3 sync multicloud-auto-deploy/static-site/ s3://...
cd multicloud-auto-deploy/infrastructure/pulumi/aws
```

### devcontainer 設定

`multicloud-auto-deploy/.devcontainer/devcontainer.json` が使用される。  
`postCreateCommand` で `bash .devcontainer/setup.sh` が実行され:

- `infrastructure/pulumi/aws|azure|gcp/requirements.txt` の pip install
- `scripts/*.sh` への実行権限付与

が自動で行われる。

---

## 2026-02-21 に削除・整理したファイル

### 削除したディレクトリ（旧バージョン）

| 削除したパス                        | 削除理由                                                                    |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `ashnova/ashnova.v1/`               | v1 の旧コード。クラウドリソース削除済み                                     |
| `ashnova/ashnova.v2/`               | v2 の旧コード。クラウドリソースなし                                         |
| `ashnova/ashnova.v3/`               | v3 の旧コード。クラウドリソース削除済み                                     |
| `ashnova/infrastructure/`           | `multicloud-auto-deploy/infrastructure/` の古いコピー                       |
| `ashnova/services/api/`             | `multicloud-auto-deploy/services/api/` の古いコピー。CI/CD は mcad 版を参照 |
| `ashnova/services/frontend_react/`  | deploy-frontend-\*.yml 削除後に参照なし                                     |
| `ashnova/services/frontend_reflex/` | いずれのワークフローからも未参照                                            |
| `ashnova/scripts/`                  | `multicloud-auto-deploy/scripts/` の古いコピー。CI/CD は mcad 版を参照      |
| `ashnova/static-site/`              | `multicloud-auto-deploy/static-site/` に統合                                |
| `multicloud-auto-deploy/.github/`   | GitHub Actions に読まれない死んだコード                                     |

### 削除したワークフロー

| 削除したファイル                                   | 削除理由                                                                                |
| -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `deploy-multicloud.yml.disabled`                   | `.disabled` で明示的に無効化済み                                                        |
| `main_multicloud-auto-deplopy-staging-funcapp.yml` | Azure Portal 自動生成。存在しないリソースに対するデプロイ。typo あり                    |
| `main_multicloud-auto-deploy-staging-func.yml`     | 同上                                                                                    |
| `deploy-frontend-aws.yml`                          | `ashnova/services/frontend_react/`（旧版）をハードコードされた staging 固定値でデプロイ |
| `deploy-frontend-azure.yml`                        | 上記と同様。削除済み旧 API URL にハードコード                                           |
| `deploy-frontend-gcp.yml`                          | 上記と同様                                                                              |

### 移動・作成したファイル

| アクション                                          | 内容                                  |
| --------------------------------------------------- | ------------------------------------- |
| `multicloud-auto-deploy/.vscode/settings.json` 作成 | Python venv パス・エディタ設定        |
| `multicloud-auto-deploy/static-site/aws/` コピー    | `ashnova/static-site/aws/` から移行   |
| `multicloud-auto-deploy/static-site/azure/` コピー  | `ashnova/static-site/azure/` から移行 |
| `multicloud-auto-deploy/static-site/gcp/` コピー    | `ashnova/static-site/gcp/` から移行   |

### ワークフローのパス更新

`deploy-landing-*.yml` と `deploy-aws.yml` / `deploy-gcp.yml` 内の  
`static-site/` → `multicloud-auto-deploy/static-site/` に変更。

---

## 削除したクラウドリソース（旧バージョン）

### v3 (Pulumi: ashnova-v3-aws/staging)

- 22 リソースを `pulumi destroy` で削除（2026-02-21）
- Pulumi スタックも `pulumi stack rm` で削除

### v1 (Terraform管理、satoshi AWSプロファイル)

AWS CLI で直接削除:

- API Gateway REST API: `utw7e2zuwc`
- Lambda Layer `simple-sns-nodejs-dependencies`: バージョン 5, 6, 10, 11
- DynamoDB テーブル: `simple-sns-messages`

### v2

- デプロイ済みリソースなし（対応不要）

### 孤立 Pulumi スタック

- `ashnova/simple-sns-aws/staging` (0 リソース) を `pulumi stack rm` で削除

---

## アクティブな本番環境（削除後に確認済み）

| クラウド | URL                           | 確認日時      |
| -------- | ----------------------------- | ------------- |
| AWS      | https://www.aws.ashnova.jp/   | 2026-02-21 ✅ |
| Azure    | https://www.azure.ashnova.jp/ | 2026-02-21 ✅ |
| GCP      | https://www.gcp.ashnova.jp/   | 2026-02-21 ✅ |

全 12 テスト（ランディング / SNS アプリ / API ヘルスチェック / GET /posts）が PASS。  
API バージョン: `3.0.0`

---

## 現在のワークフロー一覧（9件）

| ファイル                        | トリガーパス                                      | 役割                                                                |
| ------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------- |
| `deploy-aws.yml`                | `multicloud-auto-deploy/**`                       | AWS フルスタックデプロイ（Pulumi + API + frontend_react + landing） |
| `deploy-azure.yml`              | `multicloud-auto-deploy/**`                       | Azure フルスタックデプロイ                                          |
| `deploy-gcp.yml`                | `multicloud-auto-deploy/**`                       | GCP フルスタックデプロイ                                            |
| `deploy-landing-aws.yml`        | `multicloud-auto-deploy/static-site/**`           | AWS ランディングページのみ更新                                      |
| `deploy-landing-azure.yml`      | `multicloud-auto-deploy/static-site/**`           | Azure ランディングページのみ更新                                    |
| `deploy-landing-gcp.yml`        | `multicloud-auto-deploy/static-site/**`           | GCP ランディングページのみ更新                                      |
| `deploy-frontend-web-aws.yml`   | `multicloud-auto-deploy/services/frontend_web/**` | frontend_web Lambda のみ更新（AWS）                                 |
| `deploy-frontend-web-azure.yml` | `multicloud-auto-deploy/services/frontend_web/**` | frontend_web のみ更新（Azure）                                      |
| `deploy-frontend-web-gcp.yml`   | `multicloud-auto-deploy/services/frontend_web/**` | frontend_web のみ更新（GCP）                                        |

---

## トラブルシューティング

### ワークフローが GitHub 上に表示されない

`multicloud-auto-deploy/` を VS Code で開いた状態では `.github/` が見えないが、  
GitHub リポジトリのワークフロー画面 (`/actions`) には正常に表示される。  
ローカルで確認したい場合: `ls /workspaces/ashnova/.github/workflows/`

### static-site の変更が CI でデプロイされない

変更を `multicloud-auto-deploy/static-site/**` に加える必要がある（旧: `ashnova/static-site/`）。  
`deploy-landing-*.yml` のトリガーパスは `multicloud-auto-deploy/static-site/**` に更新済み。

### Pulumi スタックが見つからない

`cd /workspaces/ashnova/multicloud-auto-deploy/infrastructure/pulumi/aws` に移動して `pulumi stack ls`。  
開発コンテナ内では AWS / Azure / GCP の認証情報は `/home/vscode/.aws` 等にマウント済み。

### Python インタープリターが見つからない

`multicloud-auto-deploy/.vscode/settings.json` に venv 設定があるが、初期状態では `.venv` はない。  
Pulumi インフラの Python 依存は各 `infrastructure/pulumi/*/` 内で仮想環境を作成する:

```bash
cd infrastructure/pulumi/aws
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

---

## git ルート移行（`multicloud-auto-deploy/` を新ルートにする）

### 準備状況（2026-02-21 完了済み）

| 項目 | 状態 |
| ---- | ---- |
| `multicloud-auto-deploy/.github/workflows/` (9ファイル) | ✅ 作成済み・パス修正済み |
| 全9ファイルに `multicloud-auto-deploy/` プレフィックスが含まれないこと | ✅ `grep -rc "multicloud-auto-deploy/" ...` → 全ファイル `:0` 確認済み |
| `multicloud-auto-deploy/.devcontainer/` (setup.sh 相対パス) | ✅ 確認済み |
| `multicloud-auto-deploy/.gitignore` | ✅ 存在 |
| `multicloud-auto-deploy/LICENSE` | ✅ 存在 |
| `multicloud-auto-deploy/README.md` | ✅ 存在 |
| `multicloud-auto-deploy/.vscode/settings.json` | ✅ 作成済み |
| `multicloud-auto-deploy/static-site/` (aws/azure/gcp サブディレクトリ含む) | ✅ 統合済み |

### ワークフローのパス比較

| ファイル | 現行 (`ashnova/.github/workflows/`) | 移行後 (`multicloud-auto-deploy/.github/workflows/`) |
| ------- | ----------------------------------- | ---------------------------------------------------- |
| `deploy-aws.yml` | `cd multicloud-auto-deploy/services/api` | `cd services/api` |
| `deploy-aws.yml` | `cd multicloud-auto-deploy/infrastructure/pulumi/aws` | `cd infrastructure/pulumi/aws` |
| `deploy-landing-aws.yml` | `multicloud-auto-deploy/static-site/` | `static-site/` |
| トリガー `paths:` | `"multicloud-auto-deploy/services/**"` | `"services/**"` |

### 実行すべき git 移行コマンド（ユーザーが手動で実行）

> **注意**: 以下はどれか1つを選んで実行する。操作後は GitHub にて確認すること。

#### オプション A — 履歴を保持（推奨）

```bash
cd /workspaces/ashnova

# multicloud-auto-deploy/ の履歴だけを切り出して新ブランチを作成
git subtree split --prefix=multicloud-auto-deploy -b git-root

# 確認
git log git-root --oneline | head -10

# 新しいリポジトリを作成して push
mkdir /tmp/ashnova-mcad
cd /tmp/ashnova-mcad
git init
git pull /workspaces/ashnova git-root
git remote add origin <新しいGitHub repo URL>
git push -u origin main
```

#### オプション B — 履歴なし・シンプル（新規 repo の場合）

```bash
cd /workspaces/ashnova/multicloud-auto-deploy
git init
git add .
git commit -m "chore: initialize repository root at multicloud-auto-deploy"
git remote add origin <新しいGitHub repo URL>
git branch -M main
git push -u origin main
```

#### オプション C — `git filter-repo`（高精度・要インストール）

```bash
pip install git-filter-repo

cd /workspaces/ashnova
git filter-repo --subdirectory-filter multicloud-auto-deploy --force
# → ashnova/ リポジトリ自体が multicloud-auto-deploy/ の内容に上書きされる
git remote set-url origin <新しいGitHub repo URL>
git push --force
```

### 移行後に実施すること

1. **GitHub Actions の確認**: 旧 `ashnova/.github/workflows/` は GitHub 上で読まれなくなる。新リポジトリの `.github/workflows/` が自動的に認識される。
2. **GitHub Secrets の再設定**: 旧リポジトリに登録したシークレット（AWS/Azure/GCP 認証情報）を新リポジトリにも登録する。
3. **`pulumi config` のスタック名確認**: Pulumi スタックは Pulumi Cloud 上に保存されているため gitルートと無関係だが、`Pulumi.yaml` の `name:` や `backend:` が正しいことを確認する。
4. **VS Code で新ルートを開く**: `code /path/to/multicloud-auto-deploy` または devcontainer で開く。`.devcontainer/` は既に正しい相対パスを使用している。
5. **旧 `ashnova/` リポジトリのアーカイブ**: 移行完了後、旧リポジトリを GitHub 上で `Archived` に設定する。

---

## 前のセクション / 次のセクション

← [10 — Remaining Tasks](AI_AGENT_10_TASKS.md)
