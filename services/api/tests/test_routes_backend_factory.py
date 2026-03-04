"""Unit tests for routes and backend factory selection."""

import sys
import types

import pytest
from fastapi import HTTPException

import app.backends as backends_module
from app.models import (
    CloudProvider,
    CreatePostBody,
    Post,
    ProfileResponse,
    ProfileUpdateRequest,
    UpdatePostBody,
    UploadUrlsRequest,
)
from app.routes import limits, posts, profile, uploads


class DummyBackend:
    def list_posts(self, limit, next_token, tag):
        return (
            [
                Post(
                    postId="p1",
                    userId="u1",
                    content="hello",
                    createdAt="2026-01-01T00:00:00",
                )
            ],
            "next-1",
        )

    def get_post(self, post_id):
        if post_id == "missing":
            return None
        return Post(
            postId=post_id,
            userId="u1",
            content="hello",
            createdAt="2026-01-01T00:00:00",
        )

    def create_post(self, body, user):
        return {"ok": True, "content": body.content, "user": user.user_id}

    def delete_post(self, post_id, user):
        return {"deleted": post_id, "user": user.user_id}

    def update_post(self, post_id, body, user):
        return {"updated": post_id, "content": body.content, "user": user.user_id}

    def get_profile(self, user_id):
        return ProfileResponse(userId=user_id, nickname="nick")

    def update_profile(self, user, body):
        return ProfileResponse(userId=user.user_id, nickname=body.nickname or "n")

    def generate_upload_urls(self, count, user, content_types=None):
        return [
            {"uploadUrl": f"https://example.com/{i}", "key": f"k{i}"}
            for i in range(count)
        ]


def test_limits_endpoint(monkeypatch):
    monkeypatch.setattr(limits.settings, "max_images_per_post", 4)
    assert limits.get_limits() == {"maxImagesPerPost": 4}


def test_posts_list_and_get(monkeypatch):
    monkeypatch.setattr(posts, "get_backend", lambda: DummyBackend())

    result = posts.list_posts(limit=5, nextToken=None, tag=None)
    assert result.limit == 5
    assert len(result.items) == 1

    single = posts.get_post("p1")
    assert single.id == "p1"


def test_posts_get_not_found(monkeypatch):
    monkeypatch.setattr(posts, "get_backend", lambda: DummyBackend())

    with pytest.raises(HTTPException) as exc:
        posts.get_post("missing")
    assert exc.value.status_code == 404


def test_posts_create_validation_and_success(monkeypatch, test_user):
    monkeypatch.setattr(posts, "get_backend", lambda: DummyBackend())
    monkeypatch.setattr(posts.settings, "max_images_per_post", 2)

    with pytest.raises(HTTPException) as exc:
        posts.create_post(
            CreatePostBody(content="x", imageKeys=["1", "2", "3"]),
            user=test_user,
        )
    assert exc.value.status_code == 400

    result = posts.create_post(
        CreatePostBody(content="ok", imageKeys=["1"]),
        user=test_user,
    )
    assert result["ok"] is True


def test_posts_delete_and_update(monkeypatch, test_user):
    monkeypatch.setattr(posts, "get_backend", lambda: DummyBackend())

    deleted = posts.delete_post("p1", user=test_user)
    assert deleted["deleted"] == "p1"

    updated = posts.update_post("p1", UpdatePostBody(content="new"), user=test_user)
    assert updated["updated"] == "p1"
    assert updated["content"] == "new"


def test_profile_routes(monkeypatch, test_user):
    monkeypatch.setattr(profile, "get_backend", lambda: DummyBackend())

    p1 = profile.get_profile("u999")
    assert p1.user_id == "u999"

    p2 = profile.get_my_profile(user=test_user)
    assert p2.user_id == test_user.user_id

    p3 = profile.update_profile(ProfileUpdateRequest(nickname="neo"), user=test_user)
    assert p3.nickname == "neo"


def test_uploads_route(monkeypatch, test_user):
    monkeypatch.setattr(uploads, "get_backend", lambda: DummyBackend())
    monkeypatch.setattr(uploads.settings, "max_images_per_post", 2)

    with pytest.raises(HTTPException) as exc:
        uploads.generate_upload_urls(UploadUrlsRequest(count=3), user=test_user)
    assert exc.value.status_code == 400

    ok = uploads.generate_upload_urls(
        UploadUrlsRequest(count=2, contentTypes=["image/png", "image/jpeg"]),
        user=test_user,
    )
    assert len(ok.urls) == 2


def _install_fake_backend_module(module_name: str, class_name: str):
    module = types.ModuleType(module_name)

    class BackendImpl:
        pass

    setattr(module, class_name, BackendImpl)
    sys.modules[module_name] = module
    return BackendImpl


def test_backend_factory_local(monkeypatch):
    backends_module.get_backend.cache_clear()
    module_name = "app.backends.local_backend"
    original_module = sys.modules.get(module_name)
    try:
        local_cls = _install_fake_backend_module(module_name, "LocalBackend")
        monkeypatch.setattr(
            backends_module.settings, "cloud_provider", CloudProvider.LOCAL
        )
        instance = backends_module.get_backend()
        assert isinstance(instance, local_cls)
    finally:
        backends_module.get_backend.cache_clear()
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


def test_backend_factory_aws(monkeypatch):
    backends_module.get_backend.cache_clear()
    module_name = "app.backends.aws_backend"
    original_module = sys.modules.get(module_name)
    try:
        aws_cls = _install_fake_backend_module(module_name, "AwsBackend")
        monkeypatch.setattr(
            backends_module.settings, "cloud_provider", CloudProvider.AWS
        )
        instance = backends_module.get_backend()
        assert isinstance(instance, aws_cls)
    finally:
        backends_module.get_backend.cache_clear()
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


def test_backend_factory_azure(monkeypatch):
    backends_module.get_backend.cache_clear()
    module_name = "app.backends.azure_backend"
    original_module = sys.modules.get(module_name)
    try:
        azure_cls = _install_fake_backend_module(module_name, "AzureBackend")
        monkeypatch.setattr(
            backends_module.settings, "cloud_provider", CloudProvider.AZURE
        )
        instance = backends_module.get_backend()
        assert isinstance(instance, azure_cls)
    finally:
        backends_module.get_backend.cache_clear()
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


def test_backend_factory_gcp(monkeypatch):
    backends_module.get_backend.cache_clear()
    module_name = "app.backends.gcp_backend"
    original_module = sys.modules.get(module_name)
    try:
        gcp_cls = _install_fake_backend_module(module_name, "GcpBackend")
        monkeypatch.setattr(
            backends_module.settings, "cloud_provider", CloudProvider.GCP
        )
        instance = backends_module.get_backend()
        assert isinstance(instance, gcp_cls)
    finally:
        backends_module.get_backend.cache_clear()
        if original_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original_module


def test_backend_factory_unsupported(monkeypatch):
    backends_module.get_backend.cache_clear()
    monkeypatch.setattr(backends_module.settings, "cloud_provider", "invalid-provider")

    with pytest.raises(ValueError):
        backends_module.get_backend()

    backends_module.get_backend.cache_clear()
