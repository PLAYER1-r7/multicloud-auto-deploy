"""Unit tests for app.backends.local_backend with mocked dependencies."""

import types
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

import app.backends.local_backend as lb
from app.auth import UserInfo
from app.models import CreatePostBody, ProfileUpdateRequest, UpdatePostBody


@pytest.fixture
def backend():
    instance = lb.LocalBackend.__new__(lb.LocalBackend)
    instance.table = Mock()
    instance.minio_client = None
    instance.table_name = "simple-sns-local"
    return instance


def _client_error(code: str):
    return ClientError({"Error": {"Code": code, "Message": code}}, "Op")


class TestInitPaths:
    def test_init_storage_without_endpoint(self, backend, monkeypatch):
        monkeypatch.setattr(lb.settings, "minio_endpoint", None)
        backend._init_storage()
        assert backend.minio_client is None

    def test_init_storage_minio_endpoint_with_http(self, backend, monkeypatch):
        """Test MinIO endpoint URL parsing for HTTP"""
        monkeypatch.setattr(lb.settings, "minio_endpoint", "http://minio:9000")
        # Simulate MinIO import error for fallback test
        with patch.dict("sys.modules", {"minio": None}):
            backend._init_storage()
        assert backend.minio_client is None

    def test_init_storage_minio_endpoint_with_https(self, backend, monkeypatch):
        """Test MinIO endpoint URL parsing for HTTPS"""
        monkeypatch.setattr(lb.settings, "minio_endpoint", "https://minio:9000")
        # Simulate MinIO import error for fallback test
        with patch.dict("sys.modules", {"minio": None}):
            backend._init_storage()
        assert backend.minio_client is None

    def test_init_storage_with_exception_falls_back(self, backend, monkeypatch):
        monkeypatch.setattr(lb.settings, "minio_endpoint", "http://localhost:9000")
        # ImportError path
        with patch.dict("sys.modules", {"minio": None}):
            backend._init_storage()
        assert backend.minio_client is None

    def test_ensure_table_already_exists(self, backend):
        client = Mock()
        client.describe_table.return_value = {"Table": {"TableName": "x"}}
        backend.dynamodb = SimpleNamespace(meta=SimpleNamespace(client=client))
        backend.table_name = "x"

        backend._ensure_table()

        client.create_table.assert_not_called()

    def test_ensure_table_create_when_missing(self, backend):
        client = Mock()
        client.describe_table.side_effect = [
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            {"Table": {"TableName": "x"}},
        ]
        backend.dynamodb = SimpleNamespace(meta=SimpleNamespace(client=client))
        backend.table_name = "x"

        with patch("app.backends.local_backend.time.sleep", return_value=None):
            backend._ensure_table()

        client.create_table.assert_called_once()

    def test_ensure_table_create_when_missing_with_wait_success(self, backend):
        """Test table creation with successful wait loop on first attempt"""
        client = Mock()
        client.describe_table.side_effect = [
            _client_error("ResourceNotFoundException"),
            # First attempt in wait loop succeeds
            {"Table": {"TableName": "x"}},
        ]
        backend.dynamodb = SimpleNamespace(meta=SimpleNamespace(client=client))
        backend.table_name = "x"

        with patch("app.backends.local_backend.time.sleep", return_value=None):
            backend._ensure_table()

        client.create_table.assert_called_once()

    def test_ensure_table_create_when_missing_with_wait_failure_all_attempts(
        self, backend
    ):
        """Test table creation where waiter never succeeds"""
        client = Mock()
        # ResourceNotFoundException on initial check and all wait attempts
        client.describe_table.side_effect = [
            _client_error("ResourceNotFoundException"),
            # Wait loop: all 20 attempts fail
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
            _client_error("ResourceNotFoundException"),
        ]
        backend.dynamodb = SimpleNamespace(meta=SimpleNamespace(client=client))
        backend.table_name = "x"

        with patch("app.backends.local_backend.time.sleep", return_value=None):
            backend._ensure_table()

        # Table creation should be called even if wait loop fails
        client.create_table.assert_called_once()

    def test_init_dynamodb_sets_resource_and_table(self, backend, monkeypatch):
        mock_table = Mock()
        mock_dynamo = Mock()
        mock_dynamo.Table.return_value = mock_table
        monkeypatch.setattr(lb.settings, "dynamodb_endpoint", "http://localhost:8001")
        monkeypatch.setattr(lb.settings, "dynamodb_table_name", "simple-sns-local")
        monkeypatch.setattr(lb.settings, "aws_region", "ap-northeast-1")

        with (
            patch.object(backend, "_ensure_table", return_value=None),
            patch(
                "app.backends.local_backend.boto3.resource", return_value=mock_dynamo
            ),
        ):
            backend._init_dynamodb()

        assert backend.table is mock_table
        assert backend.table_name == "simple-sns-local"


