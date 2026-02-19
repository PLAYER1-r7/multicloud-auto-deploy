# 道の駅 Web App — セットアップガイド

> **対象**: `multicloud-auto-deploy` プロジェクトへの道の駅機能追加

---

## アーキテクチャ概要

```
[GitHub Actions] ──毎月1日──▶ [scraper.py] ──JSONL──▶ [ADLS Gen2 Bronze Layer]
                                                              │
                                                 [Databricks Notebooks]
                                                   01_bronze_ingest
                                                   02_silver_transform
                                                   03_gold_aggregate
                                                              │
                                                   [Delta Lake Gold Table]
                                                              │
                                                [FastAPI /api/michinoeki/*]
                                                              │
                                               [React MichinoekiPage.tsx]
```

---

## ファイル構成

```
multicloud-auto-deploy/
├── services/
│   ├── michinoeki-scraper/
│   │   ├── scraper.py          # 公式サイトスクレイパー (全国 1,200+ 駅)
│   │   └── requirements.txt
│   ├── api/app/routes/
│   │   └── michinoeki.py       # FastAPI ルーター (/api/michinoeki/*)
│   └── frontend_react/src/
│       ├── api/michinoeki.ts   # API クライアント
│       └── components/MichinoekiPage.tsx  # 一覧ページ
├── databricks/notebooks/
│   ├── 01_bronze_ingest.py     # Bronze Layer (JSONL → Delta)
│   ├── 02_silver_transform.py  # Silver Layer (クレンジング・正規化)
│   └── 03_gold_aggregate.py    # Gold Layer (API 配信用集約)
└── .github/workflows/
    └── update-michinoeki-data.yml  # 月次自動更新ワークフロー
```

---

## セットアップ手順

### 1. Azure リソース準備

```bash
# ADLS Gen2 (Hierarchical Namespace 有効) ストレージアカウント作成
az storage account create \
  --name <ADLS_ACCOUNT_NAME> \
  --resource-group multicloud-auto-deploy-staging-rg \
  --location japaneast \
  --sku Standard_LRS \
  --enable-hierarchical-namespace true

# bronze コンテナ作成
az storage fs create \
  --name bronze \
  --account-name <ADLS_ACCOUNT_NAME>
```

### 2. Databricks ワークスペース準備

1. Azure Portal で Azure Databricks ワークスペースを作成
2. `databricks/notebooks/` 配下の 3 つのノートブックをワークスペースへインポート
3. 各ノートブックを個別の **Databricks Job** として登録し、Job ID を控える

### 3. GitHub Secrets 設定

| Secret 名               | 説明                                   |
| ----------------------- | -------------------------------------- |
| `ADLS_ACCOUNT_NAME`     | ADLS Gen2 ストレージアカウント名       |
| `ADLS_STORAGE_KEY`      | ストレージアカウントキー               |
| `DATABRICKS_HOST`       | `https://adb-xxxx.azuredatabricks.net` |
| `DATABRICKS_TOKEN`      | Databricks Personal Access Token       |
| `DATABRICKS_JOB_BRONZE` | Job 01 の Job ID                       |
| `DATABRICKS_JOB_SILVER` | Job 02 の Job ID                       |
| `DATABRICKS_JOB_GOLD`   | Job 03 の Job ID                       |
| `AZURE_API_URL`         | Azure Functions API の URL             |

### 4. API 環境変数設定

Azure Functions の Application Settings に追加:

```
DATABRICKS_HOST       = https://adb-xxxx.azuredatabricks.net
DATABRICKS_HTTP_PATH  = /sql/1.0/warehouses/xxxx
DATABRICKS_TOKEN      = <PAT>
MICHINOEKI_CATALOG    = hive_metastore
MICHINOEKI_DATABASE   = michinoeki
```

### 5. ローカル開発 (フォールバックモード)

Databricks 未接続でも、スクレイパーで生成した JSONL があればローカル動作:

```bash
# スクレイプ (テスト: 北海道のみ)
cd services/michinoeki-scraper
pip install -r requirements.txt
python scraper.py --prefs 10 --output michinoeki_raw.jsonl

# API 起動 (JSONL をフォールバック読み込み)
cd ../api
uvicorn app.main:app --reload
# → http://localhost:8000/docs
# → http://localhost:8000/api/michinoeki/stations
```

---

## API エンドポイント

| Method | Path                            | 説明                                  |
| ------ | ------------------------------- | ------------------------------------- |
| GET    | `/api/michinoeki/stations`      | 一覧 (ページネーション・フィルタ対応) |
| GET    | `/api/michinoeki/stations/{id}` | 個別詳細                              |
| GET    | `/api/michinoeki/prefectures`   | 都道府県別集計                        |

### クエリパラメータ (stations)

| パラメータ   | 型  | デフォルト | 説明                 |
| ------------ | --- | ---------- | -------------------- |
| `page`       | int | 1          | ページ番号           |
| `page_size`  | int | 50         | 件数 (最大200)       |
| `prefecture` | str |            | 都道府県名でフィルタ |
| `keyword`    | str |            | 駅名・住所の部分一致 |

---

## 自動更新スケジュール

`update-michinoeki-data.yml` が **毎月1日 00:00 JST** に自動実行:

```
[スクレイピング] → [ADLS Gen2 Bronze] → [Databricks Pipeline] → [API ヘルスチェック]
```

手動実行時は `workflow_dispatch` から都道府県指定・Databricks スキップが可能。

---

## データ出典

- **道の駅公式サイト**: https://www.michi-no-eki.jp/
- 利用規約: https://www.michi-no-eki.jp/about/term
- 商業利用前に利用規約を必ず確認してください。
