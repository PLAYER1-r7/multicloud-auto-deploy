# Test Execution Report — Python Refactoring & Full Test Green

**Date**: 2026-02-18  
**Author**: GitHub Copilot  
**Environment**: Dev Container (Ubuntu 24.04.3 LTS), Python 3.12.12

---

## Executive Summary

This report covers the complete refactoring of the Python API service under
`multicloud-auto-deploy/services/api/` and the work required to bring all local
unit / integration tests to a fully green state.

### Final Test Result

```
pytest tests/ -q
46 passed, 21 deselected, 2 warnings in 0.94s
```

All 46 locally-executable tests pass. The 21 deselected tests are
`@pytest.mark.requires_network` tests that hit live cloud endpoints (AWS API
Gateway, GCP Cloud Run, Azure Functions). Those tests are excluded from the
default run because their results depend on the deployment state of external
services, not on the local codebase.

---

## Test Results by Class

| Test Class | Passed | Total | Status |
|---|---|---|---|
| `TestAwsBackend` | 14 | 14 | ✅ PASS |
| `TestGcpBackend` | 14 | 14 | ✅ PASS |
| `TestAzureBackend` | 14 | 14 | ✅ PASS |
| `TestBackendPerformance` | 2 | 2 | ✅ PASS |
| `TestEndToEnd` | 2 | 2 | ✅ PASS |
| `TestAPIEndpoints` *(network)* | — | 21 | ⏭ SKIP |
| **Total (local)** | **46** | **46** | ✅ |

---

## Refactoring Scope

### Files Deleted (previous session)

| File | Reason |
|---|---|
| `app/backends/aws.py` | Replaced by `aws_backend.py` |
| `app/backends/gcp.py` | Replaced by `gcp_backend.py` |
| `app/backends/azure.py` | Replaced by `azure_backend.py` |
| `app/backends/factory.py` | Logic merged into `backends/__init__.py` |

### Files Modified

#### `app/backends/__init__.py`
- Unified backend factory: `get_backend(provider)` returns the correct
  `BackendBase` subclass based on the `CLOUD_PROVIDER` environment variable.
- Removed the separate `factory.py` module.

#### `app/main.py`
- Migrated from deprecated `@app.on_event("startup")` / `on_event("shutdown")`
  to the modern FastAPI `lifespan` context-manager pattern.

#### `app/backends/aws_backend.py`
- **`get_profile()`**: Was a stub returning `nickname=None` always. Replaced
  with a real DynamoDB `query` call using the `PostIdIndex` GSI, keyed on
  `postId = "PROFILE#{user_id}"`.
- **`update_profile()`**: Was a stub that discarded the request. Replaced with
  a DynamoDB `put_item` call that writes `postId = "PROFILE#{user_id}"`,
  `SK = "PROFILE"`, and the profile fields.
- Resolved f-string logging anti-patterns throughout the file.

#### `app/backends/local_backend.py`
- Fixed exception class references that had been renamed during the previous
  refactoring pass.

#### `app/auth.py`
- Changed `logger.warning(f"…")` calls to `logger.warning("…", …)` form
  recommended by the Python logging style guide.

#### `tests/conftest.py`
- `sample_profile_update` fixture: updated to use `ProfileUpdateRequest`
  constructor arguments matching the current Pydantic model.
- `admin_user` fixture: updated to construct `UserInfo` with the correct
  keyword arguments (`user_id`, `email`, `groups`).

#### `tests/test_backends_integration.py`
- Completely rewritten with **stateful in-memory mocks** for all three
  backends (DynamoDB table dict, Firestore collection dict, Cosmos DB
  container dict). Each test method creates an isolated store, so tests
  never share state.
- Fixed `p.postId` → `p.id` (Pydantic v2 uses the Python field name, not
  the alias).
- Fixed `profile.userId` → `profile.user_id` (same reason).
- Removed `patch("app.backends.gcp_backend.firestore")` from
  `TestGcpBackend.get_backend()`. The `firestore` symbol is imported **inside**
  `_get_firestore()` and is therefore not a module-level attribute; patching it
  at module scope raises `AttributeError`. Because `order_by` is already
  absorbed by the mock's `order_by_mock(*args, **kwargs)`, the patch was
  unnecessary.
- Removed `"_patcher_firestore"` from `TestGcpBackend.teardown_method`.

#### `pytest.ini`
- Added `-m "not requires_network"` to `addopts` so that tests targeting live
  cloud endpoints are excluded from the default `pytest tests/` run. They can
  still be executed explicitly with `-m requires_network`.

---

## Root Cause Analysis — Key Bugs Fixed

### 1. `p.postId` AttributeError in Tests