class TestHelpers:
    def test_build_image_urls(self, backend, monkeypatch):
        monkeypatch.setattr(lb.settings, "minio_bucket", "images")
        assert backend._build_image_urls([]) is None
        assert backend._build_image_urls(["a.jpg", "b.jpg"]) == [
            "/storage/images/a.jpg",
            "/storage/images/b.jpg",
        ]

    def test_item_to_post_maps_fields(self, backend, monkeypatch):
        monkeypatch.setattr(lb.settings, "minio_bucket", "images")
        post = backend._item_to_post(
            {
                "postId": "p1",
                "userId": "u1",
                "content": "hello",
                "isMarkdown": True,
                "tags": ["t1"],
                "imageKeys": ["k1"],
                "createdAt": "2026-01-01T00:00:00",
                "updatedAt": "2026-01-01T01:00:00",
                "nickname": "nick",
            }
        )
        assert post.id == "p1"
        assert post.user_id == "u1"
        assert post.is_markdown is True
        assert post.image_urls == ["/storage/images/k1"]

    def test_get_nickname_success_and_failure(self, backend):
        backend.table.query.return_value = {"Items": [{"nickname": "neo"}]}
        assert backend._get_nickname("u1") == "neo"

        backend.table.query.side_effect = RuntimeError("x")
        assert backend._get_nickname("u1") is None

    def test_get_post_item_by_id_found_and_not_found(self, backend):
        backend.table.query.return_value = {"Items": [{"postId": "p1"}]}
        item = backend._get_post_item_by_id("p1")
        assert item["postId"] == "p1"

        backend.table.query.return_value = {"Items": []}
        with pytest.raises(HTTPException) as exc:
            backend._get_post_item_by_id("missing")
        assert exc.value.status_code == 404


