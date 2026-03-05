"""
Backend Integration Tests
Tests CRUD operations for all backends (AWS, GCP, Azure)
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.backends.aws_backend import AwsBackend
from app.backends.azure_backend import AzureBackend
from app.backends.base import BackendBase
from app.backends.gcp_backend import GcpBackend

# ─────────────────────────────────────────────────────────────────────────────
# Shared test data
# ─────────────────────────────────────────────────────────────────────────────
_NOW = datetime.now(timezone.utc).isoformat()

_SAMPLE_POST_ITEM = {
    "id": "mock-post-id",
    "postId": "mock-post-id",
    "userId": "test-user-1",
    "content": "Test post content",
    "tags": ["test", "integration"],
    "createdAt": _NOW,
    "updatedAt": _NOW,  # non-None so update_profile mock returns updated_at
    "imageUrls": [],
    "imageKeys": [],
    "isMarkdown": False,
    "nickname": None,
}


def _post_id(result: dict) -> str:
    return result.get("postId") or result.get("id") or result.get("post_id") or ""


def _user_id(result: dict) -> str:
    return result.get("userId") or result.get("user_id") or ""


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base (NOTE: NOT named Test* so pytest does not collect it directly)
# ─────────────────────────────────────────────────────────────────────────────
class BackendIntegrationBase:
    """Shared test logic for every backend; concrete subclasses are named Test*."""

    def get_backend(self):
        raise NotImplementedError

    # ── initialisation ───────────────────────────────────────────────────────
    def test_backend_initialization(self):
        backend = self.get_backend()
        assert backend is not None
        assert isinstance(backend, BackendBase)

    # ── create ───────────────────────────────────────────────────────────────
    def test_create_post_success(self, test_user, sample_post_body):
        backend = self.get_backend()
        result = backend.create_post(sample_post_body, test_user)

        assert result is not None
        assert isinstance(result, dict)
        assert _user_id(result) == test_user.user_id
        assert result.get("content") == sample_post_body.content
        assert result.get("tags") == sample_post_body.tags

    # ── list ─────────────────────────────────────────────────────────────────
    def test_list_posts_empty(self, test_user):
        backend = self.get_backend()
        posts, next_token = backend.list_posts(limit=20, next_token=None, tag=None)
        assert isinstance(posts, list)
        assert next_token is None or isinstance(next_token, str)

    def test_list_posts_with_tag_filter(self, test_user, sample_post_body):
        """Verify tag filter is accepted and returns correct types.
        Full state check (created post appears in list) requires a real DB.
        """
        backend = self.get_backend()
        backend.create_post(sample_post_body, test_user)
        posts, next_token = backend.list_posts(limit=20, next_token=None, tag="test")
        assert isinstance(posts, list)
        assert next_token is None or isinstance(next_token, str)

    # ── update: not universally implemented; override per-backend ────────────
    def test_update_post_success(self, test_user, sample_post_body, sample_update_body):
        pytest.skip("update_post not universally implemented; tested per-backend")

    def test_update_post_permission_denied(
        self, test_user, another_user, sample_post_body, sample_update_body
    ):
        pytest.skip("update_post not universally implemented; tested per-backend")

    def test_update_post_admin_can_update(
        self, test_user, admin_user, sample_post_body, sample_update_body
    ):
        pytest.skip("update_post not universally implemented; tested per-backend")

    # ── delete ───────────────────────────────────────────────────────────────
    def test_delete_post_success(self, test_user, sample_post_body):
        backend = self.get_backend()
        result = backend.create_post(sample_post_body, test_user)
        post_id = _post_id(result)

        delete_result = backend.delete_post(post_id, test_user)
        assert delete_result is not None
        # AWS: {"status": "deleted"}  GCP/Azure: {"message": "Post deleted ..."}
        assert (
            delete_result.get("status") == "deleted"
            or "deleted" in delete_result.get("message", "").lower()
        )

    def test_delete_post_permission_denied(
        self, test_user, another_user, sample_post_body
    ):
        backend = self.get_backend()
        result = backend.create_post(sample_post_body, test_user)
        post_id = _post_id(result)

        from fastapi import HTTPException
        with pytest.raises((PermissionError, HTTPException)):
            backend.delete_post(post_id, another_user)

    def test_delete_post_admin_can_delete(self, test_user, admin_user, sample_post_body):
        backend = self.get_backend()
        result = backend.create_post(sample_post_body, test_user)
        post_id = _post_id(result)
        delete_result = backend.delete_post(post_id, admin_user)
        assert delete_result is not None

    # ── profile ──────────────────────────────────────────────────────────────
    def test_get_profile_not_found(self, test_user):
        backend = self.get_backend()
        profile = backend.get_profile("non-existent-user")
        assert profile is not None
        assert profile.user_id == "non-existent-user"
        assert profile.nickname is None or profile.nickname == ""

    def test_update_profile_success(self, test_user, sample_profile_update):
        backend = self.get_backend()
        result = backend.update_profile(test_user, sample_profile_update)
        assert result is not None
        assert result.user_id == test_user.user_id
        assert result.updated_at is not None

    def test_get_profile_after_update(self, test_user, sample_profile_update):
        backend = self.get_backend()
        backend.update_profile(test_user, sample_profile_update)
        profile = backend.get_profile(test_user.user_id)
        assert profile is not None
        assert profile.user_id == test_user.user_id

    # ── upload URLs ──────────────────────────────────────────────────────────
    def test_generate_upload_urls(self, test_user):
        backend = self.get_backend()
        urls = backend.generate_upload_urls(count=2, user=test_user)
        assert isinstance(urls, list)
        assert len(urls) == 2
        for url_data in urls:
            assert "url" in url_data
            assert "key" in url_data
            assert isinstance(url_data["url"], str)
            assert isinstance(url_data["key"], str)


# ─────────────────────────────────────────────────────────────────────────────
# AWS
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.aws
class TestAwsBackend(BackendIntegrationBase):
    """Test AWS Backend (DynamoDB + S3)"""

    backend_class = AwsBackend

    def _make_table_mock(self):
        table = MagicMock()
        table.put_item.return_value = {}
        table.update_item.return_value = {}
        table.delete_item.return_value = {}
        table.get_item.return_value = {"ResponseMetadata": {}}

        # Simulate "list all posts" → empty; "lookup by PostIdIndex" → found
        def _query_side_effect(**kwargs):
            if kwargs.get("IndexName") == "PostIdIndex":
                post_id = (
                    kwargs.get("ExpressionAttributeValues", {}).get(":postId", "x")
                )
                return {
                    "Items": [
                        {
                            "PK": "POSTS",
                            "SK": f"{_NOW}#{post_id}",
                            "postId": post_id,
                            "userId": "test-user-1",
                            "content": "Test post content",
                            "tags": ["test", "integration"],
                            "createdAt": _NOW,
                        }
                    ]
                }
            return {"Items": [], "Count": 0}

        table.query.side_effect = _query_side_effect
        return table

    def get_backend(self):
        with patch("app.backends.aws_backend.boto3") as mock_boto3:
            mock_dynamodb = MagicMock()
            mock_table = self._make_table_mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto3.resource.return_value = mock_dynamodb

            mock_s3 = MagicMock()
            mock_s3.generate_presigned_url.return_value = (
                "https://test-bucket.s3.amazonaws.com/test-key?sig=test"
            )
            mock_boto3.client.return_value = mock_s3

            with patch.dict(
                "os.environ",
                {
                    "POSTS_TABLE_NAME": "test-posts",
                    "IMAGES_BUCKET_NAME": "test-images",
                    "AWS_REGION": "ap-northeast-1",
                },
            ):
                backend = AwsBackend()
                backend.table = mock_table
                backend.s3_client = mock_s3
                return backend

    # AWS does not implement update_post
    def test_update_post_success(self, test_user, sample_post_body, sample_update_body):
        pytest.skip("AwsBackend does not implement update_post")

    def test_update_post_permission_denied(
        self, test_user, another_user, sample_post_body, sample_update_body
    ):
        pytest.skip("AwsBackend does not implement update_post")

    def test_update_post_admin_can_update(
        self, test_user, admin_user, sample_post_body, sample_update_body
    ):
        pytest.skip("AwsBackend does not implement update_post")

    def test_list_posts_with_pagination(self):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# GCP helpers
# ─────────────────────────────────────────────────────────────────────────────
def _make_gcp_db_mock():
    """Return a MagicMock Firestore DB with sensible defaults."""
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = dict(_SAMPLE_POST_ITEM)
    mock_doc.id = "mock-post-id"

    col = MagicMock()
    col.order_by.return_value = col
    col.limit.return_value = col
    col.where.return_value = col
    col.start_after.return_value = col
    col.stream.return_value = iter([])
    col.document.return_value.get.return_value = mock_doc
    col.document.return_value.set.return_value = None
    col.document.return_value.update.return_value = None
    col.document.return_value.delete.return_value = None
    col.document.return_value.id = "mock-post-id"

    mock_db = MagicMock()
    mock_db.collection.return_value = col
    return mock_db


# ─────────────────────────────────────────────────────────────────────────────
# GCP
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.gcp
class TestGcpBackend(BackendIntegrationBase):
    """Test GCP Backend (Firestore + Cloud Storage)"""

    backend_class = GcpBackend

    def get_backend(self):
        with (
            patch("app.backends.gcp_backend.firestore") as mock_fs,
            patch("app.backends.gcp_backend.storage") as mock_st,
            patch("app.backends.gcp_backend.google") as mock_google,
            patch("app.backends.gcp_backend.settings") as mock_settings,
            patch("app.backends.gcp_backend._gcp_available", True),
        ):
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gcp_storage_bucket = "test-bucket"
            mock_settings.gcp_posts_collection = "posts"
            mock_settings.gcp_profiles_collection = "profiles"
            mock_settings.presigned_url_expiry = 300
            mock_settings.gcp_service_account = (
                "test-sa@test-project.iam.gserviceaccount.com"
            )

            mock_fs.Query = MagicMock()
            mock_fs.Query.DESCENDING = "DESCENDING"
            mock_fs.FieldFilter = MagicMock(return_value=MagicMock())

            mock_db = _make_gcp_db_mock()
            mock_fs.Client.return_value = mock_db

            mock_blob = MagicMock()
            mock_blob.generate_signed_url.return_value = (
                "https://storage.googleapis.com/test-bucket/key?sig=test"
            )
            mock_storage_client = MagicMock()
            mock_storage_client.bucket.return_value.blob.return_value = mock_blob
            mock_st.Client.return_value = mock_storage_client

            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_creds.token = "test-access-token"
            mock_google.auth.default.return_value = (mock_creds, None)
            mock_google.auth.transport.requests.Request.return_value = MagicMock()

            backend = GcpBackend()
            # Keep mocks alive beyond the with-block by re-attaching them
            backend.db = mock_db
            backend.storage_client = mock_storage_client
            backend._gcs_credentials = mock_creds
            return backend

    # GCP does not implement update_post
    def test_update_post_success(self, test_user, sample_post_body, sample_update_body):
        pytest.skip("GcpBackend does not implement update_post")

    def test_update_post_permission_denied(
        self, test_user, another_user, sample_post_body, sample_update_body
    ):
        pytest.skip("GcpBackend does not implement update_post")

    def test_update_post_admin_can_update(
        self, test_user, admin_user, sample_post_body, sample_update_body
    ):
        pytest.skip("GcpBackend does not implement update_post")


# ─────────────────────────────────────────────────────────────────────────────
# Azure helpers – stateful in-memory Cosmos DB mock
# ─────────────────────────────────────────────────────────────────────────────
class _StatefulCosmosContainer:
    """Minimal in-memory Cosmos DB container for unit tests."""

    def __init__(self, initial_items: list[dict] | None = None):
        self._store: dict[str, dict] = {}
        for item in (initial_items or []):
            key = item.get("id") or item.get("postId") or item.get("userId", "")
            self._store[key] = dict(item)

    def _not_found(self, item_id: str):
        try:
            from azure.cosmos import exceptions
            raise exceptions.CosmosResourceNotFoundError(
                message=f"Resource Not Found: {item_id}", response=None
            )
        except ImportError:
            raise KeyError(f"Not found: {item_id}")

    def read_item(self, item, partition_key=None):
        if item not in self._store:
            self._not_found(item)
        return dict(self._store[item])

    def create_item(self, body):
        key = body.get("id") or body.get("postId") or body.get("userId", "")
        self._store[key] = dict(body)
        return dict(body)

    def upsert_item(self, body):
        return self.create_item(body)

    def replace_item(self, item, body):
        key = body.get("id") or body.get("postId") or body.get("userId", item)
        self._store[key] = dict(body)
        return dict(body)

    def delete_item(self, item, partition_key=None):
        self._store.pop(item, None)

    def query_items(self, query, parameters=None, enable_cross_partition_query=False):
        return iter(list(self._store.values()))


def _make_azure_backend_with_patches():
    """Create AzureBackend with all external calls patched.  Returns the backend."""
    with (
        patch("app.backends.azure_backend.CosmosClient") as mock_cosmos_cls,
        patch("app.backends.azure_backend.settings") as mock_settings,
        patch("app.backends.azure_backend._cosmos_available", True),
        patch("app.backends.azure_backend._blob_available", True),
    ):
        mock_settings.cosmos_db_endpoint = "https://test.documents.azure.com:443/"
        mock_settings.cosmos_db_key = "test-cosmos-key"
        mock_settings.cosmos_db_database = "test-db"
        mock_settings.cosmos_db_container = "items"
        mock_settings.azure_storage_account_name = "testaccount"
        mock_settings.azure_storage_account_key = "test-storage-key"
        mock_settings.azure_storage_container = "images"
        mock_settings.presigned_url_expiry = 300

        posts_store = _StatefulCosmosContainer()
        profiles_store = _StatefulCosmosContainer()

        mock_db = MagicMock()
        mock_db.create_container_if_not_exists.side_effect = [posts_store, profiles_store]

        mock_client = MagicMock()
        mock_client.create_database_if_not_exists.return_value = mock_db
        mock_cosmos_cls.return_value = mock_client

        backend = AzureBackend()
        backend.posts_container = posts_store
        backend.profiles_container = profiles_store
        return backend


# ─────────────────────────────────────────────────────────────────────────────
# Azure
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.azure
class TestAzureBackend(BackendIntegrationBase):
    """Test Azure Backend (Cosmos DB + Blob Storage)"""

    backend_class = AzureBackend

    def get_backend(self):
        return _make_azure_backend_with_patches()

    # ── update_post (Azure has it) ───────────────────────────────────────────
    def test_update_post_success(self, test_user, sample_post_body, sample_update_body):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=test&sig=x"):
            backend = self.get_backend()
            create_result = backend.create_post(sample_post_body, test_user)
            post_id = _post_id(create_result)

            update_result = backend.update_post(post_id, sample_update_body, test_user)
            assert update_result is not None

    def test_update_post_permission_denied(
        self, test_user, another_user, sample_post_body, sample_update_body
    ):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=test&sig=x"):
            backend = self.get_backend()
            create_result = backend.create_post(sample_post_body, test_user)
            post_id = _post_id(create_result)

            from fastapi import HTTPException
            with pytest.raises((PermissionError, HTTPException)):
                backend.update_post(post_id, sample_update_body, another_user)

    def test_update_post_admin_can_update(
        self, test_user, admin_user, sample_post_body, sample_update_body
    ):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=test&sig=x"):
            backend = self.get_backend()
            create_result = backend.create_post(sample_post_body, test_user)
            post_id = _post_id(create_result)

            update_result = backend.update_post(post_id, sample_update_body, admin_user)
            assert update_result is not None

    # ── generate_upload_urls needs `generate_blob_sas` valid during call ─────
    def test_generate_upload_urls(self, test_user):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=2021&sig=test"):
            backend = self.get_backend()
            urls = backend.generate_upload_urls(count=2, user=test_user)
            assert isinstance(urls, list)
            assert len(urls) == 2
            for url_data in urls:
                assert "url" in url_data
                assert "key" in url_data
                assert isinstance(url_data["url"], str)
                assert isinstance(url_data["key"], str)

    # ── delete tests need `generate_blob_sas` for _resolve_image_urls ────────
    def test_delete_post_success(self, test_user, sample_post_body):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=test&sig=x"):
            backend = self.get_backend()
            result = backend.create_post(sample_post_body, test_user)
            post_id = _post_id(result)

            delete_result = backend.delete_post(post_id, test_user)
            assert delete_result is not None
            assert (
                delete_result.get("status") == "deleted"
                or "deleted" in delete_result.get("message", "").lower()
            )

    def test_delete_post_permission_denied(
        self, test_user, another_user, sample_post_body
    ):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=test&sig=x"):
            backend = self.get_backend()
            result = backend.create_post(sample_post_body, test_user)
            post_id = _post_id(result)

            from fastapi import HTTPException
            with pytest.raises((PermissionError, HTTPException)):
                backend.delete_post(post_id, another_user)

    def test_delete_post_admin_can_delete(self, test_user, admin_user, sample_post_body):
        with patch("app.backends.azure_backend.generate_blob_sas", return_value="sv=test&sig=x"):
            backend = self.get_backend()
            result = backend.create_post(sample_post_body, test_user)
            post_id = _post_id(result)

            delete_result = backend.delete_post(post_id, admin_user)
            assert delete_result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Performance / E2E placeholders
# ─────────────────────────────────────────────────────────────────────────────
class TestBackendPerformance:
    @pytest.mark.slow
    def test_bulk_post_creation(self, test_user, sample_post_body):
        pass

    @pytest.mark.slow
    def test_pagination_large_dataset(self, test_user):
        pass


class TestEndToEnd:
    def test_complete_post_lifecycle(
        self, test_user, sample_post_body, sample_update_body
    ):
        pass

    def test_multi_user_scenario(
        self, test_user, another_user, admin_user, sample_post_body
    ):
        pass
