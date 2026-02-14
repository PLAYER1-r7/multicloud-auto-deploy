# Python Full Stack Migration Guide

## 🎯 移行の目的

TerraformとTypeScript/Reactから、完全Python実装（Pulumi + FastAPI + Reflex）への移行。

### 目的
1. **技術スタックの統一** - Python一つでIaC、Backend、Frontendを管理
2. **開発効率の向上** - 型システムの統一、言語切り替えの削減
3. **メンテナンス性向上** - 単一言語での一貫した開発体験

## 📊 移行マップ

### Before (v1.0 - Terraform版)
```
Infrastructure: Terraform (HCL)
Backend: Python (FastAPI) → Lambda関数
Frontend: React + TypeScript + Vite
CI/CD: GitHub Actions → Terraform
```

### After (v2.0 - Pulumi完全Python版)
```
Infrastructure: Pulumi (Python) 🆕
Backend: Python (FastAPI) ✅ 維持
Frontend: Python (Reflex) 🆕
CI/CD: GitHub Actions → Pulumi 🆕
```

## 🏗️ 新しいアーキテクチャ

### AWS
```
Pulumi (Python)
├── Lambda Function (FastAPI)
├── API Gateway (HTTP API)
├── DynamoDB (Messages)
├── S3 (Images)
└── CloudFront (optional)
```

### Azure
```
Pulumi (Python)
├── Container Apps (FastAPI)
├── Cosmos DB (Messages)
├── Blob Storage (Images)
└── Front Door (optional)  
```

### GCP
```
Pulumi (Python)
├── Cloud Run (FastAPI)
├── Firestore (Messages)
├── Cloud Storage (Images)
└── Cloud CDN (optional)
```

### Frontend (共通)
```
Reflex (Python)
├── State Management
├── UI Components
├── API Client (httpx)
└── Static Export
```

## 📁 新しいディレクトリ構造

```
multicloud-auto-deploy/
├── infrastructure/
│   └── pulumi/
│       ├── aws/simple-sns/      # AWS Pulumi IaC
│       ├── azure/simple-sns/    # Azure Pulumi IaC
│       └── gcp/simple-sns/      # GCP Pulumi IaC
├── services/
│   ├── api/                     # FastAPI Backend
│   │   ├── app/
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── README.md
│   └── web/                     # Reflex Frontend
│       ├── simple_sns_web.py
│       ├── requirements.txt
│       ├── Dockerfile
│       └── README.md
├── .github/workflows/           # CI/CD (Pulumi版)
├── docker-compose.yml           # ローカル開発環境
└── README.md
```

## 🚀 段階的移行手順

### Phase 1: ローカル開発環境構築 ✅ 完了
- [x] FastAPI実装作成
- [x] Reflex実装作成
- [x] docker-compose.yml更新
- [x] MinIO統合

### Phase 2: AWS Pulumi実装 🟡 進行中
- [x] Pulumi AWS IaCコード作成
- [ ] Lambda関数デプロイテスト
- [ ] API Gateway設定
- [ ] CI/CDワークフロー更新

### Phase 3: Azure/GCP Pulumi実装 ⏳ 未着手
- [ ] Azure Container Apps Pulumiコード
- [ ] GCP Cloud Run Pulumiコード
- [ ] CI/CDワークフロー更新

### Phase 4: 本番移行 ⏳ 未着手
- [ ] Terraform state → Pulumi移行
- [ ] 既存リソースのimport
- [ ] Blue-Greenデプロイ
- [ ] 動作検証

## 🧪 ローカル開発

### 新Python版の起動

```bash
# すべてのサービスを起動
docker-compose up api web minio

# APIのみ
docker-compose up api minio

# Webのみ
docker-compose up web
```

**アクセス先:**
- FastAPI: http://localhost:8000/docs
- Reflex Web: http://localhost:3000
- MinIO Console: http://localhost:9001

### 旧版との比較テスト

```bash
# 旧版（React/TypeScript）
docker-compose up frontend backend

# 新版（Python）
docker-compose up web api minio
```

**ポート:**
- 旧Frontend: http://localhost:3001
- 新Web: http://localhost:3000
- 旧Backend: http://localhost:8080
- 新API: http://localhost:8000

## 🔄 Terraform → Pulumi 移行

### 既存リソースのインポート

```bash
cd infrastructure/pulumi/aws/simple-sns

# Pulumiスタック作成
pulumi stack init migration

# 既存リソースをインポート
pulumi import aws:dynamodb/table:Table messages-table simple-sns-messages-staging
pulumi import aws:s3/bucketV2:BucketV2 images-bucket simple-sns-images-staging
pulumi import aws:lambda/function:Function api-lambda simple-sns-api-staging
```

### 段階的移行戦略

1. **新環境作成** (推奨)
   - Pulumiで新しいスタック作成
   - 並行運用でテスト
   - DNS切り替えで移行

2. **インプレース移行** (リスク高)
   - 既存リソースをPulumiにインポート
   - Terraformを段階的に削除

## 🎨 Reflex vs React 比較

### React/TypeScript (旧)
```typescript
const MessageList: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  
  useEffect(() => {
    fetchMessages().then(setMessages);
  }, []);
  
  return (
    <div>
      {messages.map(msg => (
        <MessageCard key={msg.id} message={msg} />
      ))}
    </div>
  );
};
```

### Reflex (新)
```python
class State(rx.State):
    messages: List[Message] = []
    
    async def load_messages(self):
        self.messages = await fetch_messages()

def message_list() -> rx.Component:
    return rx.vstack(
        rx.foreach(
            State.messages,
            message_card,
        )
    )
```

**利点:**
- ✅ 型ヒント（Pydantic）
- ✅ 非同期処理（async/await）
- ✅ 状態管理がシンプル
- ✅ JavaScriptビルド不要

## 📈 進捗状況

### 完了 ✅
- FastAPI Backend実装
- Reflex Frontend実装
- AWS Pulumi IaC (基本)
- docker-compose統合
- ローカル開発環境

### 進行中 🟡
- AWS Pulumi IaC (詳細)
- CI/CDワークフロー更新

### 未着手 ⏳
- Azure Pulumi IaC
- GCP Pulumi IaC
- Terraform state移行
- 本番デプロイ

## 🔗 参考リンク

- [Pulumi Documentation](https://www.pulumi.com/docs/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Reflex](https://reflex.dev/)
- [Terraform → Pulumi Migration](https://www.pulumi.com/docs/using-pulumi/adopting-pulumi/migrating-to-pulumi/)

## 📞 問い合わせ

移行に関する質問や問題は、GitHub Issuesで報告してください。
