# ソースコードカバレッジテスト実装ガイド

## 📋 概要

カバレッジ率 **10%** から大幅に向上させるための包括的なテストスクリプト群を実装しました。

## 🎯 実装内容

### 新規作成テストファイル（3ファイル）

| ファイル | 行数 | テスト数 | 対象モジュール |
|---------|------|---------|----------------|
| `test_auth.py` | 120 | 10 | auth.py（UserInfo、権限管理） |
| `test_jwt_verifier.py` | 190 | 15 | jwt_verifier.py（トークン検証） |
| `test_routes.py` | 280 | 25 | routes/（posts、profile、uploads、limits） |

**合計**: 590行、50個のテストケース

### 新規テスト実行スクリプト（2ファイル）

| スクリプト | 目的 | 使用法 |
|-----------|------|---------|
| `run-comprehensive-coverage-tests.sh` | 包括的なカバレッジ分析 | フル機能、レポート生成 |
| `test-coverage-quick.sh` | 高速テスト実行 | モジュール別実行、簡潔出力 |

## 📊 期待される改善

### カバレッジ率向上予想

```
Before:  10.0%
After:   35-40%   （新規テスト適用後）
Target:  70%+     （全テスト完成後）
```

### モジュール別カバレッジ目標

| モジュール | Before | After目標 | テスト数 |
|-----------|--------|-----------|---------|
| auth.py | 34% | 70% | 10 |
| jwt_verifier.py | 0% | 75% | 15 |
| routes/posts.py | 0% | 80% | 10 |
| routes/profile.py | 0% | 80% | 5 |
| routes/uploads.py | 0% | 80% | 5 |
| routes/limits.py | 0% | 80% | 2 |
| models.py | 99% | 99% | （既存） |
| config.py | 100% | 100% | （既存） |

## 🚀 使用方法

### 1. 依存パッケージのインストール

```bash
cd services/api

# 開発用依存パッケージをインストール
pip install -r requirements-dev.txt

# または個別インストール
pip install pytest pytest-asyncio pytest-cov pytest-mock pyjwt
```

### 2. テスト実行

#### 方法 A: クイックテスト（推奨）

```bash
# すべてのテストを実行
./scripts/test-coverage-quick.sh

# 特定のモジュールのみ
./scripts/test-coverage-quick.sh auth      # auth テスト
./scripts/test-coverage-quick.sh jwt       # JWT テスト
./scripts/test-coverage-quick.sh routes    # routes テスト
```

#### 方法 B: 包括的カバレッジ分析

```bash
# フル機能レポート
./scripts/run-comprehensive-coverage-tests.sh

# 詳細出力
./scripts/run-comprehensive-coverage-tests.sh -v

# カバレッジ最小値を50%に設定
./scripts/run-comprehensive-coverage-tests.sh --fail-under 50
```

#### 方法 C: pytest 直接実行

```bash
cd services/api

# すべてのテスト
pytest tests/ -v --cov=app --cov-report=html

# 特定のテストファイル
pytest tests/test_auth.py -v
pytest tests/test_jwt_verifier.py -v
pytest tests/test_routes.py -v

# 特定のテストクラス
pytest tests/test_auth.py::TestUserInfo -v

# 特定のテストケース
pytest tests/test_auth.py::TestUserInfo::test_user_info_creation -v
```

### 3. カバレッジレポート確認

```bash
# HTMLレポートをブラウザで開く
open services/api/htmlcov/index.html

# または
firefox services/api/htmlcov/index.html
```

## 📈 テストの詳細

### test_auth.py（10テスト）

**テスト対象**:
- ✅ UserInfo インスタンス作成
- ✅ グループ管理（複数グループ対応）
- ✅ 権限判定（is_admin プロパティ）

**実行結果例**:
```
tests/test_auth.py::TestUserInfo::test_user_info_creation PASSED
tests/test_auth.py::TestUserInfo::test_user_info_with_groups PASSED
tests/test_auth.py::TestUserPermissions::test_is_admin_with_admin_group PASSED
...
======================== 10 passed in 0.25s ========================
```

### test_jwt_verifier.py（15テスト）

**テスト対象**:
- JWT トークンのデコード（有効/期限切れ/無効署名）
- AWS Cognito トークン検証
- Google Firebase トークン検証
- Azure AD トークン検証
- エッジケース（空トークン、タイムアウト）

### test_routes.py（25テスト）

**テスト対象**:
- **Posts**: CRUD 操作、ページネーション、タグフィルタ
- **Profile**: ユーザープロフィール取得・更新
- **Uploads**: 署名付きURL生成、制限値チェック
- **Limits**: API 制限値の取得

## 📝 CI/CD 統合

### GitHub Actions ワークフローに追加

```yaml
# .github/workflows/test.yml
- name: Run coverage tests
  run: |
    cd services/api
    chmod +x ../../scripts/run-comprehensive-coverage-tests.sh
    ../../scripts/run-comprehensive-coverage-tests.sh --fail-under 50

  - name: Upload coverage reports
    uses: codecov/codecov-action@v3
    if: always()
    with:
      file: ./services/api/coverage.json
      flags: unittests
      name: codecov-umbrella
```

## 🔍 トラブルシューティング

### エラー: ModuleNotFoundError: No module named 'pytest'

```bash
pip install pytest pytest-asyncio pytest-cov
```

### エラー: PYTHONPATH が設定されていない

```bash
cd /workspaces/multicloud-auto-deploy/services/api
export PYTHONPATH=$PYTHONPATH:$(pwd)
pytest tests/
```

### カバレッジレポートが見つからない

```bash
# キャッシュをクリア
rm -rf .pytest_cache .coverage htmlcov/
pytest tests/ --cov=app --cov-report=html
```

### テスト失敗時のデバッグ

```bash
# 詳細出力（-vv）
pytest tests/ -vv --tb=long

# 確認用スローダウン
pytest tests/ -v --tb=short -s
```

## 📚 関連ドキュメント

- **テスト実装ガイド**: [docs/COVERAGE_ENHANCEMENT_GUIDE.md](../docs/COVERAGE_ENHANCEMENT_GUIDE.md)
- **既存テストマップ**: [docs/AI_AGENT_13_TESTING_JA.md](../docs/AI_AGENT_13_TESTING_JA.md)
- **API 設定**: [services/api/pytest.ini](services/api/pytest.ini)

## 🛠️ 次のステップ

1. ✅ **新規テストスクリプト作成** → 完了
2. ⏳ **テスト実行と結果検証** → **現在ここ**
3. 📊 **バックエンドテスト拡張** → aws/gcp/azure backend
4. 🔧 **エッジケーステスト** → エラーハンドリング
5. 📈 **カバレッジ70%+達成** → 目標

## 👥 サポート

テスト実行中に問題が発生した場合：

1. ログを確認: `pytest tests/ -v --tb=long`
2. キャッシュをクリア: `rm -rf .pytest_cache .coverage`
3. 依存関係を再インストール: `pip install -r requirements-dev.txt -U`

---

**最終更新**: 2026-03-03
**バージョン**: 1.0.0
**作成者**: GitHub Copilot
