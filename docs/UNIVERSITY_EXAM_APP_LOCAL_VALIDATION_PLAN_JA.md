# 大学入試解答アプリ再検討（ローカル検証ファースト）

## 目的

大学入試解答アプリは、まず **検証速度** と **原因切り分け** を優先し、
以下の構成で進める。

- フロントエンド: ローカル起動
- バックエンド: ローカル起動（FastAPI / uvicorn）
- 外部依存: バックエンドから必要なクラウドサービス（Azure/GCP 等）を直接呼ぶ
- サーバーレス化（Function化）は、検証完了後に段階的に移行

---

## docs と現行コードの確認結果（重要）

### 1) フロントエンド構成

- docs 上は `services/frontend_react`（React SPA）を主経路として扱っている
- `services/frontend_web` はレガシー経路が混在しており、検証フェーズでは主経路にしない方が安全

### 2) OCR/数式（大学入試解答）機能

- docs (`AI_AGENT_12_OCR_MATH_JA.md`) では Azure/GCP の本実装（OCR + LLM）を説明
- 現行コードの `services/api/app/routes/solve.py` は **Azure OCR (Document Intelligence) + Azure OpenAI** を呼ぶ実装に更新済み
- 設定未投入時は 503 を返すため、検証時は `SOLVE_ENABLED=true` と Azure系キー投入が必須

### 3) ローカルでクラウド呼び出しする前提

- backend 切替は `CLOUD_PROVIDER`（`local | aws | azure | gcp`）で可能
- Azure backend は `COSMOS_DB_ENDPOINT` / `COSMOS_DB_KEY` などが必要
- GCP backend は `GCP_PROJECT_ID` / `GCP_SERVICE_ACCOUNT` / `GCP_STORAGE_BUCKET` などが必要

---

## 検証フェーズの推奨アーキテクチャ

## Phase A: ベースライン（完全ローカル）

目的: 画面・API・投稿CRUD・アップロード導線の安定確認

- `docker compose up -d minio dynamodb-local minio-setup`
- backend: `CLOUD_PROVIDER=local` で `uvicorn app.main:app --reload`
- frontend: `services/frontend_react` を `npm run dev`

## Phase B: クラウド接続検証（バックエンドのみクラウド接続）

目的: ローカル実行のまま、クラウドデータ基盤/OCR基盤との接続検証

- backend は引き続きローカル実行
- `CLOUD_PROVIDER=azure` または `CLOUD_PROVIDER=gcp` に変更
- 必要なクラウド環境変数のみ追加
- frontend はそのままローカル

この段階で、以下を切り分け可能:

- フロントの不具合か
- APIロジックの不具合か
- クラウド接続/資格情報の不具合か

## Phase C: Solve 機能の実装検証

目的: 大学入試解答（OCR + LLM）の本体検証

- まず既存の Azure 経路（OCR→LLM）で `mode=fast` を安定化
- 次に `mode=accurate`（複数OCR候補 + マージ + 評価）を段階追加
- `debugOcr=true` で品質比較ログを収集

---

## ローカル検証の実行手順（最小）

## 1. API 設定

`services/api/.env` を `services/api/.env.example` から作成し、
検証対象クラウドに合わせて以下を設定:

- `CLOUD_PROVIDER`
- Azure 利用時: `COSMOS_DB_*`, `AZURE_STORAGE_*`
- GCP 利用時: `GCP_*`
- Solve 検証時: `SOLVE_ENABLED=true` と OCR/LLM キー

## 2. backend 起動

```bash
cd /workspaces/multicloud-auto-deploy/services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3. frontend 起動（React）

```bash
cd /workspaces/multicloud-auto-deploy/services/frontend_react
npm install
npm run dev -- --host 0.0.0.0 --port 3001
```

- `vite.config.ts` の proxy で `localhost:8000` を参照

---

## Function化へ進む判断基準（Go/No-Go）

以下を満たしたら Function 化を開始する。

1. ローカル + クラウド接続で `/health`, `/posts`, `/uploads` が安定
2. `/v1/solve` がダミーでなく実装として成立（最低 fast モード）
3. エラー時の観測（ログ、リクエストID、失敗理由）が揃っている
4. 再現手順がドキュメント化済み

---

## Function化の段階移行（推奨順）

1. **APIのみ Function化**
   - frontend はローカルまたは静的配信のまま
   - API 実行環境差分（タイムアウト、認証、CORS）だけを先に吸収

2. **Solve の重処理を分離**
   - API で同期応答が重い場合、ジョブ化または非同期化を検討

3. **フロント配信最適化**
   - CDN キャッシュ・rewrite・セキュリティヘッダを最終調整

---

## 直近の実装タスク（優先順）

1. `services/api/.env` のクラウド検証プロファイル作成（azure/gcp）
2. 検証スクリプトに `solve` 系スモークを追加
3. `mode=accurate` / OCRマージの品質改善
4. その後に Function 化 PoC を開始

---

最終更新: 2026-03-03
