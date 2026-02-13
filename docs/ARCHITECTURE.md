# アーキテクチャ

Multi-Cloud Auto Deploy Platform のシステムアーキテクチャを説明します。

## システム概要

```
┌────────────────────────────────────────────────────────────┐
│                      ユーザー                                │
└──────────────────────┬─────────────────────────────────────┘
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
┌─────────┐      ┌─────────┐      ┌─────────┐
│   AWS   │      │  Azure  │      │   GCP   │
└────┬────┘      └────┬────┘      └────┬────┘
     │                │                 │
     └────────────────┴─────────────────┘
                      │
              ┌───────┴────────┐
              │ Application    │
              │ (Frontend +    │
              │  Backend + DB) │
              └────────────────┘
```

## フロントエンド

### 技術スタック

- **React 18**: UIライブラリ
- **TypeScript**: 型安全性
- **Vite**: ビルドツール
- **Tailwind CSS**: スタイリング
- **Axios**: HTTP クライアント

### デプロイ先

| クラウド | サービス | URL形式 |
|---------|---------|---------|
| AWS | S3 + CloudFront | `https://xxx.cloudfront.net` |
| Azure | Static Web Apps | `https://xxx.azurestaticapps.net` |
| GCP | Cloud Storage + CDN | `https://storage.googleapis.com/xxx` |

## バックエンド

### 技術スタック

- **FastAPI**: Pythonウェブフレームワーク
- **Python 3.11**: ランタイム
- **Pydantic**: データバリデーション
- **Uvicorn**: ASGI サーバー

### API エンドポイント

```
GET  /                     - ルート
GET  /api/health          - ヘルスチェック
GET  /api/messages        - メッセージ一覧
POST /api/messages        - メッセージ作成
GET  /api/messages/{id}   - メッセージ取得
DELETE /api/messages/{id} - メッセージ削除
```

### デプロイ先

| クラウド | サービス | 特徴 |
|---------|---------|------|
| AWS | Lambda + API Gateway | サーバーレス、オートスケール |
| Azure | Azure Functions | サーバーレス、統合認証 |
| GCP | Cloud Functions/Run | サーバーレス、コンテナ対応 |

## データベース

### 選択肢

| クラウド | サービス | タイプ | 用途 |
|---------|---------|-------|------|
| AWS | DynamoDB | NoSQL | 高速、スケーラブル |
| AWS | RDS (PostgreSQL) | SQL | リレーショナル |
| Azure | Cosmos DB | NoSQL | グローバル分散 |
| Azure | Azure SQL | SQL | エンタープライズ |
| GCP | Firestore | NoSQL | リアルタイム |
| GCP | Cloud SQL | SQL | マネージド |

## CI/CD パイプライン

```
┌─────────────┐
│   GitHub    │
│ Repository  │
└──────┬──────┘
       │ Push/PR
┌──────▼───────────┐
│ GitHub Actions   │
├──────────────────┤
│ 1. Checkout      │
│ 2. Build         │
│ 3. Test          │
│ 4. Package       │
└──────┬───────────┘
       │
   ┌───┴───┬───────┬───────┐
   ▼       ▼       ▼       ▼
┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐
│ AWS │ │Azure│ │ GCP │ │Local │
└─────┘ └─────┘ └─────┘ └──────┘
```

### ワークフロー

1. **Trigger**: Push to main or Manual
2. **Build**: 
   - Frontend: `npm run build`
   - Backend: `pip install` + `zip`
3. **Test**: 
   - Frontend: `vitest`
   - Backend: `pytest`
4. **Deploy Infrastructure**: Terraform/Pulumi
5. **Deploy Application**: 
   - Frontend → S3/Storage
   - Backend → Lambda/Functions
6. **Notify**: Success/Failure

## Infrastructure as Code

### Terraform

```hcl
# 構造
infrastructure/terraform/
├── aws/
│   ├── main.tf        # プロバイダー設定
│   ├── frontend.tf    # S3 + CloudFront
│   ├── backend.tf     # Lambda + API Gateway
│   ├── database.tf    # DynamoDB
│   ├── variables.tf   # 変数定義
│   └── outputs.tf     # 出力値
├── azure/
└── gcp/
```

### Pulumi

```python
# Python SDKによるインフラ定義
import pulumi
import pulumi_aws as aws

bucket = aws.s3.Bucket("frontend",
    website={
        "index_document": "index.html"
    })
```

## セキュリティ

### 認証・認可

- **AWS**: Cognito
- **Azure**: Azure AD B2C
- **GCP**: Firebase Auth

### ネットワーク

- HTTPS強制
- CORS設定
- APIキー（オプション）

### シークレット管理

- **AWS**: Secrets Manager / Parameter Store
- **Azure**: Key Vault
- **GCP**: Secret Manager

## スケーリング

### 水平スケーリング

| サービス | 自動スケール | 最大 |
|---------|-------------|------|
| Lambda | あり | 1000 並列 |
| Azure Functions | あり | 200 インスタンス |
| Cloud Functions | あり | 設定可能 |

### データベーススケーリング

- **DynamoDB**: オンデマンド課金
- **Cosmos DB**: RU/s 自動スケール
- **Firestore**: 自動

## モニタリング

### メトリクス

- リクエスト数
- レスポンスタイム
- エラー率
- コスト

### ログ

- **AWS**: CloudWatch Logs
- **Azure**: Application Insights
- **GCP**: Cloud Logging

### アラート

- エラー閾値超過
- レイテンシ増加
- コスト異常

## ディザスタリカバリ

### バックアップ

- データベーススナップショット
- S3バージョニング
- マルチリージョン対応

### RTO/RPO

- **RTO** (Recovery Time Objective): < 1時間
- **RPO** (Recovery Point Objective): < 5分

## パフォーマンス最適化

### フロントエンド

- Code Splitting
- Lazy Loading
- CDNキャッシング
- 画像最適化

### バックエンド

- コネクションプーリング
- キャッシング (Redis)
- 非同期処理
- バッチ処理

## コスト最適化

### 戦略

1. **サーバーレス優先**: 使用量課金
2. **オートスケール**: 需要に応じて調整
3. **リザーブドインスタンス**: 予測可能な負荷
4. **ストレージクラス**: ライフサイクルポリシー

### コスト比較（月額概算、小規模）

| クラウド | フロントエンド | バックエンド | DB | 合計 |
|---------|--------------|-------------|----|----|
| AWS | $2 | $1 | $1 | $4 |
| Azure | $0* | $1 | $1 | $2 |
| GCP | $1 | $1 | $1 | $3 |

*Azure Static Web Appsの無料枠

## 今後の拡張

- Kubernetes対応
- マルチリージョンデプロイ
- Blue-Greenデプロイ
- A/Bテスト機能
- メトリクスダッシュボード
