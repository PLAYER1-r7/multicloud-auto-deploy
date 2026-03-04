# 残りのTODOリスト - 優先度順

## 🔴 高優先度（実装推奨 1-2 週間以内）

### T7: Lambda Coldstart | 削減
- ❌ **状態**: 開始保留中（ベースオンデータ収集待ち）
- **開始条件**: 1-2 週間のトラフィック データ蓄積（最小 100 invocations）
- **推奨開始日**: 2026-03-10 〜 2026-03-17
- **推定実装日数**: 5-7 days
- **期待効果**: API レスポンス時間 30-50% 削減

#### 実装ロードマップ
- [ ] CloudWatch Logs から Lambda 実行時間メトリクス抽出
- [ ] Coldstart vs Warm start パターン分析
- [ ] 最適化オプション評価（Provisioned Concurrency, コード最適化）
- [ ] 最適化実装
- [ ] A/B テスト検証
- [ ] デプロイ & モニタリング

**関連ファイル**: `services/api/app/main.py`, `infrastructure/pulumi/aws/__main__.py`

---

## 🟡 中優先度（3-4 週間以内に実装）

### 1. AWS CDN 変更: CloudFront → CloudFlare
- ❌ **状態**: 未実装
- **推定コスト削減**: $50-100/月
- **実装難度**: 🟡 中（DNS 切覆え必要）
- **推定日数**: 10-15 days

#### 実装内容
- [ ] CloudFlare アカウント設定（Free～Pro プラン評価）
- [ ] DNS レコード移行計画
- [ ] CloudFront から CloudFlare へのドメイン 切り替え設計
- [ ] キャッシュルール設定移行
- [ ] WAF ルール移行（AWS WAF v2 → CloudFlare WAF）
- [ ] SSL/TLS 設定確認
- [ ] テストデプロイメント
- [ ] 本番カットオーバー

**コスト試算**:
- CloudFront: $150-200/月
- CloudFlare Pro: $200/月（～または Free: $0）
- **差分**: -$50～-200/月

---

### 2. Azure Application Gateway + WAF 追加
- ❌ **状態**: 未実装
- **推定コスト**: +$25-40/月
- **実装難度**: 🟡 中
- **推定日数**: 7-10 days

#### 実装内容
- [ ] Application Gateway (Standard_v2) AR 作成設定
- [ ] WAF ポリシー定義（OWASP CRS ルール）
- [ ] Backend pool に Azure Functions 設定
- [ ] Health probe 構成
- [ ] HTTP settings（接続タイムアウト等）
- [ ] Rate limiting ルール（10,000 req/5min）
- [ ] Terraform/Pulumi code 作成
- [ ] ステージング環境でのテスト
- [ ] 本番デプロイ

**セキュリティ向上**: WAF + rate limiting サポート

**関連ファイル**: `infrastructure/pulumi/azure/__main__.py`

---

### 3. GCP Cloud CDN キャッシュ以降化
- ❌ **状態**: 部分実装（基本的なキャッシュOnly）
- **推定コスト削減**: $15-25/月
- **実装難度**: 🟡 低～中
- **推定日数**: 3-5 days

#### 実装内容
- [ ] クエリ文字列処理最適化（utm_*, ga_* パラメータ除外）
- [ ] Cookie-based キャッシュ戦略洗練
- [ ] `Cache-Control` ヘッダーカスタマイズ
- [ ] GeoIP ロード分散設定
- [ ] キャッシュヒット率監視ダッシュボード作成
- [ ] A/B テスト検証

**関連ファイル**: `infrastructure/pulumi/gcp/__main__.py`

---

## 🟢 低優先度（1 か月以内に検討）

### 1. テストカバレッジ向上（10% → 60%+）
- ❌ **状態**: 準備完了（COVERAGE_ENHANCEMENT_GUIDE.md 参照）
- **推定実装日数**: 10-15 days
- **テスト対象優先度順**:

#### 高優先度（0% カバレッジ）
- [ ] `services/api/app/jwt_verifier.py` （117 行）
  - 認証トークン検証ロジック
  - AWS Cognito, Google Firebase, Azure AD トークン検証

- [ ] `services/api/app/main.py` （140 行）
  - FastAPI アプリケーション初期化
  - ミドルウェア検証
  - エラーハンドリング

- [ ] `services/api/routes/posts.py` （33 行）
  - POST エンドポイント CRUD 操作

- [ ] `services/api/routes/profile.py` （17 行）
  - プロフィール取得/更新

- [ ] `services/api/routes/uploads.py` （14 行）
  - ファイルアップロード処理

#### 中優先度（12-34% カバレッジ）
- [ ] `services/api/backends/aws_backend.py` （146 行, 15%）
  - Lambda 呼び出し、DynamoDB 操作

- [ ] `services/api/backends/azure_backend.py` （202 行, 14%）
  - Azure Functions 呼び出し、Cosmos DB 操作

- [ ] `services/api/backends/gcp_backend.py` （186 行, 12%）
  - GCP Cloud Functions 呼び出し、Firestore 操作

**実装計画**:
- [ ] pytest フレームワーク拡張
- [ ] Mock オブジェクト作成（AWS SDK, Azure SDK, GCP SDK）
- [ ] ユニットテスト実装
- [ ] 統合テスト実装
- [ ] カバレッジレポート生成
- [ ] CI/CD パイプライン統合

