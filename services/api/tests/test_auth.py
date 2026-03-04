"""
Authentication Module Tests
Tests auth.py functionality: UserInfo, user permissions
"""

from app.auth import UserInfo


class TestUserInfo:
    """Test UserInfo model"""

    def test_user_info_creation(self):
        """Test creating a UserInfo instance"""
        user = UserInfo(
            user_id="test-user-1",
            email="test@example.com",
            groups=None,
        )
        assert user.user_id == "test-user-1"
        assert user.email == "test@example.com"
        assert user.groups is None

    def test_user_info_with_groups(self):
        """Test UserInfo with groups"""
        user = UserInfo(
            user_id="admin-user",
            email="admin@example.com",
            groups=["Admins", "Developers"],
        )
        assert user.user_id == "admin-user"
        assert user.groups == ["Admins", "Developers"]

    def test_user_info_empty_groups(self):
        """Test UserInfo with empty groups list"""
        user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=[],
        )
        assert user.groups == []

    def test_user_info_with_none_email(self):
        """Test UserInfo with None email"""
        user = UserInfo(
            user_id="user-1",
            email=None,
            groups=None,
        )
        assert user.email is None

    def test_user_info_string_representation(self):
        """Test UserInfo has expected attributes"""
        user = UserInfo(
            user_id="test-user",
            email="test@example.com",
            groups=["Users"],
        )
        assert hasattr(user, "user_id")
        assert hasattr(user, "email")
        assert hasattr(user, "groups")


class TestUserPermissions:
    """Test user permission checks"""

    def test_is_admin_with_admin_group(self):
        """Test admin user detection"""
        admin_user = UserInfo(
            user_id="admin-1",
            email="admin@example.com",
            groups=["Admins"],
        )
        assert admin_user.is_admin is True

    def test_is_admin_without_group(self):
        """Test regular user is not admin"""
        regular_user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=None,
        )
        assert regular_user.is_admin is False

    def test_is_admin_with_other_groups(self):
        """Test user with non-admin groups is not admin"""
        user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=["Users", "Developers"],
        )
        assert user.is_admin is False

    def test_is_admin_with_multiple_groups_including_admin(self):
        """Test user with multiple groups including Admins"""
        user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=["Users", "Developers", "Admins"],
        )
        assert user.is_admin is True

    def test_user_with_multiple_groups(self):
        """Test user with multiple group memberships"""
        user = UserInfo(
            user_id="user-1",
            email="user@example.com",
            groups=["Users", "Developers", "Testers"],
        )
        assert len(user.groups) == 3
        assert "Developers" in user.groups
        assert "Testers" in user.groups
        assert "Admins" not in user.groups
