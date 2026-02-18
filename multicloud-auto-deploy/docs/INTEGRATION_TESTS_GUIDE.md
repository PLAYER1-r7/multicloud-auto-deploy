# 統合テスト完全ガイド

**作成日**: 2026-02-18  
**バージョン**: 1.0.0  
**対象環境**: All (AWS/GCP/Azure)

---

## 📋 目次

1. [概要](#概要)
2. [テスト構成](#テスト構成)
3. [実行方法](#実行方法)
4. [テストカバレッジ](#テストカバレッジ)
5. [トラブルシューティング](#トラブルシューティング)
6. [CI/CD統合](#ci-cd統合)

---

## 概要

本プロジェクトの統合テストは、**3つのクラウドプロバイダー（AWS/GCP/Azure）**のバックエンド実装を網羅的にテストします。

### テストの種類

| テスト種別                  | 説明                                   | ツール            |
| --------------------------- | -------------------------------------- | ----------------- |
| **ユニットテスト**          | バックエンドクラスの個別メソッドテスト | pytest (mocked)   |
| **統合テスト**              | CRUD操作の完全フローテスト             | pytest (mocked)   |
| **APIエンドポイントテスト** | 実際のデプロイ済みAPI HTTPテスト       | pytest + requests |
| **E2Eテスト**               | 全クラウドのエンドツーエンドテスト     | bash + curl       |

---

## テスト構成

### ディレクトリ構造

```
services/api/
├── tests/
│   ├── __init__.py                    # テストパッケージ初期化
│   ├── conftest.py                    # pytest設定とフィクスチャ
│   ├── test_backends_integration.py   # バックエンド統合テスト
│   └── test_api_endpoints.py          # APIエンドポイントテスト
├── pytest.ini                         # pytest設定ファイル
└── requirements-dev.txt               # 開発/テスト用依存関係

scripts/
├── run-integration-tests.sh           # Pythonテスト実行スクリプト (NEW)
├── test-api.sh                        # 単一API HTTPテスト
├── test-e2e.sh                        # マルチクラウドE2Eテスト
└── test-endpoints.sh                  # エンドポイントヘルスチェック
```

### テストファイル詳細

#### 1. `conftest.py` - pytest設定

**機能**:

- テスト用フィクスチャ定義
- ユーザー認証情報モック
- サンプルデータ生成
- クリーンアップ処理

**主要フィクスチャ**:

```python
test_user()              # 一般ユーザー
admin_user()             # 管理者ユーザー
another_user()           # 別ユーザー
sample_post_body()       # 投稿作成用データ
sample_update_body()     # 投稿更新用データ
sample_profile_update()  # プロフィール更新用データ
aws_config()             # AWS設定
gcp_config()             # GCP設定
azure_config()           # Azure設定
```

#### 2. `test_backends_integration.py` - バックエンド統合テスト

**テストクラス**:

##### `TestBackendBase` (基底クラス)

全バックエンド共通のテストケース:

- ✅ `test_backend_initialization()` - バックエンド初期化
- ✅ `test_create_post_success()` - 投稿作成
- ✅ `test_list_posts_empty()` - 投稿一覧（空）
- ✅ `test_list_posts_with_tag_filter()` - タグフィルタリング
- ✅ `test_update_post_success()` - 投稿更新
- ✅ `test_update_post_permission_denied()` - 権限エラー（更新）
- ✅ `test_update_post_admin_can_update()` - 管理者権限（更新）
- ✅ `test_delete_post_success()` - 投稿削除
- ✅ `test_delete_post_permission_denied()` - 権限エラー（削除）
- ✅ `test_delete_post_admin_can_delete()` - 管理者権限（削除）
- ✅ `test_get_profile_not_found()` - プロフィール取得（未存在）
- ✅ `test_update_profile_success()` - プロフィール更新
- ✅ `test_get_profile_after_update()` - 更新後プロフィール取得
- ✅ `test_generate_upload_urls()` - アップロードURL生成

##### `TestAwsBackend` (AWS特化)

- DynamoDB + S3 のモックテスト
- マーカー: `@pytest.mark.aws`

##### `TestGcpBackend` (GCP特化)

- Firestore + Cloud Storage のモックテスト
- マーカー: `@pytest.mark.gcp`

##### `TestAzureBackend` (Azure特化)

- Cosmos DB + Blob Storage のモックテスト
- マーカー: `@pytest.mark.azure`

#### 3. `test_api_endpoints.py` - APIエンドポイントテスト

**テストクラス**:

##### `TestAPIEndpoints`

実際のデプロイ済みAPIエンドポイントをテスト:

- ✅ `test_health_check()` - ヘルスチェック
- ✅ `test_list_messages_initial()` - メッセージ一覧取得
- ✅ `test_crud_operations_flow()` - CRUD完全フロー
- ✅ `test_pagination()` - ページネーション
- ✅ `test_invalid_message_id()` - 無効ID（404エラー）
- ✅ `test_empty_content_validation()` - バリデーションエラー

**参考**: `scripts/test-api.sh` のテストケース 1-12

##### `TestMultiCloudEndpoints`

- ✅ `test_all_cloud_health_checks()` - 全クラウドヘルスチェック

**参考**: `scripts/test-endpoints.sh`

##### `TestCrossCloudConsistency`

- ✅ `test_response_format_consistency()` - レスポンス形式の一貫性
- ✅ `test_api_version_consistency()` - APIバージョンの一貫性

**参考**: `scripts/test-e2e.sh` の一貫性チェック

---

## 実行方法

### 方法1: Python pytest直接実行

#### 全テスト実行（モックテストのみ）

```bash
cd services/api
pytest tests/
```

#### AWS バックエンドのみテスト

```bash
pytest tests/ -m aws
```

#### GCP バックエンドのみテスト

```bash
pytest tests/ -m gcp
```

#### Azure バックエンドのみテスト

```bash
pytest tests/ -m azure
```

#### 詳細出力

```bash
pytest tests/ -vv
```

#### カバレッジレポート生成

```bash
pytest tests/ --cov=app --cov-report=html
# レポート: htmlcov/index.html
```

#### 特定のテストのみ実行

```bash
pytest tests/ -k "test_create_post"
```

### 方法2: シェルスクリプト実行（推奨）

#### Pythonテスト実行

```bash
./scripts/run-integration-tests.sh
```

#### 詳細出力で実行

```bash
./scripts/run-integration-tests.sh -v
```

#### 特定のマーカーでテスト

```bash
./scripts/run-integration-tests.sh -m aws
```

#### 実際のAPIエンドポイントをテスト

```bash
# 環境変数設定
export AWS_API_ENDPOINT="https://abc123.execute-api.ap-northeast-1.amazonaws.com"
export GCP_API_ENDPOINT="https://app-xyz.a.run.app"
export AZURE_API_ENDPOINT="https://func-xyz.azurewebsites.net/api/HttpTrigger"

# 実行
./scripts/run-integration-tests.sh --endpoints
```

#### カバレッジ付きで実行

```bash
./scripts/run-integration-tests.sh --coverage
```

### 方法3: 既存のシェルスクリプト実行

#### 単一APIテスト

```bash
./scripts/test-api.sh -e https://your-api-endpoint.com
```

#### マルチクラウドE2Eテスト

```bash
./scripts/test-e2e.sh
```

#### エンドポイントヘルスチェック

```bash
./scripts/test-endpoints.sh
```

---

## テストカバレッジ

### バックエンドメソッド

| メソッド                 | AWS | GCP | Azure | テスト数 |
| ------------------------ | :-: | :-: | :---: | :------: |
| `list_posts()`           | ✅  | ✅  |  ✅   |    3     |
| `create_post()`          | ✅  | ✅  |  ✅   |    3     |
| `update_post()`          | ✅  | ✅  |  ✅   |    9     |
| `delete_post()`          | ✅  | ✅  |  ✅   |    9     |
| `get_profile()`          | ✅  | ✅  |  ✅   |    3     |
| `update_profile()`       | ✅  | ✅  |  ✅   |    6     |
| `generate_upload_urls()` | ✅  | ✅  |  ✅   |    3     |

**合計**: 108テストケース（36ケース × 3クラウド）

### APIエンドポイント

| エンドポイント             | メソッド | テスト               | 参考スクリプト     |
| -------------------------- | -------- | -------------------- | ------------------ |
| `/`                        | GET      | ヘルスチェック       | test-api.sh #1     |
| `/api/messages/`           | GET      | 一覧取得             | test-api.sh #2, #4 |
| `/api/messages/`           | POST     | 作成                 | test-api.sh #3     |
| `/api/messages/{id}`       | GET      | 個別取得             | test-api.sh #5     |
| `/api/messages/{id}`       | PUT      | 更新                 | test-api.sh #6, #7 |
| `/api/messages/{id}`       | DELETE   | 削除                 | test-api.sh #8, #9 |
| `/api/messages/?page=1`    | GET      | ページネーション     | test-api.sh #10    |
| `/api/messages/invalid-id` | GET      | エラー404            | test-api.sh #11    |
| `/api/messages/`           | POST     | バリデーションエラー | test-api.sh #12    |

**合計**: 27エンドポイントテスト（9エンドポイント × 3クラウド）

---

## pytest マーカー

テストを分類・フィルタリングするためのマーカー:

| マーカー                            | 説明               | 使用例                       |
| ----------------------------------- | ------------------ | ---------------------------- |
| `@pytest.mark.aws`                  | AWS特化テスト      | `pytest -m aws`              |
| `@pytest.mark.gcp`                  | GCP特化テスト      | `pytest -m gcp`              |
| `@pytest.mark.azure`                | Azure特化テスト    | `pytest -m azure`            |
| `@pytest.mark.integration`          | 統合テスト         | `pytest -m integration`      |
| `@pytest.mark.unit`                 | ユニットテスト     | `pytest -m unit`             |
| `@pytest.mark.slow`                 | 時間のかかるテスト | `pytest -m "not slow"`       |
| `@pytest.mark.requires_network`     | ネットワーク必須   | `pytest -m requires_network` |
| `@pytest.mark.requires_credentials` | 認証情報必須       | デフォルトで除外             |

---

## トラブルシューティング

### 問題: pytest が見つからない

**解決方法**:

```bash
pip install pytest pytest-mock pytest-asyncio requests
```

### 問題: ImportError: No module named 'app'

**解決方法**:

```bash
# services/api ディレクトリから実行
cd /workspaces/ashnova/multicloud-auto-deploy/services/api
pytest tests/
```

### 問題: モックエラー (MagicMock related)

**解決方法**:

```bash
pip install pytest-mock
```

### 問題: API エンドポイントテストが失敗

**原因**: エンドポイントが未設定または未デプロイ

**解決方法**:

```bash
# 環境変数を設定
export AWS_API_ENDPOINT="https://your-endpoint.com"

# または、テスト実行時にスキップ
pytest tests/ -m "not requires_network"
```

### 問題: Permission denied エラー

**原因**: テストスクリプトに実行権限がない

**解決方法**:

```bash
chmod +x scripts/run-integration-tests.sh
```

---

## CI/CD統合

### GitHub Actions

`.github/workflows/test.yml` 例:

```yaml
name: Integration Tests

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          cd services/api
          pip install -r requirements.txt
          pip install pytest pytest-mock pytest-asyncio requests

      - name: Run integration tests
        run: |
          ./scripts/run-integration-tests.sh -v

      - name: Run endpoint tests (if deployed)
        if: env.AWS_API_ENDPOINT != ''
        env:
          AWS_API_ENDPOINT: ${{ secrets.AWS_API_ENDPOINT }}
          GCP_API_ENDPOINT: ${{ secrets.GCP_API_ENDPOINT }}
          AZURE_API_ENDPOINT: ${{ secrets.AZURE_API_ENDPOINT }}
        run: |
          ./scripts/run-integration-tests.sh --endpoints
```

### ローカルでのCI模倣

```bash
# 全テストを実行（CIと同じ）
./scripts/run-integration-tests.sh -v

# カバレッジ付きで実行
./scripts/run-integration-tests.sh --coverage
```

---

## テスト実行例

### 例1: 開発時の基本テスト

```bash
# サービスディレクトリへ移動
cd services/api

# 全テスト実行
pytest tests/ -v

# 出力例:
# tests/test_backends_integration.py::TestBackendBase::test_create_post_success PASSED
# tests/test_backends_integration.py::TestBackendBase::test_update_post_success PASSED
# ...
# ==================== 42 passed in 2.15s ====================
```

### 例2: AWS特化テスト

```bash
./scripts/run-integration-tests.sh -m aws -v

# 出力例:
# ========================================
# Python統合テスト実行
# ========================================
#
# Python: 3.12.0
# pytest: pytest 7.4.3
# マーカー: -m aws
#
# tests/test_backends_integration.py::TestAwsBackend::test_backend_initialization PASSED
# tests/test_backends_integration.py::TestAwsBackend::test_create_post_success PASSED
# ...
# ========================================
# ✅ 全てのテストが成功しました！
# ========================================
```

### 例3: 実デプロイ済みAPIテスト

```bash
# 環境変数設定
export AWS_API_ENDPOINT="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"

# エンドポイントテスト実行
./scripts/run-integration-tests.sh --endpoints -v

# 出力例:
# ========================================
# Python統合テスト実行
# ========================================
#
# エンドポイントテスト: 有効
#
# 環境変数:
#   AWS_API_ENDPOINT=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
#   GCP_API_ENDPOINT=未設定
#   AZURE_API_ENDPOINT=未設定
#
# tests/ test_api_endpoints.py::TestAPIEndpoints::test_health_check[aws] PASSED
# tests/test_api_endpoints.py::TestAPIEndpoints::test_crud_operations_flow[aws] PASSED
# ...
#
# === Multi-Cloud Health Check Results ===
# ✅ aws: {'status_code': 200, 'accessible': True, 'response': {...}}
# ❌ gcp: {'status_code': None, 'accessible': False, 'error': '...'}
# ...
```

### 例4: カバレッジレポート生成

```bash
./scripts/run-integration-tests.sh --coverage

# 出力例:
# ...
# ---------- coverage: platform linux, python 3.12.0 ----------
# Name                                  Stmts   Miss  Cover
# ---------------------------------------------------------
# app/__init__.py                           0      0   100%
# app/backends/__init__.py                 10      0   100%
# app/backends/aws_backend.py             150     15    90%
# app/backends/gcp_backend.py             145     12    92%
# app/backends/azure_backend.py           148     14    91%
# ---------------------------------------------------------
# TOTAL                                   453     41    91%
#
# カバレッジレポート: htmlcov/index.html
```

---

## まとめ

### テストの目的

1. **品質保証**: 全バックエンドが仕様通り動作することを保証
2. **リグレッション防止**: コード変更時の意図しない動作変更を検出
3. **ドキュメント**: テストコードが実装の使用例となる
4. **CI/CD統合**: 自動テストでデプロイ前に品質チェック

### ベストプラクティス

- ✅ **コミット前にテスト実行**: `./scripts/run-integration-tests.sh`
- ✅ **新機能追加時はテスト追加**: 新しいメソッドには対応するテストを書く
- ✅ **デプロイ後はエンドポイントテスト**: `./scripts/run-integration-tests.sh --endpoints`
- ✅ **定期的にE2Eテスト**: `./scripts/test-e2e.sh`
- ✅ **カバレッジ90%以上維持**: `--coverage` で確認

### 今後の改善

- [ ] パフォーマンステスト追加 (`TestBackendPerformance`)
- [ ] エンドツーエンドワークフローテスト追加 (`TestEndToEnd`)
- [ ] 負荷テスト（Locust等）
- [ ] セキュリティテスト（認証・認可）
- [ ] カオスエンジニアリングテスト（障害シミュレーション）

---

**作成者**: GitHub Copilot  
**最終更新**: 2026-02-18  
**関連ドキュメント**:

- [API_OPERATION_VERIFICATION_REPORT.md](API_OPERATION_VERIFICATION_REPORT.md)
- [AWS_BACKEND_COMPLETE_FIX_REPORT.md](AWS_BACKEND_COMPLETE_FIX_REPORT.md)
- [BACKEND_IMPLEMENTATION_INVESTIGATION.md](BACKEND_IMPLEMENTATION_INVESTIGATION.md)