class TestPosts:
    def test_list_posts_with_filters_and_next_token(self, backend):
        backend.table.query.return_value = {
            "Items": [
                {
                    "postId": "p1",
                    "userId": "u1",
                    "content": "c1",
                    "createdAt": "2026-01-01T00:00:00",
                    "imageKeys": [],
                    "tags": ["x"],
                }
            ],
            "LastEvaluatedKey": {"SK": "token-1"},
        }
        with patch.object(backend, "_get_nickname", return_value="nick"):
            posts, token = backend.list_posts(limit=5, next_token="prev", tag="x")

        assert len(posts) == 1
        assert token == "token-1"
        assert posts[0].nickname == "nick"
        kwargs = backend.table.query.call_args.kwargs
        assert kwargs["ExclusiveStartKey"] == {"PK": "POSTS", "SK": "prev"}
        assert kwargs["ExpressionAttributeValues"][":tag"] == "x"

    def test_create_post(self, backend):
        body = CreatePostBody(
            content="hello", isMarkdown=True, imageKeys=["k1"], tags=["t"]
        )
        user = UserInfo(user_id="u1", email="u1@example.com", groups=None)

        with (
            patch("app.backends.local_backend.uuid.uuid4", return_value="uuid-1"),
            patch.object(backend, "_get_nickname", return_value="nick"),
        ):
            result = backend.create_post(body, user)

        backend.table.put_item.assert_called_once()
        assert result["postId"] == "uuid-1"
        assert result["userId"] == "u1"
        assert result["nickname"] == "nick"

    def test_get_post(self, backend):
        with (
            patch.object(
                backend,
                "_get_post_item_by_id",
                return_value={
                    "postId": "p1",
                    "userId": "u1",
                    "content": "hello",
                    "isMarkdown": False,
                    "tags": ["t"],
                    "imageKeys": ["k1"],
                    "createdAt": "2026-01-01T00:00:00",
                    "updatedAt": "2026-01-01T00:01:00",
                },
            ),
            patch.object(backend, "_get_nickname", return_value="nick"),
            patch.object(
                backend, "_build_image_urls", return_value=["/storage/images/k1"]
            ),
        ):
            result = backend.get_post("p1")

        assert result["postId"] == "p1"
        assert result["nickname"] == "nick"

    def test_update_post_forbidden(self, backend):
        body = UpdatePostBody(content="new")
        user = UserInfo(user_id="u2", email="u2@example.com", groups=None)
        with (
            patch.object(
                backend,
                "_get_post_item_by_id",
                return_value={"postId": "p1", "userId": "u1", "SK": "k"},
            ),
            pytest.raises(HTTPException) as exc,
        ):
            backend.update_post("p1", body, user)
        assert exc.value.status_code == 403

    def test_update_post_success(self, backend):
        body = UpdatePostBody(
            content="new", isMarkdown=True, imageKeys=["k2"], tags=["n"]
        )
        user = UserInfo(user_id="u1", email="u1@example.com", groups=None)

        with (
            patch.object(
                backend,
                "_get_post_item_by_id",
                return_value={"postId": "p1", "userId": "u1", "SK": "sk1"},
            ),
            patch.object(
                backend, "get_post", return_value={"postId": "p1", "content": "new"}
            ),
        ):
            result = backend.update_post("p1", body, user)

        backend.table.update_item.assert_called_once()
        assert result["postId"] == "p1"


class TestProfile:
    def test_get_profile_not_found_returns_default(self, backend):
        backend.table.query.return_value = {"Items": []}
        result = backend.get_profile("u1")
        assert result.user_id == "u1"
        assert result.nickname is None

    def test_get_profile_found_with_avatar(self, backend):
        backend.table.query.return_value = {
            "Items": [
                {
                    "userId": "u1",
                    "nickname": "neo",
                    "bio": "bio",
                    "avatarKey": "a.png",
                    "createdAt": "2026-01-01T00:00:00",
                    "updatedAt": "2026-01-01T01:00:00",
                }
            ]
        }
        with patch.object(
            backend, "_build_image_urls", return_value=["/storage/images/a.png"]
        ):
            result = backend.get_profile("u1")
        assert result.nickname == "neo"
        assert result.avatar_url == "/storage/images/a.png"

    def test_update_profile_new_and_existing(self, backend):
        user = UserInfo(user_id="u1", email="u1@example.com", groups=None)
        body = ProfileUpdateRequest(nickname="neo", bio="bio", avatarKey="a.png")

        backend.table.get_item.return_value = {}
        with patch.object(
            backend, "get_profile", return_value=SimpleNamespace(user_id="u1")
        ):
            result = backend.update_profile(user, body)
        assert result.user_id == "u1"

        backend.table.get_item.return_value = {
            "Item": {
                "createdAt": "2025-01-01T00:00:00",
                "nickname": "old",
                "bio": "oldbio",
                "avatarKey": "old.png",
            }
        }
        with patch.object(
            backend, "get_profile", return_value=SimpleNamespace(user_id="u1")
        ):
            backend.update_profile(user, ProfileUpdateRequest())

        assert backend.table.put_item.call_count >= 2


