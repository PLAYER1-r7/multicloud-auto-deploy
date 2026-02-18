"""
Pytest Configuration for Multi-Cloud Backend Tests
"""
import os
import uuid
import pytest
from datetime import datetime, timezone
from typing import Generator

# Set test environment variables
os.environ["CLOUD_PROVIDER"] = "local"
os.environ["AUTH_DISABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STORAGE_PATH"] = "/tmp/test-storage"

from app.auth import UserInfo
from app.models import CreatePostBody, UpdatePostBody, ProfileUpdateRequest


@pytest.fixture
def test_user() -> UserInfo:
    """Create a test user"""
    return UserInfo(
        user_id="test-user-1",
        nickname="Test User",
        email="test@example.com",
        is_admin=False,
    )


@pytest.fixture
def admin_user() -> UserInfo:
    """Create an admin user"""
    return UserInfo(
        user_id="admin-user-1",
        nickname="Admin User",
        email="admin@example.com",
        is_admin=True,
    )


@pytest.fixture
def another_user() -> UserInfo:
    """Create another test user"""
    return UserInfo(
        user_id="test-user-2",
        nickname="Another User",
        email="another@example.com",
        is_admin=False,
    )


@pytest.fixture
def sample_post_body() -> CreatePostBody:
    """Create sample post data"""
    return CreatePostBody(
        content="Test post content",
        tags=["test", "integration"],
        image_keys=["test-image-1.jpg"],
        is_markdown=False,
    )


@pytest.fixture
def sample_update_body() -> UpdatePostBody:
    """Create sample update data"""
    return UpdatePostBody(
        content="Updated post content",
        tags=["updated", "test"],
        image_keys=["updated-image-1.jpg"],
    )


@pytest.fixture
def sample_profile_update() -> ProfileUpdateRequest:
    """Create sample profile update data"""
    return ProfileUpdateRequest(
        nickname="Updated Nickname",
    )


@pytest.fixture
def unique_post_id() -> str:
    """Generate a unique post ID"""
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data after each test"""
    yield
    # Cleanup logic can be added here if needed
    # For now, backends handle their own cleanup


# Mock environment configurations for each backend
@pytest.fixture
def aws_config():
    """AWS backend configuration"""
    return {
        "CLOUD_PROVIDER": "aws",
        "AWS_REGION": "ap-northeast-1",
        "POSTS_TABLE_NAME": "test-posts",
        "IMAGES_BUCKET_NAME": "test-images",
    }


@pytest.fixture
def gcp_config():
    """GCP backend configuration"""
    return {
        "CLOUD_PROVIDER": "gcp",
        "GCP_PROJECT_ID": "test-project",
        "GCP_STORAGE_BUCKET": "test-bucket",
        "GCP_POSTS_COLLECTION": "posts",
        "GCP_PROFILES_COLLECTION": "profiles",
    }


@pytest.fixture
def azure_config():
    """Azure backend configuration"""
    return {
        "CLOUD_PROVIDER": "azure",
        "COSMOS_DB_ENDPOINT": "https://test.documents.azure.com:443/",
        "COSMOS_DB_KEY": "test-key",
        "COSMOS_DB_DATABASE": "test-db",
        "COSMOS_DB_CONTAINER": "items",
        "AZURE_STORAGE_ACCOUNT_NAME": "testaccount",
        "AZURE_STORAGE_ACCOUNT_KEY": "test-key",
        "AZURE_STORAGE_CONTAINER": "images",
    }