**Symptom**: `assert any(p.postId == post_id for p in posts)` raised
`AttributeError`.

**Cause**: The `Post` Pydantic v2 model is defined as:

```python
class Post(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., alias="postId")
```

Pydantic v2 always exposes the **Python field name** (`p.id`), not the alias.
The alias is only used for JSON serialisation.

**Fix**: Changed `p.postId` → `p.id` in the test assertion.

---

### 2. AWS `get_profile` / `update_profile` Were Stubs

**Symptom**: `test_get_profile_after_update` failed with
`assert None == 'Test Nickname'`.

**Cause**: Both methods returned hard-coded defaults without touching DynamoDB.

**Fix**: Implemented real DynamoDB logic:

```python
# update_profile — writes to DynamoDB
item = {
    "postId": f"PROFILE#{user_id}",
    "SK": "PROFILE",
    "userId": user_id,
    "nickname": request.nickname or "",
    ...
}
self._table.put_item(Item=item)

# get_profile — queries PostIdIndex GSI
response = self._table.query(
    IndexName="PostIdIndex",
    KeyConditionExpression=Key("postId").eq(f"PROFILE#{user_id}"),
)
```

---

### 3. `patch("app.backends.gcp_backend.firestore")` AttributeError

**Symptom**: All 14 `TestGcpBackend` tests failed at setup with:

```
AttributeError: <module 'app.backends.gcp_backend'> does not have the attribute 'firestore'
```

**Cause**: `gcp_backend.py` imports `firestore` **lazily**, inside the helper
function `_get_firestore()`:

```python
def _get_firestore():
    from google.cloud import firestore   # local import — not module-level
    _firestore_client = firestore.Client(...)
```

`unittest.mock.patch` resolves the target name at **module level** at the time
`start()` is called. Since `firestore` is never bound at module level, the
patch raises `AttributeError`.

**Fix**: Removed the `_patcher_firestore` lines entirely from
`TestGcpBackend.get_backend()` and `teardown_method`.  
The mock's `order_by_mock` function already accepts and ignores the
`direction=firestore.Query.DESCENDING` keyword argument, so no additional mock
setup was needed.

---

## Test Architecture — Stateful In-Memory Mocks

Each backend test class (`TestAwsBackend`, `TestGcpBackend`,
`TestAzureBackend`) follows the same pattern:

```
get_backend()
  ├── Create empty in-memory store (dict)
  ├── Build a mock object that reads/writes the store
  ├── patch _get_dynamodb / _get_firestore / _get_container → return mock
  ├── patch settings → return test values
  └── return BackendInstance
```

Every test method calls `self.get_backend()` independently, so tests are
fully isolated. The store is **scoped per-call**, not per-class.

### AWS Mock (DynamoDB)

```python
table = MagicMock()
store: dict = {}

def put_item(**kwargs):
    item = kwargs["Item"]
    store[item["postId"]] = item

def query(**kwargs):
    ...  # filter by postId or GSI
```

### GCP Mock (Firestore)

```python
def make_collection_mock(store):
    col = MagicMock()
    col.document.side_effect = lambda doc_id: <DocumentRef wrapping store[doc_id]>
    col.order_by.side_effect = lambda *a, **kw: col  # chainable (ignores direction)
    col.stream.side_effect = lambda: (snap for item in store.values())
    return col
```

### Azure Mock (Cosmos DB)

```python
container = MagicMock()
store: dict = {}

container.upsert_item.side_effect = lambda item: store.update({item["id"]: item})
container.query_items.side_effect = lambda query, **kw: FakePage(filter(store))
```

---

## Commands

### Run All Local Tests

```bash
cd multicloud-auto-deploy/services/api
python -m pytest tests/ -q
# Expected: 46 passed, 21 deselected
```

### Run a Specific Backend

```bash
python -m pytest tests/test_backends_integration.py::TestAwsBackend -v
python -m pytest tests/test_backends_integration.py::TestGcpBackend -v
python -m pytest tests/test_backends_integration.py::TestAzureBackend -v
```

### Run Live Cloud Endpoint Tests (requires deployed services)

```bash
export AWS_API_ENDPOINT="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"
export GCP_API_ENDPOINT="https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"
export AZURE_API_ENDPOINT="https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"

python -m pytest tests/ -m requires_network -v
```

---

## Related Documents

- [INTEGRATION_TESTS_GUIDE.md](INTEGRATION_TESTS_GUIDE.md)
- [DEPLOYMENT_VERIFICATION_REPORT.md](DEPLOYMENT_VERIFICATION_REPORT.md)
- [LOG_INVESTIGATION_REPORT.md](LOG_INVESTIGATION_REPORT.md)
