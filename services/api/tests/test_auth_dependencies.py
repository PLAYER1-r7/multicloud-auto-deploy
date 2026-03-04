"""Unit tests for auth dependency helper functions."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

import app.config as config_module
from app.auth import UserInfo, get_current_user, get_jwt_verifier


class TestGetJwtVerifier:
    def test_returns_none_when_provider_missing(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_provider=None)
        )
        assert get_jwt_verifier() is None

    @patch("app.jwt_verifier.JWTVerifier")
    def test_builds_cognito_config(self, mock_cls, monkeypatch):
        monkeypatch.setattr(
            config_module,
            "settings",
            SimpleNamespace(
                auth_provider="cognito",
                aws_region="ap-northeast-1",
                cognito_user_pool_id="pool",
                cognito_client_id="client",
            ),
        )
        get_jwt_verifier()
        mock_cls.assert_called_once_with(
            "cognito",
            {"region": "ap-northeast-1", "user_pool_id": "pool", "client_id": "client"},
        )

    @patch("app.jwt_verifier.JWTVerifier")
    def test_builds_firebase_config(self, mock_cls, monkeypatch):
        monkeypatch.setattr(
            config_module,
            "settings",
            SimpleNamespace(auth_provider="firebase", gcp_project_id="proj-1"),
        )
        get_jwt_verifier()
        mock_cls.assert_called_once_with("firebase", {"project_id": "proj-1"})

    @patch("app.jwt_verifier.JWTVerifier")
    def test_builds_azure_config(self, mock_cls, monkeypatch):
        monkeypatch.setattr(
            config_module,
            "settings",
            SimpleNamespace(
                auth_provider="azure",
                azure_tenant_id="tenant-name.onmicrosoft.com",
                azure_client_id="client",
            ),
        )
        get_jwt_verifier()
        provider, conf = mock_cls.call_args[0]
        assert provider == "azure"
        assert conf["tenant_name"] == "tenant-name"
        assert conf["is_b2c"] is False

    def test_unknown_provider_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            config_module,
            "settings",
            SimpleNamespace(auth_provider="unknown"),
        )
        assert get_jwt_verifier() is None


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_auth_disabled_returns_test_user(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=True)
        )
        result = await get_current_user()
        assert isinstance(result, UserInfo)
        assert result.user_id == "test-user-1"

    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=False)
        )
        result = await get_current_user(credentials=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_verifier_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=False)
        )
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch("app.auth.get_jwt_verifier", return_value=None):
            result = await get_current_user(credentials=cred)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_failure_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=False)
        )
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")
        verifier = Mock()
        verifier.verify_token.return_value = None
        with patch("app.auth.get_jwt_verifier", return_value=verifier):
            result = await get_current_user(credentials=cred)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_success_returns_userinfo(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=False)
        )
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good")
        verifier = Mock()
        verifier.verify_token.return_value = {"sub": "u1"}
        verifier.extract_user_info.return_value = {
            "user_id": "u1",
            "email": "u1@example.com",
            "groups": ["Users"],
        }
        with patch("app.auth.get_jwt_verifier", return_value=verifier):
            result = await get_current_user(credentials=cred)
        assert result.user_id == "u1"
        assert result.email == "u1@example.com"
        assert result.groups == ["Users"]

    @pytest.mark.asyncio
    async def test_extract_user_info_missing_groups_defaults_empty_list(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=False)
        )
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good")
        verifier = Mock()
        verifier.verify_token.return_value = {"sub": "u1"}
        verifier.extract_user_info.return_value = {"user_id": "u1", "email": None}
        with patch("app.auth.get_jwt_verifier", return_value=verifier):
            result = await get_current_user(credentials=cred)
        assert result.groups == []

    @pytest.mark.asyncio
    async def test_verifier_exception_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            config_module, "settings", SimpleNamespace(auth_disabled=False)
        )
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x")
        verifier = Mock()
        verifier.verify_token.side_effect = RuntimeError("boom")
        with patch("app.auth.get_jwt_verifier", return_value=verifier):
            result = await get_current_user(credentials=cred)
        assert result is None