**関連ファイル**: `services/api/tests/` ディレクトリ

---

### 2. 分散トレーシング・観測性強化
- ❌ **状態**: 未実装
- **推定実装日数**: 7-10 days
- **実装難度**: 🟡 中

#### 実装内容
- [ ] OpenTelemetry SDK 統合（Python）
- [ ] Jaeger トレーシングサーバー設定（docker-compose）
- [ ] Lambda → API → Firestore のリクエスト追跡
- [ ] Span attribute 定義（user_id, request_id等）
- [ ] グレースフル シャットダウン（flush traces）
- [ ] ダッシュボード構築（Jaeger UI）
- [ ] CloudWatch Insights より詳細な分析可能に

**メリット**:
- マイクロサービス間のレイテンシー可視化
- 問題点の特定が容易に

**関連ファイル**: `services/api/app/main.py`, `infrastructure/docker-compose.yml`

---

### 3. GitHub Actions CI/CD パイプライン拡張
- ❌ **状態**: 部分実装
- **推定実装日数**: 5-7 days

#### 実装内容
- [ ] Pull Request 自動テストランナー（pytest, coverage）
- [ ] コード品質分析（pylint, flake8, mypy）
- [ ] セキュリティスキャン（Trivy for Docker images）
- [ ] 自動デプロイメント approval workflow
- [ ] ロールバック自動化
- [ ] デプロイメント成功通知（Slack）

**関連ファイル**: `.github/workflows/deploy-*.yml`

---

### 4. 多言語ドキュメント生成
- ❌ **状態**: 未実装
- **推定実装日数**: 3-5 days

#### 対象言語
- [ ] 日本語（現在地）
- [ ] 英語
- [ ] 中国簡体字

**自動化**: GitHub Actions で `docs/` をビルド & 公開

---

## 🔵 オプション（長期タスク）

### 1. マルチクラウド コスト最適化
- ❌ **状態**: 継続的なタスク
- **推定年間コスト削減可能額**: $500-1000

#### 検討項目
- [ ] Reserved Instance または Savings Plans 購入（AWS）
- [ ] Azure Hybrid Benefit 活用（Licenseライセンス既有の場合）
- [ ] GCP Committed Use Discounts 申請
- [ ] 不要なリソース定期クリーンアップ

---

### 2. マルチクラウド 災害復旧（DR）戦略
- ❌ **状態**: 設計段階
- **推定実装日数**: 20-30 days

#### 実装内容
- [ ] Backup ストレージ戦略（クロスリージョン）
- [ ] Failover 自動化スクリプト
- [ ] RTO/RPO 定義 & 検証
- [ ] DR テスト実施（四半期 1 回）

---

## 📊 タスク進捗サマリー

| カテゴリ | タスク | 状態 | 優先度 | 日数 |
|---------|--------|------|--------|------|
| **実装完了** | S1, S2, 0b, 0d, T8, T9, T10 | ✅ | - | - |
| **高優先度** | T7: Lambda Coldstart削減 | ❌ | 🔴 | 5-7d |
| **中優先度** | AWS CDN 最適化 | ❌ | 🟡 | 10-15d |
| **中優先度** | Azure WAF 追加 | ❌ | 🟡 | 7-10d |
| **中優先度** | GCP キャッシュ最適化 | ❌ | 🟡 | 3-5d |
| **低優先度** | テストカバレッジ向上 | ❌ | 🟢 | 10-15d |
| **低優先度** | 分散トレーシング | ❌ | 🟢 | 7-10d |
| **低優先度** | CI/CD 拡張 | ❌ | 🟢 | 5-7d |
| **低優先度** | ドキュメント多言語化 | ❌ | 🟢 | 3-5d |
| **オプション** | コスト最適化 | ❌ | 🔵 | 継続 |
| **オプション** | DR 戦略 | ❌ | 🔵 | 20-30d |

---

## 推奨実装スケジュール

```
Week 1 (2026-03-03 - 2026-03-09):  [セッション完了]
└─ ✅ S1, S2, 0b, 0d, T8, T9, T10 完了

Week 2 (2026-03-10 - 2026-03-16):  [T7 開始準備 + 中優先度タスク開始]
├─ T7 ベースラインメトリクス収集開始
├─ Azure WAF 設計開始
└─ GCP キャッシュ最適化 実装開始

Week 3 (2026-03-17 - 2026-03-23):  [T7 本実装 + Medium priority並列実行]
├─ T7: Lambda Coldstart削減実装
├─ AWS CDN CloudFlare 評価開始
└─ テストカバレッジ向上 関数選定

Week 4+ (2026-03-24+):  [長期タスク実装]
├─ 高難度タスク（CloudFlare 移行、テスト拡張）
└─ オプショナルタスク（分散トレーシング、DR）
```

---

## 注釈

- **T7**: 1-2 週間の本番トラフィック分析が必要なため、早期開始を推奨
- **CloudFlare**: AWS CloudFront+ cloudfront + WAF コスト比較による長期的な削減が見込まれる
- **テストカバレッジ**: 継続的な品質向上のため優先度を上げることを検討

---

*最終更新: 2026-03-03 (セッション完了後)*
*次回レビュー推奨日: 2026-03-10*
