# Ashnova v3 セットアップガイド

## 🎯 Dev Container リビルド後の確認手順

### 1. Docker が利用可能か確認

```bash
docker --version
docker compose version
```

### 2. v3ディレクトリに移動

```bash
cd /workspaces/ashnova/ashnova.v3
```

### 3. ローカルインフラを起動

```bash
# PostgreSQL と MinIO を起動
docker compose up -d

# 起動確認
docker compose ps

# ログ確認
docker compose logs -f
```

### 4. データベース接続確認

```bash
# PostgreSQLにログイン
docker exec -it simplesns-postgres psql -U simplesns -d simplesns

# テーブル確認
\dt

# サンプルデータ確認
SELECT * FROM posts;
SELECT * FROM profiles;

# 終了
\q
```

### 5. MinIO 確認

```bash
# MinIO Console にアクセス
# ブラウザで: http://localhost:9001
# Username: minioadmin
# Password: minioadmin

# または CLI で確認
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local
mc ls local/images
```

### 6. Python API 起動

```bash
cd services/api

# 仮想環境が作成されているか確認
ls -la .venv

# アクティベート
source .venv/bin/activate

# 依存関係確認
pip list | grep fastapi
pip list | grep sqlalchemy

# API起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. API 動作確認

別のターミナルで:

```bash
# ヘルスチェック
curl http://localhost:8000/health

# 投稿一覧取得
curl http://localhost:8000/posts

# Swagger UI でAPI確認
# ブラウザで: http://localhost:8000/docs
```

### 8. 簡易テスト

```bash
# 投稿一覧取得（サンプルデータが返ってくるはず）
curl http://localhost:8000/posts | jq

# プロフィール取得
curl http://localhost:8000/profile/test-user-1 | jq

# 投稿作成テスト（認証無効モード）
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello from v3!",
    "isMarkdown": false,
    "tags": ["test", "v3"]
  }' | jq
```

## 🐛 トラブルシューティング

### Dockerが起動しない場合

```bash
# Docker サービス確認
sudo service docker status

# 必要に応じて起動
sudo service docker start
```

### ポートが使用中の場合

```bash
# ポート確認
sudo lsof -i :8000
sudo lsof -i :5432
sudo lsof -i :9000

# docker-compose.yml のポート番号を変更
```

### Python仮想環境が作成されていない場合

```bash
cd /workspaces/ashnova/ashnova.v3/services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### データベース初期化がうまくいかない場合

```bash
# コンテナを完全に削除して再起動
docker compose down -v
docker compose up -d
```

## ✅ セットアップ完了チェックリスト

- [ ] Docker が動作している
- [ ] PostgreSQL コンテナが起動している
- [ ] MinIO コンテナが起動している
- [ ] Python 仮想環境がアクティベートできる
- [ ] API が起動する
- [ ] `/health` エンドポイントが 200 を返す
- [ ] `/posts` エンドポイントがサンプルデータを返す
- [ ] Swagger UI が表示される

すべてチェックできたら、次のステップ（Pulumiスタック作成）に進めます！
