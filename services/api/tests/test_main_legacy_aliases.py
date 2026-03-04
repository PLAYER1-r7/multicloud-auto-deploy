"""Unit tests for legacy aliases and validation handler in app.main."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.exceptions import RequestValidationError

import app.main as main_module
from app.models import CreatePostBody, UpdatePostBody


class _Backend:
    def list_posts(self, limit, next_token, tag):
        return [], "next-token"

    def create_post(self, body, user):
        return {"content": body.content, "user": user.user_id}

    def delete_post(self, post_id, user):
        if post_id == "missing":
            raise ValueError("not found")
        if post_id == "denied":
            raise PermissionError("forbidden")
        return {"deleted": post_id}

    def get_post(self, post_id):
        if post_id == "missing":
            raise ValueError("not found")
        return {"postId": post_id}

    def update_post(self, post_id, body, user):
        if post_id == "missing":
            raise ValueError("not found")
        if post_id == "denied":
            raise PermissionError("forbidden")
        return {"updated": post_id, "content": body.content}


@pytest.fixture
def backend():
    return _Backend()


def test_legacy_list_messages(backend, monkeypatch):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    result = main_module.legacy_list_messages(limit=10, nextToken=None, tag=None)
    assert result.limit == 10
    assert result.next_token == "next-token"


def test_legacy_create_message_with_anonymous_user(backend, monkeypatch):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    body = CreatePostBody(content="hello")
    result = main_module.legacy_create_message(body, user=None)
    assert result["user"] == "anonymous"


def test_legacy_delete_message_success(backend, monkeypatch, test_user):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    result = main_module.legacy_delete_message("p1", user=test_user)
    assert result["deleted"] == "p1"


def test_legacy_delete_message_maps_value_error(backend, monkeypatch, test_user):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    with pytest.raises(Exception) as exc:
        main_module.legacy_delete_message("missing", user=test_user)
    assert exc.value.status_code == 404


def test_legacy_delete_message_maps_permission_error(backend, monkeypatch, test_user):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    with pytest.raises(Exception) as exc:
        main_module.legacy_delete_message("denied", user=test_user)
    assert exc.value.status_code == 403


def test_legacy_get_message_success(backend, monkeypatch):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    result = main_module.legacy_get_message("p1", user=None)
    assert result["postId"] == "p1"


def test_legacy_get_message_maps_value_error(backend, monkeypatch):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    with pytest.raises(Exception) as exc:
        main_module.legacy_get_message("missing", user=None)
    assert exc.value.status_code == 404


def test_legacy_update_message_success(backend, monkeypatch, test_user):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    body = UpdatePostBody(content="new")
    result = main_module.legacy_update_message("p1", body, user=test_user)
    assert result["updated"] == "p1"


def test_legacy_update_message_maps_value_error(backend, monkeypatch, test_user):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    body = UpdatePostBody(content="new")
    with pytest.raises(Exception) as exc:
        main_module.legacy_update_message("missing", body, user=test_user)
    assert exc.value.status_code == 404


def test_legacy_update_message_maps_permission_error(backend, monkeypatch, test_user):
    monkeypatch.setattr(main_module, "get_backend", lambda: backend)
    body = UpdatePostBody(content="new")
    with pytest.raises(Exception) as exc:
        main_module.legacy_update_message("denied", body, user=test_user)
    assert exc.value.status_code == 403


class _URL:
    path = "/api/messages"


class _DummyRequest:
    method = "POST"
    url = _URL()

    def __init__(self, body_bytes=b"{}"):
        self._body_bytes = body_bytes

    async def body(self):
        return self._body_bytes


class _BrokenBodyRequest(_DummyRequest):
    async def body(self):
        raise RuntimeError("cannot read")


@pytest.mark.asyncio
async def test_validation_exception_handler_success_body_read():
    exc = RequestValidationError(
        [{"loc": ["body", "content"], "msg": "bad", "type": "value_error"}]
    )
    res = await main_module.validation_exception_handler(_DummyRequest(b'{"x":1}'), exc)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_validation_exception_handler_body_read_error():
    exc = RequestValidationError(
        [{"loc": ["body", "content"], "msg": "bad", "type": "value_error"}]
    )
    res = await main_module.validation_exception_handler(_BrokenBodyRequest(), exc)
    assert res.status_code == 422


def test_root_and_health_powertools_branch(monkeypatch):
    metric_mock = Mock()
    monkeypatch.setattr(main_module, "powertools_available", True)
    monkeypatch.setattr(main_module, "metrics", metric_mock, raising=False)
    monkeypatch.setattr(
        main_module, "MetricUnit", SimpleNamespace(Count="Count"), raising=False
    )

    root_res = main_module.root()
    health_res = main_module.health()

    assert root_res.status == "ok"
    assert health_res.status == "ok"
    assert metric_mock.add_metric.call_count == 2
