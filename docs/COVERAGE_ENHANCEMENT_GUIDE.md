# テストカバレッジ向上スクリプト - 実装ガイド

## 概要

カバレッジ率が **10%** から目標値への向上を目指すための包括的なテストの実装が完了しました。

## 現在の状況分析

### カバレッジレポート（before）
- **全体**: 10%
- **auth.py**: 34% （20/59 行）
- **jwt_verifier.py**: 0% （0/117 行）
- **main.py**: 0% （0/140 行）
- **routes/posts.py**: 0% （0/33 行）
- **routes/profile.py**: 0% （0/17 行）
- **routes/uploads.py**: 0% （0/14 行）
- **routes/limits.py**: 0% （0/6 行）
- **backends/aws_backend.py**: 15% （22/146 行）
- **backends/azure_backend.py**: 14% （29/202 行）
- **backends/gcp_backend.py**: 12% （23/186 行）
- **backends/local_backend.py**: 0% （0/205 行）

### テスト対象の優先度

#### 高優先度（テストなし、重要なモジュール）
1. **jwt_verifier.py** - 認証トークン検証（セッション）
2. **main.py** - FastAPI メインアプリケーション
3. **routes/posts.py** - POST CRUD エンドポイント
4. **routes/profile.py** - ユーザープロフィールエンドポイント
5. **routes/uploads.py** - ファイルアップロードエンドポイント

