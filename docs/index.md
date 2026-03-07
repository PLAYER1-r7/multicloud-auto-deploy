# multicloud-auto-deploy Documentation

> 🌐 **Multi-Cloud Auto Deploy Platform**
> AWS / Azure / GCP 対応のフルスタックアプリケーション自動デプロイプラットフォーム

---

## 🎯 プロジェクト概要

**multicloud-auto-deploy** は、SNS スタイルの投稿アプリケーションを3つのクラウドプロバイダー（AWS、Azure、GCP）に同時にデプロイするプラットフォームです。

### ✨ 主な特徴

- ✅ **マルチクラウド対応**: AWS / Azure / GCP で同一アプリケーション実行
- ✅ **フルスタック**: React フロントエンド + FastAPI バックエンド + クラウド DB
- ✅ **Infrastructure as Code**: Pulumi による IaC 管理
- ✅ **完全自動化**: GitHub Actions による CI/CD パイプライン
- ✅ **セキュリティ**: CORS、HTTPS、IAM、暗号化を本番反映
- ✅ **カスタムドメイン**: 全クラウドで ashnova.jp ドメイン対応

---

## 🚀 クイックスタート

### 前提条件

- Python 3.12+
- Docker & Docker Compose
- Pulumi 3.0+
- AWS CLI 2.x / Azure CLI 2.x / gcloud CLI

### セットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/PLAYER1-r7/multicloud-auto-deploy.git
cd multicloud-auto-deploy

# 2. Python 仮想環境を構築
python3 -m venv .venv
source .venv/bin/activate

# 3. 依存関係をインストール
pip install -r requirements.txt

# 4. ローカルセットアップ
make setup-local

# 5. 開発サーバーを起動
make dev
```

詳細は [Getting Started ガイド](getting-started/overview.md) を参照。

---

## 📊 現在のステータス

### ✅ 完了フェーズ

| フェーズ     | 内容                               | 状態    |
| ------------ | ---------------------------------- | ------- |
| **Phase 1**  | 教材生成パイプライン               | ✅ 完了 |
| **Phase 2**  | Bedrock / Polly / Personalize 統合 | ✅ 完了 |
| **Phase 3**  | React UI & 統合テスト              | ✅ 完了 |
| **Security** | CORS / HTTPS / Audit Logs 本番反映 | ✅ 完了 |

### ⏳ 進行中 / 計画中

| 項目                    | 説明                                    | 優先度      |
| ----------------------- | --------------------------------------- | ----------- |
| Branch Protection Rules | main/develop への直接 push 禁止         | 🔴 Critical |
| 監視とアラート設定      | CloudWatch/Monitor/Logging チューニング | 🟡 High     |
| 負荷テスト              | Locust による性能ベースライン確立       | 🟡 High     |
| GitHub Pages            | ドキュメント自動公開                    | 🟢 Medium   |

詳細は [タスク進捗](tasks.md) を参照。

---

## 🔗 主要リンク

### デモ環境（本番）

| Cloud     | API                                                                                                             | Frontend                                                                      | CMS                                                                                             |
| --------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **AWS**   | [API Gateway](https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com)                                      | [CloudFront](https://d1qob7569mn5nw.cloudfront.net)                           | [S3](http://multicloud-auto-deploy-production-frontend.s3-website-ap-northeast-1.amazonaws.com) |
| **Azure** | [Functions](https://multicloud-auto-deploy-production-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api) | [Front Door](https://mcad-production-diev0w-f9ekdmehb0bga5aw.z01.azurefd.net) | [Blob](https://mcadwebdiev0w.z11.web.core.windows.net)                                          |
| **GCP**   | [Cloud Functions](https://console.cloud.google.com)                                                             | [Cloud CDN](https://www.gcp.ashnova.jp)                                       | [GCS](https://storage.googleapis.com)                                                           |

### プロジェクト管理

- 📋 [GitHub Issues](https://github.com/PLAYER1-r7/multicloud-auto-deploy/issues)
- 🎯 [Milestones](https://github.com/PLAYER1-r7/multicloud-auto-deploy/milestones)
- 📦 [Releases](https://github.com/PLAYER1-r7/multicloud-auto-deploy/releases)
- 📊 [Actions](https://github.com/PLAYER1-r7/multicloud-auto-deploy/actions)

---

## 📚 ドキュメント構成

### 文書の責務分離

- `docs/`: プロダクト仕様・設計・実装・運用（製品そのもの）
- `.github/`: GitHub 上の作業管理・協業・自動化運用

運用文書の入口は [../.github/00_START_HERE.md](../.github/00_START_HERE.md) を参照。

```
docs/
├── getting-started/     # セットアップと基本
│   ├── overview.md      # プロジェクト概要
│   ├── setup.md         # 環境セットアップ
│   └── quickstart.md    # クイックスタート
├── architecture/        # 設計とアーキテクチャ
│   ├── system-design.md # システム設計
│   ├── cloud-architecture.md # クラウド構成
│   └── api-design.md    # API 設計
├── implementation/      # 実装詳細
├── deployment/          # デプロイと環境
├── operations/          # オペレーション
├── reference/           # 技術リファレンス
└── 00_START_HERE.md     # docs の読み順入口
```

---

## 🛠️ 技術スタック

### フロントエンド

- **Framework**: React 18 + Vite + TypeScript
- **UI**: Tailwind CSS + Shadcn/ui
- **状態管理**: Zustand
- **ホスティング**: CloudFront / Front Door / Cloud CDN

### バックエンド

- **Framework**: FastAPI 1.0+
- **認証**: JWT (Cognito / Azure AD / Firebase)
- **ORM**: SQLAlchemy
- **Deploy**: Lambda / Functions / Cloud Run

### インフラストラクチャ

- **IaC**: Pulumi (Python)
- **Database**: DynamoDB / Cosmos DB / Firestore
- **Storage**: S3 / Blob Storage / Cloud Storage
- **CDN**: CloudFront / Front Door / Cloud CDN

### CI/CD

- **Pipeline**: GitHub Actions
- **Build**: Docker + Vite + Pulumi
- **Deploy**: Automated multi-cloud

---

## 📖 さらに詳しく

- [実装ガイド](implementation-guide.md) — ソースコード解説
- [セキュリティ](operations/security.md) — セキュリティ実装
- [API リファレンス](reference/api.md) — エンドポイント仕様
- [GitHub 運用文書の入口](../.github/00_START_HERE.md) — Issue/PR/Projects/運用手順

---

## 🤝 貢献

Pull Request を歓迎します！詳細は [CONTRIBUTING.md](../CONTRIBUTING.md) を参照。

---

## 📝 ライセンス

MIT License — See [LICENSE](../LICENSE)

---

**Last Updated**: 2026-02-28
**Version**: 1.0.110.251
**Status**: ✅ Production
