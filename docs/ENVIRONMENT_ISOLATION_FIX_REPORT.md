# 環境混入対策レポート

**作成日**: 2026-02-27
**対象ツール**: `scripts/cloud_architecture_mapper.py`
**問題**: staging/production環境のリソースが相互に混入

---

## 1. 問題の詳細

### 1.1 確認された混入

- **staging スナップショット** に `multicloud-auto-deploy-production-api` (GCP Cloud Run) が混入
- **production スナップショット** に `multicloud-auto-deploy-staging-api` (GCP Cloud Run) が混入

### 1.2 影響範囲

- **AWS**: 影響なし（正しくフィルタリング済み）
- **Azure**: 影響なし（正しくフィルタリング済み）
- **GCP**: Cloud Run サービスで混入発生 ⚠️

### 1.3 根本原因

**問題のコード** ([cloud_architecture_mapper.py Line 315](../scripts/cloud_architecture_mapper.py#L315)):

```python
for service in run_services:
    name = service.get("metadata", {}).get("name", "")
    if stack in name or "multicloud-auto-deploy" in name:  # ← 問題の条件
        append_resource(snapshot, "compute", name, name, region, "gcloud-cli")
```

**なぜ混入するか**:

```python
stack = "staging"
name = "multicloud-auto-deploy-production-api"

# 条件1: stack in name
"staging" in "multicloud-auto-deploy-production-api"  # → False

# 条件2: "multicloud-auto-deploy" in name
"multicloud-auto-deploy" in "multicloud-auto-deploy-production-api"  # → True ✗

# → OR条件により、production APIもstagingスナップショットに含まれる
```

---

## 2. 現状のリソース名規則

### 2.1 実際に存在するGCPリソース

**Cloud Run サービス**:

```
multicloud-auto-deploy-production-api
multicloud-auto-deploy-staging-api
```

**Storage バケット**:

```
ashnova-multicloud-auto-deploy-production-frontend
ashnova-multicloud-auto-deploy-production-function-source
ashnova-multicloud-auto-deploy-production-uploads
ashnova-multicloud-auto-deploy-staging-frontend
ashnova-multicloud-auto-deploy-staging-function-source
ashnova-multicloud-auto-deploy-staging-landing
ashnova-multicloud-auto-deploy-staging-uploads
```

### 2.2 命名パターン分析

| リソースタイプ | パターン                                       | 例                              |
| -------------- | ---------------------------------------------- | ------------------------------- |
| Cloud Run      | `multicloud-auto-deploy-{環境}-api`            | `staging-api`, `production-api` |
| Storage        | `ashnova-multicloud-auto-deploy-{環境}-{用途}` | `staging-frontend`              |
| URL Maps       | `multicloud-auto-deploy-{環境}-cdn-*`          | `staging-cdn-urlmap-v2`         |

**共通点**: すべて `{プレフィックス}-{環境名}-{サフィックス}` 形式

---

## 3. 修正案

### 3.1 推奨する修正方法（優先度1）

**修正内容**: AWS/Azure と同じフィルタパターンに統一

**変更前** (Line 262-315):

```python
def collect_gcp(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    project_id = snapshot.pulumi_outputs.get("gcp_project")
    if not project_id:
        try:
            project_id = run_text_command(["gcloud", "config", "get-value", "project"])
        except Exception:
            project_id = ""

    frontend_prefix = f"ashnova-multicloud-auto-deploy-{stack}"
    # ... (backend-buckets, url-mapsのコードは変更なし)

    # 問題の箇所
    run_services = run_json_command([...])
    for service in run_services:
        name = service.get("metadata", {}).get("name", "")
        if stack in name or "multicloud-auto-deploy" in name:  # ← 緩すぎる
            append_resource(snapshot, "compute", name, name, region, "gcloud-cli")
```

**変更後**:

```python
def collect_gcp(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    project_id = snapshot.pulumi_outputs.get("gcp_project")
    if not project_id:
        try:
            project_id = run_text_command(["gcloud", "config", "get-value", "project"])
        except Exception:
            project_id = ""

    # 環境プレフィックスを統一的に定義
    prefix = f"multicloud-auto-deploy-{stack}"
    frontend_prefix = f"ashnova-{prefix}"

    # ... (backend-buckets, url-mapsのコードは変更なし)

    # 修正後の厳密なフィルタ
    run_services = run_json_command([...])
    for service in run_services:
        name = service.get("metadata", {}).get("name", "")
        if prefix in name:  # ← 厳密な環境判定
            append_resource(snapshot, "compute", name, name, region, "gcloud-cli")
```

**修正理由**:

1. AWS (`prefix = f"multicloud-auto-deploy-{stack}"`) と同じパターンで統一
2. 環境名が含まれるリソースのみを収集（`staging` → `multicloud-auto-deploy-staging-*` のみ）
3. 将来的な環境追加（dev, qa等）にも対応可能

### 3.2 代替案（優先度2）

**オプションA: 正規表現による厳密なパターンマッチング**

```python
import re

pattern = re.compile(rf"multicloud-auto-deploy-{stack}-.+")
for service in run_services:
    name = service.get("metadata", {}).get("name", "")
    if pattern.match(name):
        append_resource(...)
```

**メリット**: より厳密な制御、誤マッチを完全防止
**デメリット**: 複雑性増加、パフォーマンスオーバーヘッド

**オプションB: リソースラベルベースのフィルタ**

```python
for service in run_services:
    labels = service.get("metadata", {}).get("labels", {})
    if labels.get("environment") == stack:
        append_resource(...)
```

**メリット**: 最も信頼性が高い、命名規則に依存しない
**デメリット**: すべてのリソースにラベル付けが必要（インフラ変更が必要）

---

## 4. テスト計画

### 4.1 修正後の検証方法

**ステップ1: スナップショット再生成**

```bash
cd /workspaces/multicloud-auto-deploy

# stagingスナップショット生成
.venv/bin/python scripts/cloud_architecture_mapper.py collect \
  --stack staging \
  --output docs/generated/architecture/snapshot.staging.json

# productionスナップショット生成
.venv/bin/python scripts/cloud_architecture_mapper.py collect \
  --stack production \
  --output docs/generated/architecture/snapshot.production.json
```

**ステップ2: 混入チェック**

```bash
# stagingにproductionリソースが含まれていないことを確認
jq -r '.clouds.gcp.resources[] | select(.resource_type == "compute") | .name' \
  docs/generated/architecture/snapshot.staging.json | grep production
# → 出力なし（空）が期待値

# productionにstagingリソースが含まれていないことを確認
jq -r '.clouds.gcp.resources[] | select(.resource_type == "compute") | .name' \
  docs/generated/architecture/snapshot.production.json | grep staging
# → 出力なし（空）が期待値
```

**ステップ3: 正しいリソースが含まれることを確認**

```bash
# staging環境のリソース確認
jq -r '.clouds.gcp.resources[] | select(.resource_type == "compute") | .name' \
  docs/generated/architecture/snapshot.staging.json
# → "multicloud-auto-deploy-staging-api" のみ出力されるべき

# production環境のリソース確認
jq -r '.clouds.gcp.resources[] | select(.resource_type == "compute") | .name' \
  docs/generated/architecture/snapshot.production.json
# → "multicloud-auto-deploy-production-api" のみ出力されるべき
```

### 4.2 期待される結果

| 環境       | 収集されるべきCloud Run                 | 収集されるべきでないCloud Run           |
| ---------- | --------------------------------------- | --------------------------------------- |
| staging    | `multicloud-auto-deploy-staging-api`    | `multicloud-auto-deploy-production-api` |
| production | `multicloud-auto-deploy-production-api` | `multicloud-auto-deploy-staging-api`    |

---

## 5. 実装コード

### 5.1 修正パッチ

**ファイル**: `scripts/cloud_architecture_mapper.py`

**変更箇所1: prefixの統一定義** (Line 262-270):

```python
# 変更前
def collect_gcp(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    project_id = snapshot.pulumi_outputs.get("gcp_project")
    if not project_id:
        try:
            project_id = run_text_command(["gcloud", "config", "get-value", "project"])
        except Exception:
            project_id = ""

    frontend_prefix = f"ashnova-multicloud-auto-deploy-{stack}"
```

```python
# 変更後
def collect_gcp(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    project_id = snapshot.pulumi_outputs.get("gcp_project")
    if not project_id:
        try:
            project_id = run_text_command(["gcloud", "config", "get-value", "project"])
        except Exception:
            project_id = ""

    # AWS/Azureと同じパターンに統一
    prefix = f"multicloud-auto-deploy-{stack}"
    frontend_prefix = f"ashnova-{prefix}"
```

**変更箇所2: Cloud Runフィルタの厳密化** (Line 310-316):

```python
# 変更前
    for service in run_services:
        name = service.get("metadata", {}).get("name", "")
        if stack in name or "multicloud-auto-deploy" in name:
            append_resource(snapshot, "compute", name, name, region, "gcloud-cli")
```

```python
# 変更後
    for service in run_services:
        name = service.get("metadata", {}).get("name", "")
        if prefix in name:
            append_resource(snapshot, "compute", name, name, region, "gcloud-cli")
```

**変更箇所3: backend-bucketsフィルタの整理** (Line 277-291):

```python
# 変更前
    backend_buckets = run_json_command(
        ["gcloud", "compute", "backend-buckets", "list", "--format=json"]
    )
    for bucket in backend_buckets:
        name = bucket.get("name", "")
        bucket_name = bucket.get("bucketName", "")
        if stack in name or frontend_prefix in bucket_name:
            append_resource(
                snapshot,
                "cdn",
                name,
                name,
                "global",
                "gcloud-cli",
                {"bucketName": bucket_name},
            )
```

```python
# 変更後（prefixを使った統一的な判定に変更）
    backend_buckets = run_json_command(
        ["gcloud", "compute", "backend-buckets", "list", "--format=json"]
    )
    for bucket in backend_buckets:
        name = bucket.get("name", "")
        bucket_name = bucket.get("bucketName", "")
        if prefix in name or frontend_prefix in bucket_name:
            append_resource(
                snapshot,
                "cdn",
                name,
                name,
                "global",
                "gcloud-cli",
                {"bucketName": bucket_name},
            )
```

---

## 6. まとめ

### 6.1 変更のインパクト

- **LOW**: 既存のリソース名規則に変更なし
- **NO BREAKING CHANGE**: 命名規則が正しく運用されていれば影響なし
- **SAFE**: AWS/Azureと同じロジックに統一

### 6.2 次のアクション

1. ✅ このレポートを確認
2. ⏭️ 修正パッチを適用
3. ⏭️ テスト計画に従って検証
4. ⏭️ 図を再生成して視覚的に確認