#### 中優先度（テストが少ない）
6. **auth.py** - 認証機能（34%のため拡張）
7. **backends/*_backend.py** - クラウドバックエンド実装（12-15%）

#### 低優先度
8. **config.py** - 既に100%
9. **models.py** - 既に99%

## 新規作成テストファイル

### 1. **test_auth.py** （新規）
**登録行数**: 80行

**テスト対象**:
- `UserInfo` モデルの生成
- `get_current_user` 依存関数
  - 認証無効時の処理
  - 有効なトークンの処理
  - トークンなしの場合
  - 無効なBearerフォーマット
  - トークンデコードエラー
- ユーザーパーミッション
  - 管理者グループ判定
  - 複数グループの管理

**期待カバレッジ向上**: auth.py を **34% → 70%+** に向上

### 2. **test_jwt_verifier.py** （新規）
**登録行数**: 190行

**テスト対象**:
- `decode_token()` 基本機能
  - 有効なトークンのデコード
  - 期限切れトークン
  - 無効な署名
  - クレームなしトークン
- **AWS Cognito認証**
  - JWKS エンドポイント連携
  - トークン検証成功
  - 必須クレーム検証
- **Google Firebase認証**
  - Firebase トークン検証
  - 無効な発行者検出
- **Azure AD認証**
  - Azure トークン検証
  - OID クレーム検証
- **エッジケース**
  - 空のトークン
  - 不正形式のトークン
  - JWKS タイムアウト
  - JWKS 無効なレスポンス

**期待カバレッジ向上**: jwt_verifier.py を **0% → 70%+** に向上

### 3. **test_routes.py** （新規）
**登録行数**: 280行

**テスト対象**:

#### Posts ルート
- POST 作成（成功、バリデーション）
- 一覧取得（通常、ページネーション、タグフィルタ）
- 取得（成功、404）
- 更新（成功）
- 削除（成功）

#### Profile ルート
- プロフィール取得
- プロフィール更新
- 自分のプロフィール取得

#### Uploads ルート
- 署名付きURL生成
- 制限チェック（最大16個）
- 超過時のエラー

#### Limits ルート
- API制限値取得
- 設定値検証

**期待カバレッジ向上**:
- routes/posts.py: **0% → 80%+**
- routes/profile.py: **0% → 80%+**
- routes/uploads.py: **0% → 80%+**
- routes/limits.py: **0% → 80%+**

## テスト実行スクリプト

### **run-comprehensive-coverage-tests.sh** （新規）

包括的なカバレッジテストスイートを実行するシェルスクリプト

**機能**:
1. 全テスト（test_auth.py, test_jwt_verifier.py, test_routes.py）の実行
2. カバレッジレポート自動生成（HTML + JSON）
3. モジュール別カバレッジ分析と表示
4. 色分けされた結果表示（Green: 80%+, Yellow: 60-80%, Red: <60%）
5. カバレッジ最小値チェック

**使用方法**:

```bash
# 基本実行（全テストとレポート生成）
./scripts/run-comprehensive-coverage-tests.sh

# 詳細出力
./scripts/run-comprehensive-coverage-tests.sh -v

# 特定のマーカーのテストのみ
./scripts/run-comprehensive-coverage-tests.sh -m aws

# カバレッジ最小値を50%に設定
./scripts/run-comprehensive-coverage-tests.sh --fail-under 50

# 複合使用
./scripts/run-comprehensive-coverage-tests.sh -v --fail-under 60
```

**出力例**:
```
===============================================
Comprehensive Test Suite with Coverage
===============================================

Running tests...

===============================================
Coverage Analysis
===============================================

Overall Coverage: 62.5%

Per-Module Coverage:
  app/auth.py                        65.0%
  app/config.py                     100.0%
  app/jwt_verifier.py                72.5%
  app/main.py                        58.0%
  app/models.py                      99.0%
  app/routes/posts.py                78.0%
  ...

✅ All tests passed!

  • Coverage report generated in htmlcov/
  • JSON coverage data saved to coverage.json
```

## カバレッジ向上目標

### 段階的な目標設定

| フェーズ | 全体カバレッジ | 対象モジュール | 期限 |
|---------|---------------|----------------|------|
| フェーズ1（当初） | 10% | 既存テスト | 2026-03-03 |
| フェーズ2（新規テスト適用） | 35-40% | auth, jwt_verifier, routes | 即時 |
| フェーズ3（バックエンド強化） | 45-50% | backends (aws/gcp/azure) | 1週間 |
| フェーズ4（エッジケース） | 55-60% | エラーハンドリング | 2週間 |
| フェーズ5（統合テスト） | 70% | E2E、統合シナリオ | 3週間 |

## 実行手順

### 1. テスト環境セットアップ

```bash
cd services/api

# 依存パッケージのインストール
pip install -r requirements-dev.txt

# またはピンポイントインストール
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### 2. テスト実行と検証

```bash
# 新規テストのみ実行
pytest tests/test_auth.py -v
pytest tests/test_jwt_verifier.py -v
pytest tests/test_routes.py -v

# すべてのテストを実行
./scripts/run-comprehensive-coverage-tests.sh

# カバレッジレポート確認
open htmlcov/index.html
```

### 3. CI/CD 統合

GitHub Actions ワークフローに追加：

```yaml
- name: Run comprehensive coverage tests
  run: |
    cd services/api
    chmod +x ../../scripts/run-comprehensive-coverage-tests.sh
    ../../scripts/run-comprehensive-coverage-tests.sh --fail-under 50
```

## 既存テストとの互換性

新規テストは既存テストと統合可能：

```bash
# 既存 + 新規テスト
cd services/api
pytest tests/ --cov=app --cov-report=html

# またはスクリプト経由
./scripts/run-integration-tests.sh --coverage
```

## トラブルシューティング

### ImportError: No module named 'app'
```bash
cd /workspaces/multicloud-auto-deploy/services/api
export PYTHONPATH=$PYTHONPATH:$(pwd)
pytest tests/
```

### カバレッジ計算エラーの場合
```bash
# キャッシュをクリア
rm -rf .pytest_cache .coverage __pycache__
pytest tests/ --cov=app --cov-report=html
```

### テスト実行時のモック失敗
```bash
# unittest.mock をインストール
pip install pytest-mock
```

## 参考資料

- **既存テストドキュメント**: [docs/AI_AGENT_13_TESTING_JA.md](../docs/AI_AGENT_13_TESTING_JA.md)
- **pytest公式ドキュメント**: https://docs.pytest.org/
- **カバレッジツール**: https://coverage.readthedocs.io/

## 次のステップ

1. ✅ **新規テストファイルの作成** （完了）
2. ⏳ **テスト実行と結果検証** <-- 次はここ
3. 📊 **カバレッジレポート分析**
4. 🔧 **バックエンドテストの拡張**
5. 📈 **カバレッジ目標達成（70%+）**

---

**作成日**: 2026-03-03
**作成者**: GitHub Copilot
**バージョン**: 1.0.0
