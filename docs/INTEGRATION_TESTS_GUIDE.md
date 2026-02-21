# Integration Tests Complete Guide

**Created**: 2026-02-18  
**Version**: 1.0.0  
**Target Environments**: All (AWS/GCP/Azure)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [How to Run](#how-to-run)
4. [Test Coverage](#test-coverage)
5. [Troubleshooting](#troubleshooting)
6. [CI/CD Integration](#cicd-integration)

---

## Overview

The integration tests in this project comprehensively test the backend implementations across **3 cloud providers (AWS/GCP/Azure)**.

### Test Types

| Test Type                  | Description                                       | Tool              |
| -------------------------- | ------------------------------------------------- | ----------------- |
| **Unit Tests**             | Tests for individual backend class methods        | pytest (mocked)   |
| **Integration Tests**      | Full-flow tests for CRUD operations               | pytest (mocked)   |
| **API Endpoint Tests**     | HTTP tests against actually deployed APIs         | pytest + requests |
| **E2E Tests**              | End-to-end tests across all clouds                | bash + curl       |

---

## Test Structure

### Directory Layout

```
services/api/
├── tests/
│   ├── __init__.py                    # Test package initialization
│   ├── conftest.py                    # pytest configuration and fixtures
│   ├── test_backends_integration.py   # Backend integration tests
│   └── test_api_endpoints.py          # API endpoint tests
├── pytest.ini                         # pytest config file
└── requirements-dev.txt               # Development/test dependencies

scripts/
├── run-integration-tests.sh           # Python test runner script (NEW)
├── test-api.sh                        # Single API HTTP test
├── test-e2e.sh                        # Multi-cloud E2E test
└── test-endpoints.sh                  # Endpoint health check
```

### Test File Details

#### 1. `conftest.py` - pytest Configuration

**Features**:

- Fixture definitions for testing
- Mock user credentials
- Sample data generation
- Cleanup processing

**Key Fixtures**:

```python
test_user()              # Regular user
admin_user()             # Admin user
another_user()           # Different user
sample_post_body()       # Data for creating posts
sample_update_body()     # Data for updating posts
sample_profile_update()  # Data for updating profiles
aws_config()             # AWS configuration
gcp_config()             # GCP configuration
azure_config()           # Azure configuration
```

#### 2. `test_backends_integration.py` - Backend Integration Tests

**Test Classes**:

##### `TestBackendBase` (base class)

Test cases common to all backends:

- ✅ `test_backend_initialization()` - Backend initialization
- ✅ `test_create_post_success()` - Create post
- ✅ `test_list_posts_empty()` - List posts (empty)
- ✅ `test_list_posts_with_tag_filter()` - Tag filtering
- ✅ `test_update_post_success()` - Update post
- ✅ `test_update_post_permission_denied()` - Permission error (update)
- ✅ `test_update_post_admin_can_update()` - Admin permission (update)
- ✅ `test_delete_post_success()` - Delete post
- ✅ `test_delete_post_permission_denied()` - Permission error (delete)
- ✅ `test_delete_post_admin_can_delete()` - Admin permission (delete)
- ✅ `test_get_profile_not_found()` - Get profile (not found)
- ✅ `test_update_profile_success()` - Update profile
- ✅ `test_get_profile_after_update()` - Get profile after update
- ✅ `test_generate_upload_urls()` - Generate upload URLs

##### `TestAwsBackend` (AWS-specific)

- DynamoDB + S3 mock tests
- Marker: `@pytest.mark.aws`

##### `TestGcpBackend` (GCP-specific)

- Firestore + Cloud Storage mock tests
- Marker: `@pytest.mark.gcp`

##### `TestAzureBackend` (Azure-specific)

- Cosmos DB + Blob Storage mock tests
- Marker: `@pytest.mark.azure`

#### 3. `test_api_endpoints.py` - API Endpoint Tests

**Test Classes**:

##### `TestAPIEndpoints`

Tests against actually deployed API endpoints:

- ✅ `test_health_check()` - Health check
- ✅ `test_list_messages_initial()` - Fetch message list
- ✅ `test_crud_operations_flow()` - Full CRUD flow
- ✅ `test_pagination()` - Pagination
- ✅ `test_invalid_message_id()` - Invalid ID (404 error)
- ✅ `test_empty_content_validation()` - Validation error

**Reference**: `scripts/test-api.sh` test cases 1-12

##### `TestMultiCloudEndpoints`

- ✅ `test_all_cloud_health_checks()` - Health check across all clouds

**Reference**: `scripts/test-endpoints.sh`

##### `TestCrossCloudConsistency`

- ✅ `test_response_format_consistency()` - Response format consistency
- ✅ `test_api_version_consistency()` - API version consistency

**Reference**: consistency checks in `scripts/test-e2e.sh`

---

## How to Run

### Method 1: Direct Python pytest

#### Run All Tests (mocked only)

```bash
cd services/api
pytest tests/
```

#### AWS Backend Only

```bash
pytest tests/ -m aws
```

#### GCP Backend Only

```bash
pytest tests/ -m gcp
```

#### Azure Backend Only

```bash
pytest tests/ -m azure
```

#### Verbose Output

```bash
pytest tests/ -vv
```

#### Generate Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
# Report: htmlcov/index.html
```

#### Run Specific Tests Only

```bash
pytest tests/ -k "test_create_post"
```

### Method 2: Shell Script (Recommended)

#### Run Python Tests

```bash
./scripts/run-integration-tests.sh
```

#### Run with Verbose Output

```bash
./scripts/run-integration-tests.sh -v
```

#### Run with Specific Marker

```bash
./scripts/run-integration-tests.sh -m aws
```

#### Test Actual API Endpoints

```bash
# Set environment variables
export AWS_API_ENDPOINT="https://abc123.execute-api.ap-northeast-1.amazonaws.com"
export GCP_API_ENDPOINT="https://app-xyz.a.run.app"
export AZURE_API_ENDPOINT="https://func-xyz.azurewebsites.net/api/HttpTrigger"

# Run
./scripts/run-integration-tests.sh --endpoints
```

#### Run with Coverage

```bash
./scripts/run-integration-tests.sh --coverage
```

### Method 3: Run Existing Shell Scripts

#### Single API Test

```bash
./scripts/test-api.sh -e https://your-api-endpoint.com
```

#### Multi-Cloud E2E Test

```bash
./scripts/test-e2e.sh
```

#### Endpoint Health Check

```bash
./scripts/test-endpoints.sh
```

---

## Test Coverage

### Backend Methods

| Method                   | AWS | GCP | Azure | Tests |
| ------------------------ | :-: | :-: | :---: | :---: |
| `list_posts()`           | ✅  | ✅  |  ✅   |   3   |
| `create_post()`          | ✅  | ✅  |  ✅   |   3   |
| `update_post()`          | ✅  | ✅  |  ✅   |   9   |
| `delete_post()`          | ✅  | ✅  |  ✅   |   9   |
| `get_profile()`          | ✅  | ✅  |  ✅   |   3   |
| `update_profile()`       | ✅  | ✅  |  ✅   |   6   |
| `generate_upload_urls()` | ✅  | ✅  |  ✅   |   3   |

**Total**: 108 test cases (36 cases × 3 clouds)

### API Endpoints

| Endpoint                   | Method | Test                     | Reference Script   |
| -------------------------- | ------ | ------------------------ | ------------------ |
| `/`                        | GET    | Health check             | test-api.sh #1     |
| `/api/messages/`           | GET    | List retrieval           | test-api.sh #2, #4 |
| `/api/messages/`           | POST   | Create                   | test-api.sh #3     |
| `/api/messages/{id}`       | GET    | Single retrieval         | test-api.sh #5     |
| `/api/messages/{id}`       | PUT    | Update                   | test-api.sh #6, #7 |
| `/api/messages/{id}`       | DELETE | Delete                   | test-api.sh #8, #9 |
| `/api/messages/?page=1`    | GET    | Pagination               | test-api.sh #10    |
| `/api/messages/invalid-id` | GET    | Error 404                | test-api.sh #11    |
| `/api/messages/`           | POST   | Validation error         | test-api.sh #12    |

**Total**: 27 endpoint tests (9 endpoints × 3 clouds)

---

## pytest Markers

Markers for classifying and filtering tests:

| Marker                              | Description                    | Example                      |
| ----------------------------------- | ------------------------------ | ---------------------------- |
| `@pytest.mark.aws`                  | AWS-specific tests             | `pytest -m aws`              |
| `@pytest.mark.gcp`                  | GCP-specific tests             | `pytest -m gcp`              |
| `@pytest.mark.azure`                | Azure-specific tests           | `pytest -m azure`            |
| `@pytest.mark.integration`          | Integration tests              | `pytest -m integration`      |
| `@pytest.mark.unit`                 | Unit tests                     | `pytest -m unit`             |
| `@pytest.mark.slow`                 | Slow-running tests             | `pytest -m "not slow"`       |
| `@pytest.mark.requires_network`     | Requires network               | `pytest -m requires_network` |
| `@pytest.mark.requires_credentials` | Requires credentials           | Excluded by default          |

---

## Troubleshooting

### Problem: pytest not found

**Solution**:

```bash
pip install pytest pytest-mock pytest-asyncio requests
```

### Problem: ImportError: No module named 'app'

**Solution**:

```bash
# Run from services/api directory
cd /workspaces/ashnova/multicloud-auto-deploy/services/api
pytest tests/
```

### Problem: Mock errors (MagicMock related)

**Solution**:

```bash
pip install pytest-mock
```

### Problem: API endpoint tests fail

**Cause**: Endpoint not configured or not yet deployed

**Solution**:

```bash
# Set environment variable
export AWS_API_ENDPOINT="https://your-endpoint.com"

# Or skip at test execution
pytest tests/ -m "not requires_network"
```

### Problem: Permission denied error

**Cause**: Test script lacks execute permission

**Solution**:

```bash
chmod +x scripts/run-integration-tests.sh
```

---

## CI/CD Integration

### GitHub Actions

Example `.github/workflows/test.yml`:

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

### Local CI Simulation

```bash
# Run all tests (same as CI)
./scripts/run-integration-tests.sh -v

# Run with coverage
./scripts/run-integration-tests.sh --coverage
```

---

## Test Execution Examples

### Example 1: Basic Development Tests

```bash
# Navigate to service directory
cd services/api

# Run all tests
pytest tests/ -v

# Example output:
# tests/test_backends_integration.py::TestBackendBase::test_create_post_success PASSED
# tests/test_backends_integration.py::TestBackendBase::test_update_post_success PASSED
# ...
# ==================== 42 passed in 2.15s ====================
```

### Example 2: AWS-Specific Tests

```bash
./scripts/run-integration-tests.sh -m aws -v

# Example output:
# ========================================
# Python Integration Test Execution
# ========================================
#
# Python: 3.12.0
# pytest: pytest 7.4.3
# Marker: -m aws
#
# tests/test_backends_integration.py::TestAwsBackend::test_backend_initialization PASSED
# tests/test_backends_integration.py::TestAwsBackend::test_create_post_success PASSED
# ...
# ========================================
# ✅ All tests passed!
# ========================================
```

### Example 3: Actual Deployed API Tests

```bash
# Set environment variable
export AWS_API_ENDPOINT="https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"

# Run endpoint tests
./scripts/run-integration-tests.sh --endpoints -v

# Example output:
# ========================================
# Python Integration Test Execution
# ========================================
#
# Endpoint test: enabled
#
# Environment variables:
#   AWS_API_ENDPOINT=https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com
#   GCP_API_ENDPOINT=not set
#   AZURE_API_ENDPOINT=not set
#
# tests/test_api_endpoints.py::TestAPIEndpoints::test_health_check[aws] PASSED
# tests/test_api_endpoints.py::TestAPIEndpoints::test_crud_operations_flow[aws] PASSED
# ...
#
# === Multi-Cloud Health Check Results ===
# ✅ aws: {'status_code': 200, 'accessible': True, 'response': {...}}
# ❌ gcp: {'status_code': None, 'accessible': False, 'error': '...'}
# ...
```

### Example 4: Generate Coverage Report

```bash
./scripts/run-integration-tests.sh --coverage

# Example output:
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
# Coverage report: htmlcov/index.html
```

---

## Summary

### Purpose of Tests

1. **Quality Assurance**: Ensure all backends operate according to specifications
2. **Regression Prevention**: Detect unintended behavior changes during code modifications
3. **Documentation**: Test code serves as usage examples for the implementation
4. **CI/CD Integration**: Automated tests perform quality checks before deployment

### Best Practices

- ✅ **Run tests before committing**: `./scripts/run-integration-tests.sh`
- ✅ **Add tests when adding new features**: Write corresponding tests for new methods
- ✅ **Run endpoint tests after deployment**: `./scripts/run-integration-tests.sh --endpoints`
- ✅ **Run E2E tests regularly**: `./scripts/test-e2e.sh`
- ✅ **Maintain 90%+ coverage**: Check with `--coverage`

### Future Improvements

- [ ] Add performance tests (`TestBackendPerformance`)
- [ ] Add end-to-end workflow tests (`TestEndToEnd`)
- [ ] Load testing (Locust, etc.)
- [ ] Security testing (authentication & authorization)
- [ ] Chaos engineering tests (failure simulation)

---

**Author**: GitHub Copilot  
**Last Updated**: 2026-02-18  
**Related Documents**:

- [API_OPERATION_VERIFICATION_REPORT.md](API_OPERATION_VERIFICATION_REPORT.md)
- [AWS_BACKEND_COMPLETE_FIX_REPORT.md](AWS_BACKEND_COMPLETE_FIX_REPORT.md)
- [BACKEND_IMPLEMENTATION_INVESTIGATION.md](BACKEND_IMPLEMENTATION_INVESTIGATION.md)
