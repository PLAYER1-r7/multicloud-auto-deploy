"""Unit tests for AwsBackend / AzureBackend / GcpBackend with mocked services."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import app.backends.aws_backend as aws_mod
import app.backends.azure_backend as azure_mod
import app.backends.gcp_backend as gcp_mod
from app.auth import UserInfo
from app.models import CreatePostBody, ProfileUpdateRequest


@pytest.fixture
def aws_backend():
    backend = aws_mod.AwsBackend.__new__(aws_mod.AwsBackend)
    backend.s3_client = Mock()
    backend.table = Mock()
    backend.table_name = "posts"
    backend.bucket_name = "bucket"
    return backend


@pytest.fixture
def azure_backend():
    backend = azure_mod.AzureBackend.__new__(azure_mod.AzureBackend)
    backend.posts_container = Mock()
    backend.profiles_container = Mock()
    backend.storage_account = "acct"
    backend.storage_key = "key"
    backend.images_container = "images"
    return backend


@pytest.fixture
def gcp_backend():
    backend = gcp_mod.GcpBackend.__new__(gcp_mod.GcpBackend)
    backend.db = Mock()
    backend.storage_client = Mock()
    backend.bucket_name = "bucket"
    backend.posts_collection = "posts"
    backend.profiles_collection = "profiles"
    backend._gcs_credentials = SimpleNamespace(valid=True, token="tok")
    backend._gcs_auth_request = object()
    return backend


class TestAwsBackend:
    def test_init_requires_table_name(self, monkeypatch):
        monkeypatch.setattr(aws_mod.boto3, "resource", lambda *_: Mock())
        monkeypatch.setattr(aws_mod.boto3, "client", lambda *_: Mock())
        monkeypatch.delenv("POSTS_TABLE_NAME", raising=False)
        with pytest.raises(ValueError):
            aws_mod.AwsBackend()

    def test_resolve_image_urls_handles_https_http_and_key(self, aws_backend):
        aws_backend._key_to_presigned_url = Mock(return_value="https://signed/key")
        result = aws_backend._resolve_image_urls(
            [
                "https://already",
                "http://insecure",
                "plain-key",
                None,
            ]
        )
        assert result == ["https://already", "https://signed/key"]

    def test_list_posts_with_next_token_and_tag(self, aws_backend):
        aws_backend._resolve_image_urls = Mock(return_value=["https://img"])
        aws_backend.table.query.return_value = {
            "Items": [
                {
                    "postId": "p1",
                    "userId": "u1",
                    "content": "c",
                    "createdAt": "2026-01-01T00:00:00",
                    "tags": ["x"],
                    "imageKeys": ["k1"],
                }
            ],
            "LastEvaluatedKey": {"SK": "next-sk"},
        }
        posts, token = aws_backend.list_posts(limit=5, next_token="prev", tag="x")
        assert len(posts) == 1
        assert token == "next-sk"
        kwargs = aws_backend.table.query.call_args.kwargs
        assert kwargs["ExclusiveStartKey"] == {"PK": "POSTS", "SK": "prev"}
        assert kwargs["ExpressionAttributeValues"][":tag"] == "x"

    def test_create_post_success(self, aws_backend):
        body = CreatePostBody(content="hello", tags=["t"], imageKeys=["k1"])
        user = UserInfo(user_id="u1", email=None, groups=None)
        aws_backend.table.get_item.return_value = {"Item": {"nickname": "neo"}}
        aws_backend._resolve_image_urls = Mock(return_value=["https://img"])

        with patch("app.backends.aws_backend.uuid.uuid4", return_value="id-1"):
            result = aws_backend.create_post(body, user)

        assert result["postId"] == "id-1"
        assert result["nickname"] == "neo"
        aws_backend.table.put_item.assert_called_once()

    def test_delete_post_permission_and_success(self, aws_backend):
        user = UserInfo(user_id="u1", email=None, groups=None)
        admin = UserInfo(user_id="admin", email=None, groups=["Admins"])

        aws_backend.table.query.return_value = {
            "Items": [{"postId": "p1", "SK": "sk", "userId": "owner"}]
        }
        with pytest.raises(PermissionError):
            aws_backend.delete_post("p1", user)

        result = aws_backend.delete_post("p1", admin)
        assert result["status"] == "deleted"
        aws_backend.table.delete_item.assert_called()

    def test_generate_upload_urls_uses_content_types(self, aws_backend):
        user = UserInfo(user_id="u1", email=None, groups=None)
        aws_backend.s3_client.generate_presigned_url.return_value = "https://put-url"
        with patch("app.backends.aws_backend.uuid.uuid4", side_effect=["id1", "id2"]):
            urls = aws_backend.generate_upload_urls(
                2, user, ["image/png", "image/heic"]
            )
        assert urls[0]["key"].endswith("id1.png")
        assert urls[1]["key"].endswith("id2.heic")

    def test_generate_upload_urls_requires_bucket(self, aws_backend):
        aws_backend.bucket_name = ""
        with pytest.raises(ValueError):
            aws_backend.generate_upload_urls(
                1, UserInfo(user_id="u", email=None, groups=None)
            )

    def test_get_post_not_found(self, aws_backend):
        aws_backend.table.query.return_value = {"Items": []}
        assert aws_backend.get_post("missing") is None

    def test_get_profile_not_found_and_update_profile(self, aws_backend):
        aws_backend.table.get_item.return_value = {}
        profile = aws_backend.get_profile("u1")
        assert profile.user_id == "u1"

        user = UserInfo(user_id="u1", email=None, groups=None)
        result = aws_backend.update_profile(user, ProfileUpdateRequest(nickname="neo"))
        assert result.nickname == "neo"


class TestAzureBackend:
    def test_init_success(self, monkeypatch):
        monkeypatch.setattr(azure_mod, "_cosmos_available", True)
        monkeypatch.setattr(
            azure_mod, "PartitionKey", lambda path: {"path": path}, raising=False
        )

        posts_container = Mock()
        profiles_container = Mock()
        fake_db = Mock()
        fake_db.create_container_if_not_exists.side_effect = [
            posts_container,
            profiles_container,
        ]
        fake_client = Mock()
        fake_client.create_database_if_not_exists.return_value = fake_db
        monkeypatch.setattr(
            azure_mod, "CosmosClient", lambda endpoint, key: fake_client, raising=False
        )

        monkeypatch.setattr(azure_mod.settings, "cosmos_db_endpoint", "https://cosmos")
        monkeypatch.setattr(azure_mod.settings, "cosmos_db_key", "key")
        monkeypatch.setattr(azure_mod.settings, "cosmos_db_database", "db")
        monkeypatch.setattr(azure_mod.settings, "azure_storage_account_name", "acct")
        monkeypatch.setattr(azure_mod.settings, "azure_storage_account_key", "sk")
        monkeypatch.setattr(azure_mod.settings, "azure_storage_container", "images")

        backend = azure_mod.AzureBackend()
        assert backend.posts_container is posts_container
        assert backend.profiles_container is profiles_container
        assert backend.storage_account == "acct"

    def test_init_import_and_config_guards(self, monkeypatch):
        monkeypatch.setattr(azure_mod, "_cosmos_available", False)
        with pytest.raises(ImportError):
            azure_mod.AzureBackend()

        monkeypatch.setattr(azure_mod, "_cosmos_available", True)
        monkeypatch.setattr(azure_mod.settings, "cosmos_db_endpoint", None)
        monkeypatch.setattr(azure_mod.settings, "cosmos_db_key", None)
        with pytest.raises(ValueError):
            azure_mod.AzureBackend()

    def test_blob_key_to_read_sas_url_fallback(self, azure_backend, monkeypatch):
        monkeypatch.setattr(azure_mod, "_blob_available", False)
        azure_backend.storage_key = None
        url = azure_backend._blob_key_to_read_sas_url("a.png")
        assert url.endswith("/images/a.png")

    def test_resolve_image_urls(self, azure_backend):
        azure_backend._blob_key_to_read_sas_url = Mock(return_value="https://sas")
        result = azure_backend._resolve_image_urls(
            [
                "https://acct.blob.core.windows.net/images/path/a.png",
                "https://external/image.png",
                "http://insecure",
                "blob-key",
            ]
        )
        assert result == ["https://sas", "https://external/image.png", "https://sas"]

    def test_item_to_post(self, azure_backend):
        azure_backend._resolve_image_urls = Mock(return_value=["https://sas"])
        post = azure_backend._item_to_post(
            {
                "id": "p1",
                "userId": "u1",
                "content": "c",
                "isMarkdown": True,
                "imageKeys": ["k1"],
                "tags": ["t"],
                "createdAt": "2026-01-01T00:00:00",
            }
        )
        assert post.id == "p1"
        assert post.user_id == "u1"
        assert post.image_urls == ["https://sas"]

    def test_generate_upload_urls(self, azure_backend, monkeypatch):
        monkeypatch.setattr(azure_mod, "_blob_available", True)
        monkeypatch.setattr(
            azure_mod,
            "BlobSasPermissions",
            lambda **kwargs: kwargs,
            raising=False,
        )
        monkeypatch.setattr(azure_mod.settings, "presigned_url_expiry", 300)
        monkeypatch.setattr(
            azure_mod, "generate_blob_sas", lambda **kwargs: "sas-token", raising=False
        )

        user = UserInfo(user_id="u1", email=None, groups=None)
        with patch("app.backends.azure_backend.uuid.uuid4", return_value="id1"):
            urls = azure_backend.generate_upload_urls(1, user, ["image/png"])

        assert urls[0]["key"] == "u1/id1.png"
        assert "sas-token" in urls[0]["url"]

    def test_get_profile_not_found_and_update_profile(self, azure_backend, monkeypatch):
        class NotFoundError(Exception):
            pass

        monkeypatch.setattr(
            azure_mod,
            "cosmos_exceptions",
            SimpleNamespace(CosmosResourceNotFoundError=NotFoundError),
            raising=False,
        )

        azure_backend.profiles_container.read_item.side_effect = NotFoundError()
        p = azure_backend.get_profile("u1")
        assert p.user_id == "u1"

        user = UserInfo(user_id="u1", email=None, groups=None)
        body = ProfileUpdateRequest(nickname="neo", bio="bio", avatarKey="a.png")
        azure_backend.profiles_container.read_item.side_effect = NotFoundError()
        with patch.object(
            azure_backend, "get_profile", return_value=SimpleNamespace(user_id="u1")
        ):
            res = azure_backend.update_profile(user, body)
        assert res.user_id == "u1"

    def test_list_posts_variants(self, azure_backend):
        azure_backend.posts_container.query_items.return_value = [
            {
                "id": "p1",
                "userId": "u1",
                "content": "c1",
                "createdAt": "2026-01-01T00:00:00",
            },
            {
                "id": "p2",
                "userId": "u2",
                "content": "c2",
                "createdAt": "2026-01-01T00:00:01",
            },
        ]
        azure_backend._item_to_post = Mock(
            side_effect=lambda x: SimpleNamespace(id=x.get("id"))
        )

        posts, token = azure_backend.list_posts(limit=1, next_token="bad", tag=None)
        assert len(posts) == 1
        assert token == "1"

    def test_get_post_none_and_delete_post_paths(self, azure_backend, monkeypatch):
        class NotFoundError(Exception):
            pass

        monkeypatch.setattr(
            azure_mod,
            "cosmos_exceptions",
            SimpleNamespace(CosmosResourceNotFoundError=NotFoundError),
            raising=False,
        )

        azure_backend.posts_container.read_item.side_effect = Exception("x")
        assert azure_backend.get_post("p1") is None

        azure_backend.posts_container.read_item.side_effect = NotFoundError()
        with pytest.raises(Exception) as exc:
            azure_backend.delete_post(
                "p1", UserInfo(user_id="u", email=None, groups=None)
            )
        assert exc.value.status_code == 404

        azure_backend.posts_container.read_item.side_effect = None
        azure_backend.posts_container.read_item.return_value = {"userId": "owner"}
        with pytest.raises(Exception) as exc2:
            azure_backend.delete_post(
                "p1", UserInfo(user_id="u", email=None, groups=None)
            )

        assert exc2.value.status_code == 403

    def test_create_post_and_get_profile_error_path(self, azure_backend, monkeypatch):
        monkeypatch.setattr(
            azure_mod,
            "cosmos_exceptions",
            SimpleNamespace(
                CosmosResourceNotFoundError=type("NotFound", (Exception,), {})
            ),
            raising=False,
        )

        user = UserInfo(user_id="u1", email=None, groups=None)
        body = CreatePostBody(content="hello", imageKeys=["k1"])

        azure_backend.profiles_container.read_item.side_effect = RuntimeError(
            "profile read failed"
        )
        azure_backend._resolve_image_urls = Mock(return_value=["https://img"])
        with patch("app.backends.azure_backend.uuid.uuid4", return_value="id1"):
            created = azure_backend.create_post(body, user)
        assert created["postId"] == "id1"

        azure_backend.profiles_container.read_item.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            azure_backend.get_profile("u1")

    def test_generate_upload_urls_import_guard(self, azure_backend, monkeypatch):
        monkeypatch.setattr(azure_mod, "_blob_available", False)
        with pytest.raises(ImportError):
            azure_backend.generate_upload_urls(
                1, UserInfo(user_id="u1", email=None, groups=None)
            )


class TestGcpBackend:
    def test_init_success_and_fallback_credentials(self, monkeypatch):
        monkeypatch.setattr(gcp_mod, "_gcp_available", True)

        fake_firestore_client = Mock()
        fake_storage_client = Mock()
        monkeypatch.setattr(
            gcp_mod,
            "firestore",
            SimpleNamespace(Client=lambda project: fake_firestore_client),
            raising=False,
        )
        monkeypatch.setattr(
            gcp_mod,
            "storage",
            SimpleNamespace(Client=lambda project: fake_storage_client),
            raising=False,
        )
        fake_google = SimpleNamespace(
            auth=SimpleNamespace(
                default=lambda: (SimpleNamespace(valid=True, token="tok"), "proj"),
                transport=SimpleNamespace(
                    requests=SimpleNamespace(Request=lambda: object())
                ),
            )
        )
        monkeypatch.setattr(gcp_mod, "google", fake_google, raising=False)
        monkeypatch.setattr(gcp_mod.settings, "gcp_project_id", "proj")
        monkeypatch.setattr(gcp_mod.settings, "gcp_posts_collection", "posts")
        monkeypatch.setattr(gcp_mod.settings, "gcp_profiles_collection", "profiles")
        monkeypatch.setattr(gcp_mod.settings, "gcp_storage_bucket", "bucket")

        backend = gcp_mod.GcpBackend()
        assert backend.posts_collection == "posts"
        assert backend.profiles_collection == "profiles"

    def test_init_credentials_prefetch_failure(self, monkeypatch):
        monkeypatch.setattr(gcp_mod, "_gcp_available", True)
        monkeypatch.setattr(
            gcp_mod,
            "firestore",
            SimpleNamespace(Client=lambda project: Mock()),
            raising=False,
        )
        monkeypatch.setattr(
            gcp_mod,
            "storage",
            SimpleNamespace(Client=lambda project: Mock()),
            raising=False,
        )
        fake_google = SimpleNamespace(
            auth=SimpleNamespace(
                default=lambda: (_ for _ in ()).throw(RuntimeError("no creds")),
                transport=SimpleNamespace(
                    requests=SimpleNamespace(Request=lambda: object())
                ),
            )
        )
        monkeypatch.setattr(gcp_mod, "google", fake_google, raising=False)
        monkeypatch.setattr(gcp_mod.settings, "gcp_project_id", "proj")
        monkeypatch.setattr(gcp_mod.settings, "gcp_posts_collection", "posts")
        monkeypatch.setattr(gcp_mod.settings, "gcp_profiles_collection", "profiles")
        monkeypatch.setattr(gcp_mod.settings, "gcp_storage_bucket", "bucket")

        backend = gcp_mod.GcpBackend()
        assert backend._gcs_credentials is None
        assert backend._gcs_auth_request is None

    def test_init_import_guard(self, monkeypatch):
        monkeypatch.setattr(gcp_mod, "_gcp_available", False)
        with pytest.raises(ImportError):
            gcp_mod.GcpBackend()

    def test_doc_to_post_timestamp_handling(self, gcp_backend):
        ts_obj = SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00")
        doc = SimpleNamespace(
            id="p1",
            to_dict=lambda: {
                "userId": "u1",
                "content": "c",
                "createdAt": ts_obj,
                "updatedAt": None,
                "imageUrls": [],
                "tags": [],
            },
        )
        post = gcp_backend._doc_to_post(doc)
        assert post.id == "p1"
        assert post.created_at == "2026-01-01T00:00:00"

    def test_doc_to_post_timestamp_numeric_branch(self, gcp_backend):
        ts_obj = SimpleNamespace(timestamp=lambda: 0)
        doc = SimpleNamespace(
            id="p1",
            to_dict=lambda: {
                "userId": "u1",
                "content": "c",
                "createdAt": ts_obj,
                "updatedAt": None,
                "imageUrls": [],
                "tags": [],
            },
        )
        post = gcp_backend._doc_to_post(doc)
        assert post.created_at.startswith("1970-01-01")

    def test_create_post_and_get_post(self, gcp_backend):
        user = UserInfo(user_id="u1", email=None, groups=None)
        body = CreatePostBody(content="hello", imageKeys=["img1.png"])

        profile_doc = SimpleNamespace(exists=True, to_dict=lambda: {"nickname": "neo"})
        posts_col = Mock()
        profiles_col = Mock()
        profiles_col.document.return_value.get.return_value = profile_doc
        posts_col.document.return_value = Mock()
        gcp_backend.db.collection.side_effect = lambda name: (
            profiles_col if name == "profiles" else posts_col
        )

        with patch("app.backends.gcp_backend.uuid.uuid4", return_value="id1"):
            result = gcp_backend.create_post(body, user)

        assert result["postId"] == "id1"
        assert result["nickname"] == "neo"

        post_doc = SimpleNamespace(
            exists=True,
            to_dict=lambda: {
                "userId": "u1",
                "content": "hello",
                "tags": [],
                "createdAt": "2026-01-01T00:00:00",
                "updatedAt": None,
                "imageUrls": [],
            },
        )
        posts_col.document.return_value.get.return_value = post_doc
        got = gcp_backend.get_post("id1")
        assert got.id == "id1"

    def test_generate_upload_urls(self, gcp_backend, monkeypatch):
        monkeypatch.setattr(gcp_mod.settings, "gcp_service_account", "svc@example.com")
        monkeypatch.setattr(gcp_mod.settings, "presigned_url_expiry", 300)

        blob = Mock()
        blob.generate_signed_url.return_value = "https://signed"
        bucket = Mock()
        bucket.blob.return_value = blob
        gcp_backend.storage_client.bucket.return_value = bucket

        user = UserInfo(user_id="u1", email=None, groups=None)
        with patch("app.backends.gcp_backend.uuid.uuid4", return_value="id1"):
            urls = gcp_backend.generate_upload_urls(1, user, ["image/heic"])

        assert urls[0]["key"].endswith("id1.heic")
        assert urls[0]["url"] == "https://signed"

    def test_update_profile_set_and_update_paths(self, gcp_backend):
        user = UserInfo(user_id="u1", email=None, groups=None)
        doc_ref = Mock()

        not_exists_doc = SimpleNamespace(exists=False)
        exists_doc = SimpleNamespace(exists=True)

        profiles_col = Mock()
        profiles_col.document.return_value = doc_ref
        gcp_backend.db.collection.side_effect = lambda name: profiles_col

        body = ProfileUpdateRequest(nickname="neo")

        doc_ref.get.return_value = not_exists_doc
        with patch.object(
            gcp_backend, "get_profile", return_value=SimpleNamespace(user_id="u1")
        ):
            gcp_backend.update_profile(user, body)
        doc_ref.set.assert_called_once()

        doc_ref.get.return_value = exists_doc
        with patch.object(
            gcp_backend, "get_profile", return_value=SimpleNamespace(user_id="u1")
        ):
            gcp_backend.update_profile(user, ProfileUpdateRequest(bio="bio"))
        doc_ref.update.assert_called_once()

    def test_list_posts_with_cursor_and_tag(self, gcp_backend, monkeypatch):
        fake_query = Mock()
        fake_query.limit.return_value = fake_query
        fake_query.start_after.return_value = fake_query
        fake_query.where.return_value = fake_query
        fake_query.stream.return_value = [
            SimpleNamespace(
                id="p1",
                to_dict=lambda: {
                    "postId": "p1",
                    "userId": "u",
                    "content": "c",
                    "createdAt": "2026-01-01T00:00:00",
                },
            ),
            SimpleNamespace(
                id="p2",
                to_dict=lambda: {
                    "postId": "p2",
                    "userId": "u",
                    "content": "c",
                    "createdAt": "2026-01-01T00:00:01",
                },
            ),
        ]

        fake_col = Mock()
        fake_col.order_by.return_value = fake_query
        fake_col.document.return_value.get.return_value = SimpleNamespace(exists=True)
        gcp_backend.db.collection.return_value = fake_col

        monkeypatch.setattr(
            gcp_mod,
            "firestore",
            SimpleNamespace(
                Query=SimpleNamespace(DESCENDING="DESC"),
                FieldFilter=lambda *a, **k: (a, k),
            ),
            raising=False,
        )

        posts, token = gcp_backend.list_posts(limit=1, next_token="cursor", tag="x")
        assert len(posts) == 1
        assert token == "p1"

    def test_get_post_none_and_delete_post_paths(self, gcp_backend):
        posts_col = Mock()
        gcp_backend.db.collection.return_value = posts_col

        posts_col.document.return_value.get.return_value = SimpleNamespace(exists=False)
        assert gcp_backend.get_post("missing") is None

        user = UserInfo(user_id="u1", email=None, groups=None)
        with pytest.raises(Exception) as exc:
            gcp_backend.delete_post("missing", user)
        assert exc.value.status_code == 404

        posts_col.document.return_value.get.return_value = SimpleNamespace(
            exists=True,
            to_dict=lambda: {"userId": "owner"},
        )
        with pytest.raises(Exception) as exc2:
            gcp_backend.delete_post("p1", user)
        assert exc2.value.status_code == 403

        posts_col.document.return_value.get.return_value = SimpleNamespace(
            exists=True,
            to_dict=lambda: {"userId": "u1"},
        )
        ok = gcp_backend.delete_post("p1", user)
        assert ok["postId"] == "p1"

    def test_get_profile_exists_with_timestamp(self, gcp_backend):
        ts_obj = SimpleNamespace(timestamp=lambda: 0)
        doc_ref = Mock()
        doc_ref.get.return_value = SimpleNamespace(
            exists=True,
            to_dict=lambda: {
                "nickname": "neo",
                "bio": "bio",
                "avatarUrl": "https://x",
                "createdAt": ts_obj,
                "updatedAt": ts_obj,
            },
        )
        col = Mock()
        col.document.return_value = doc_ref
        gcp_backend.db.collection.return_value = col

        p = gcp_backend.get_profile("u1")
        assert p.nickname == "neo"

    def test_generate_upload_urls_fallback_credentials_path(
        self, gcp_backend, monkeypatch
    ):
        gcp_backend._gcs_credentials = None
        gcp_backend._gcs_auth_request = None

        creds = SimpleNamespace(valid=True, token="tok")
        fake_google = SimpleNamespace(
            auth=SimpleNamespace(
                default=lambda: (creds, "proj"),
                transport=SimpleNamespace(
                    requests=SimpleNamespace(Request=lambda: object())
                ),
            )
        )
        monkeypatch.setattr(gcp_mod, "google", fake_google, raising=False)

        monkeypatch.setattr(gcp_mod.settings, "gcp_service_account", "svc@example.com")
        monkeypatch.setattr(gcp_mod.settings, "presigned_url_expiry", 300)

        blob = Mock()
        blob.generate_signed_url.return_value = "https://signed"
        bucket = Mock()
        bucket.blob.return_value = blob
        gcp_backend.storage_client.bucket.return_value = bucket

        user = UserInfo(user_id="u1", email=None, groups=None)
        with patch("app.backends.gcp_backend.uuid.uuid4", return_value="id2"):
            urls = gcp_backend.generate_upload_urls(1, user)
        assert urls[0]["key"].endswith("id2.jpg")

    def test_generate_upload_urls_refresh_and_missing_sa(
        self, gcp_backend, monkeypatch
    ):
        creds = SimpleNamespace(valid=False, token="tok", refresh=Mock())
        gcp_backend._gcs_credentials = creds
        gcp_backend._gcs_auth_request = object()

        monkeypatch.setattr(gcp_mod.settings, "gcp_service_account", None)
        with pytest.raises(RuntimeError):
            gcp_backend.generate_upload_urls(
                1, UserInfo(user_id="u", email=None, groups=None)
            )

        assert creds.refresh.called
