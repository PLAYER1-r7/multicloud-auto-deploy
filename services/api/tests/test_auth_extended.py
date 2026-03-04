"""
Authentication Extended Module Tests
Tests auth.py dependency functions: authorization checks
"""

import pytest
from fastapi import HTTPException

from app.auth import UserInfo, require_admin, require_user


class TestRequireUser:
    """Test require_user dependency"""

    @pytest.mark.asyncio
    async def test_require_user_with_user(self):
        """Test require_user with authenticated user"""
        user = UserInfo(user_id="user-1", email="user@example.com")

        result = await require_user(user=user)

        assert result == user
        assert result.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_require_user_without_user(self):
        """Test require_user without user raises 401"""
        with pytest.raises(HTTPException) as exc_info:
            await require_user(user=None)

        assert exc_info.value.status_code == 401
        assert "認証が必要です" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_user_sets_www_authenticate_header(self):
        """Test require_user includes WWW-Authenticate header"""
        with pytest.raises(HTTPException) as exc_info:
            await require_user(user=None)

        assert "WWW-Authenticate" in exc_info.value.headers
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_require_user_with_admin_user(self):
        """Test require_user accepts admin users"""
        admin_user = UserInfo(
            user_id="admin-1",
            email="admin@example.com",
            groups=["Admins"],
        )

        result = await require_user(user=admin_user)

        assert result == admin_user
        assert result.is_admin is True


class TestRequireAdmin:
    """Test require_admin dependency"""

    @pytest.mark.asyncio
    async def test_require_admin_with_admin_user(self):
        """Test require_admin with admin user"""
        admin_user = UserInfo(
            user_id="admin-1",
            email="admin@example.com",
            groups=["Admins"],
        )

        result = await require_admin(user=admin_user)

        assert result == admin_user
        assert result.is_admin is True

    @pytest.mark.asyncio
    async def test_require_admin_without_admin_group(self):
        """Test require_admin without admin group raises 403"""
        regular_user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=["Users"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=regular_user)

        assert exc_info.value.status_code == 403
        assert "管理者権限が必要です" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_admin_with_no_groups(self):
        """Test require_admin without groups raises 403"""
        user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_with_multiple_groups_including_admin(self):
        """Test require_admin allows user with admin in multiple groups"""
        admin_user = UserInfo(
            user_id="admin-1",
            email="admin@example.com",
            groups=["Users", "Developers", "Admins"],
        )

        result = await require_admin(user=admin_user)

        assert result == admin_user
        assert result.is_admin is True

    @pytest.mark.asyncio
    async def test_require_admin_regular_user_raises_403(self):
        """Test require_admin rejects regular users"""
        user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=["Testers"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=user)

        assert exc_info.value.status_code == 403
