# 🚀 デプロイメント監視レポート
**生成日時:** 2026-02-28 02:43:00 UTC
**リポジトリ:** PLAYER1-r7/multicloud-auto-deploy
**監視対象:** develop & main ブランチ

---

## 📊 デプロイメント統計

| メトリクス | 値 | 状態 |
|-----------|-----|------|
| 直近20実行 | 20 | ✓ |
| 成功 | 18 | ✓ |
| 失敗 | 2 | ⚠️ |
| 成功率 | 90.0% | 良好 |
| 進行中 | 0 | ✓ |

---

## 🟢 成功したデプロイメント

### 最新実行セット（2026-02-28 02:16:10Z）

#### AWS デプロイ
- ✓ **Deploy to AWS** - 成功 (1m54s)
- ✓ **Deploy Frontend Web (React SPA) to AWS** - 成功 (1m9s)
- コミット: `fix: wrap bare LaTeX steps in aligned env, strengthen step format prompt`

#### Azure デプロイ
- ✓ **Deploy to Azure** - 成功 (9m8s)
- ✓ **Deploy Frontend Web (React SPA) to Azure** - 成功 (20m16s)
- コミット: `fix: wrap bare LaTeX steps in aligned env, strengthen step format prompt`

#### GCP バックエンド
- ✓ **Deploy to GCP** - 成功 (4m36s)
- コミット: `fix: wrap bare LaTeX steps in aligned env, strengthen step format prompt`

#### その他
- ✓ **CodeQL Security Analysis** - 成功 (1m18s)
- ✓ **Version Bump (Push Count) on Push** - 成功 (9s)

---

## 🔴 失敗したデプロイメント

### 1. GCP Frontend Web (React SPA) デプロイ
**Status:** ❌ FAILED
**時刻:** 2026-02-28 02:16:10Z
**実行時間:** 1m3s
**コミット:** `fix: wrap bare LaTeX steps in aligned env, strengthen step format prompt`

#### エラーの詳細
```
ERROR: (gcloud.compute.url-maps.invalidate-cdn-cache) Some requests did not succeed:
 - The resource 'projects/***/global/urlMaps/multicloud-auto-deploy-staging-cdn-urlmap' was not found
```

#### 影響範囲
- GCP Cloud CDN のキャッシュ無効化が失敗
- React SPA ファイルのアップロード: **成功** ✓
- ファイルは GCS に正常に格納されている

#### 根本原因
GCP CloudCDN の `multicloud-auto-deploy-staging-cdn-urlmap` という URL Map が見つからない。
以下の原因が考えられます：
1. URL Map がプロジェクトに存在しない
2. URL Map の名前が変更された
3. プロジェクトID に不一致がある
4. URL Map が削除されている

#### 対応方針
```bash
# URL Map 一覧を確認
gcloud compute url-maps list --project=<PROJECT_ID>

# 該当ワークフローを確認
gh run view <RUN_ID> --log | grep -i "url-map"

# ワークフロー設定ファイルを確認
cat .github/workflows/deploy-gcp.yml | grep -i "urlmap"
```

---

## 📈 ワークフロー別成功率

| ワークフロー | 直近10実行 | 成功率 | 状態 |
|-----------|---------|-------|------|
| Deploy to AWS | 6/10 | 60.0% | ⚠️ 要監視 |
| Deploy to Azure | 8/10 | 80.0% | 良好 |
| Deploy to GCP | 9/10 | 90.0% | 良好 |
| Deploy Frontend Web to AWS | 8/10 | 80.0% | 良好 |
| Deploy Frontend Web to Azure | 8/10 | 80.0% | 良好 |
| Deploy Frontend Web to GCP | 3/10 | 30.0% | ❌ 要対応 |
| CodeQL Analysis | 10/10 | 100% | 優秀 |
| Version Bump | 9/10 | 90.0% | 良好 |

---

## 🔧 推奨アクション

### 優先度1: GCP CDN 設定を修正
1. GCP プロジェクトで URL Map の存在確認
2. `.github/workflows/deploy-gcp.yml` の設定を更新
3. 失敗したワークフロー (22511225224) を再実行

```bash
# ワークフローを再実行
gh run rerun 22511225224 --repo PLAYER1-r7/multicloud-auto-deploy
```

### 優先度2: AWS デプロイ成功率を改善
- Deploy to AWS の成功率が 60% と低い
- 最新の AWS deploy は成功しているため、傾向を監視

### 継続監視
- リアルタイム監視を続行
- 本番環境（main ブランチ）のデプロイを監視
- GCP CDN 設定修正後の再テストを確認

---

## 🎯 本番環境デプロイメント状況

**最新テスト実行:** 2026-02-28 01:55:03Z（develop ブランチ）
- Deploy to AWS: ✓ 成功
- Deploy to Azure: ✓ 成功
- Deploy to GCP: ✓ 成功
- CodeQL: ✓ 成功

**本番環境マージ:** main ブランチへのマージは、develop での全テスト成功を確認してから実行

---

## 📌 モニタリングコマンド

```bash
# リアルタイムモニタリング（develop ブランチ）
bash scripts/watch-deployment.sh develop 10

# リアルタイムモニタリング（main ブランチ）
bash scripts/watch-deployment.sh main 10

# CI/CD パイプライン全体の監視
bash scripts/monitor-cicd.sh

# 失敗した実行の詳細ログ
gh run view 22511225224 --log

# 最新の実行をリアルタイムで監視
gh run watch
```

---

**監視状態:** ✅ アクティブ
**次回更新:** 自動（10分ごと）