class TestUploadUrlsAndLikes:
    def test_generate_upload_urls_without_minio(self, backend):
        user = UserInfo(user_id="u1", email=None, groups=None)
        with patch("app.backends.local_backend.uuid.uuid4", side_effect=["id1", "id2"]):
            urls = backend.generate_upload_urls(2, user)
        assert len(urls) == 2
        assert urls[0]["key"].endswith("id1.jpg")

    def test_generate_upload_urls_with_minio_signing(self, backend, monkeypatch):
        backend.minio_client = object()
        user = UserInfo(user_id="u1", email=None, groups=None)
        monkeypatch.setattr(lb.settings, "minio_access_key", "ak")
        monkeypatch.setattr(lb.settings, "minio_secret_key", "sk")
        monkeypatch.setattr(lb.settings, "minio_bucket", "images")
        monkeypatch.setattr(lb.settings, "presigned_url_expiry", 300)

        signer = Mock()
        signer.generate_presigned_url.return_value = "http://minio:9000/images/key"
        with (
            patch("app.backends.local_backend.boto3.client", return_value=signer),
            patch("app.backends.local_backend.uuid.uuid4", return_value="id1"),
        ):
            urls = backend.generate_upload_urls(1, user)

        assert urls[0]["url"].startswith("/storage")

    def test_generate_upload_urls_signing_error(self, backend, monkeypatch):
        backend.minio_client = object()
        user = UserInfo(user_id="u1", email=None, groups=None)
        monkeypatch.setattr(lb.settings, "minio_access_key", "ak")
        monkeypatch.setattr(lb.settings, "minio_secret_key", "sk")
        monkeypatch.setattr(lb.settings, "minio_bucket", "images")
        monkeypatch.setattr(lb.settings, "presigned_url_expiry", 300)

        signer = Mock()
        signer.generate_presigned_url.side_effect = RuntimeError("boom")
        with (
            patch("app.backends.local_backend.boto3.client", return_value=signer),
            patch("app.backends.local_backend.uuid.uuid4", return_value="id1"),
            pytest.raises(HTTPException) as exc,
        ):
            backend.generate_upload_urls(1, user)
        assert exc.value.status_code == 500

    def test_like_and_unlike(self, backend):
        user = UserInfo(user_id="u1", email=None, groups=None)
        assert backend.like_post("p1", user) == {"post_id": "p1", "liked": True}
        assert backend.unlike_post("p1", user) == {"post_id": "p1", "liked": False}


class TestDeletePostSqlPath:
    @staticmethod
    def _fake_sqlalchemy_module():
        module = types.ModuleType("sqlalchemy")

        def text(query):
            return query

        module.text = text
        return module

    def test_delete_post_sql_success(self, backend):
        user = UserInfo(user_id="u1", email=None, groups=None)

        row_result = Mock()
        row_result.fetchone.side_effect = [("u1",), None]

        conn = Mock()
        conn.execute.return_value = row_result

        @contextmanager
        def _cm():
            yield conn

        backend._get_connection = _cm

        fake_sqlalchemy = self._fake_sqlalchemy_module()
        with patch.dict("sys.modules", {"sqlalchemy": fake_sqlalchemy}):
            result = backend.delete_post("p1", user)
        assert result["message"] == "Post deleted successfully"

    def test_delete_post_sql_forbidden_and_not_found(self, backend):
        non_admin = UserInfo(user_id="u2", email=None, groups=None)
        admin = UserInfo(user_id="admin", email=None, groups=["Admins"])

        # not found
        row_result = Mock()
        row_result.fetchone.return_value = None
        conn = Mock()
        conn.execute.return_value = row_result

        @contextmanager
        def cm_not_found():
            yield conn

        backend._get_connection = cm_not_found
        fake_sqlalchemy = self._fake_sqlalchemy_module()
        with (
            patch.dict("sys.modules", {"sqlalchemy": fake_sqlalchemy}),
            pytest.raises(HTTPException) as exc,
        ):
            backend.delete_post("missing", non_admin)
        assert exc.value.status_code == 404

        # forbidden
        row_result2 = Mock()
        row_result2.fetchone.return_value = ("owner",)
        conn2 = Mock()
        conn2.execute.return_value = row_result2

        @contextmanager
        def cm_forbidden():
            yield conn2

        backend._get_connection = cm_forbidden
        with (
            patch.dict("sys.modules", {"sqlalchemy": fake_sqlalchemy}),
            pytest.raises(HTTPException) as exc2,
        ):
            backend.delete_post("p1", non_admin)
        assert exc2.value.status_code == 403

        # admin should pass
        with patch.dict("sys.modules", {"sqlalchemy": fake_sqlalchemy}):
            result = backend.delete_post("p1", admin)
        assert result["message"] == "Post deleted successfully"
