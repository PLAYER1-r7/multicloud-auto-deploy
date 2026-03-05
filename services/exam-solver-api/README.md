# Exam Solver API (FastAPI)

大学入試解答サポートサービス - OCR・AI解答の独立マイクロサービス

**Status**: Ready for deployment (Workflow trigger)

## 🎯 特徴

- **FastAPI** - 高速で型安全なPythonフレームワーク
- **マルチクラウド対応** - AWS Lambda / Azure Functions / GCP Cloud Functions
- **OCR + AI** - Azure Document Intelligence + OpenAI / GCP Vision + Gemini
- **クラウド分離** - SNS API と完全に独立したマイクロサービス
- **自動API文書** - OpenAPI (Swagger UI / ReDoc)

## 🚀 クイックスタート

### ローカル開発

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数設定（Solve を有効化）
export SOLVE_ENABLED=true
export CLOUD_PROVIDER=azure  # or gcp
export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
export AZURE_OPENAI_ENDPOINT=...

# 開発サーバー起動
uvicorn app.main:app --reload

# API文書
open http://localhost:8000/docs
```

### Docker使用

```bash
docker build -t exam-solver-api .
docker run -p 8000:8000 \
  -e CLOUD_PROVIDER=azure \
  -e SOLVE_ENABLED=true \
  exam-solver-api
```

## 📁 プロジェクト構造

```
services/exam-solver-api/  ← 大学入試解答サービス（新規）
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPIアプリケーション（/v1/solve のみ）
│   ├── config.py        # 設定管理（Solve 関連のみ）
│   ├── models.py        # SolveRequest/SolveResponse モデル
│   ├── routes/
│   │   ├── solve.py     # POST /v1/solve エンドポイント
│   │   └── learning.py  # 学習支援エンドポイント
│   ├── services/
│   │   ├── base_math_solver.py
│   │   ├── azure_math_solver.py
│   │   ├── gcp_math_solver.py
│   │   └── material_generator.py
│   └── backends/        # (認証用に保持)
├── index.py             # AWS Lambda ハンドラー
├── function_app.py      # Azure Functions ハンドラー
├── function.py          # GCP Cloud Functions ハンドラー
├── requirements.txt
├── requirements-aws.txt
├── requirements-azure.txt
├── requirements-gcp.txt
└── tests/
    ├── conftest.py
    └── test_*.py
```

## 📋 API エンドポイント

| メソッド | エンドポイント           | 説明                       |
| -------- | ------------------------ | -------------------------- |
| `POST`   | `/v1/solve`              | 数学問題を OCR + AI で解答 |
| `GET`    | `/v1/ocr-debug?limit=20` | OCR デバッグログを取得     |
| `GET`    | `/health`                | ヘルスチェック             |

## ⚙️ 環境変数

### Solve オプション

```bash
SOLVE_ENABLED=true                    # エンドポイント有効化（デフォルト false）
CLOUD_PROVIDER=azure                  # または gcp
```

### Azure 設定

```bash
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_STORAGE_ACCOUNT_NAME=...
AZURE_STORAGE_ACCOUNT_KEY=...
```

### GCP 設定

```bash
GCP_PROJECT_ID=...
GCP_VERTEX_AI_LOCATION=asia-northeast1
GCP_VERTEX_AI_MODEL=gemini-2.0-flash
```

## 🚢 デプロイメント

### AWS Lambda

```bash
# ワークフロー: .github/workflows/deploy-exam-solver-aws.yml
git push origin develop  # staging 自動デプロイ
git push origin main     # production 自動デプロイ
```

### Azure Functions

```bash
# ワークフロー: .github/workflows/deploy-exam-solver-azure.yml
git push origin develop  # staging 自動デプロイ
git push origin main     # production 自動デプロイ
```

### GCP Cloud Functions

```bash
# ワークフロー: .github/workflows/deploy-exam-solver-gcp.yml
git push origin develop  # staging 自動デプロイ
git push origin main     # production 自動デプロイ
```

## 🧪 テスト実行

```bash
# 全テスト
pytest tests/ -v

# カバレッジ測定
pytest tests/ --cov=app --cov-report=html

# 特定テストのみ
pytest tests/test_api_endpoints.py -v
```

## 📚 参考資料

- [AI_AGENT_12_OCR_MATH_JA.md](../../docs/AI_AGENT_12_OCR_MATH_JA.md) - OCR・数式解答サービス仕様
- [EXAM_SOLVER_MAINTENANCE_PLAN.md](../../EXAM_SOLVER_MAINTENANCE_PLAN.md) - メンテナンス計画
- [FastAPI ドキュメント](https://fastapi.tiangolo.com/)

## 🔗 関連サービス

- **SNS API** - `services/sns-api/` - メッセージング機能
- **Frontend React** - `services/frontend_react/` - React SPA UI
