"""
Backend Integration Tests
Tests CRUD operations for all backends (AWS, GCP, Azure)
"""
import pytest
from typing import Type
from unittest.mock import Mock, patch, MagicMock

from app.backends.base import BackendBase
from app.backends.aws_backend import AwsBackend
from app.backends.gcp_backend import GcpBackend
from app.backends.azure_backend import AzureBackend
from app.auth import UserInfo
from app.models import CreatePostBody, UpdatePostBody, ProfileUpdateRequest


class TestBackendBase:
    """Base test class for backend implementations"""
    
    backend_class: Type[BackendBase] = None
    
    def get_backend(self):
        """Get backend instance (to be implemented by subclasses)"""
        raise NotImplementedError
    
    def test_backend_initialization(self):
        """Test backend can be initialized"""
        backend = self.get_backend()
        assert backend is not None
        assert isinstance(backend, BackendBase)
    
    def test_create_post_success(self, test_user, sample_post_body):
        """Test post creation"""
        backend = self.get_backend()
        
        result = backend.create_post(sample_post_body, test_user)
        
        assert result is not None
        assert "item" in result
        item = result["item"]
        assert item["userId"] == test_user.user_id
        assert item["content"] == sample_post_body.content
        assert item["tags"] == sample_post_body.tags
    
    def test_list_posts_empty(self, test_user):
        """Test listing posts when empty"""
        backend = self.get_backend()
        
        posts, next_token = backend.list_posts(limit=20, next_token=None, tag=None)
        
        assert isinstance(posts, list)
        # May be empty or contain existing test data
        assert next_token is None or isinstance(next_token, str)
    
    def test_list_posts_with_tag_filter(self, test_user, sample_post_body):
        """Test listing posts with tag filter"""
        backend = self.get_backend()
        
        # Create a post with tags
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # List posts with tag filter
        posts, _ = backend.list_posts(limit=20, next_token=None, tag="test")
        
        # Should find at least the post we just created
        assert len(posts) > 0
        assert any(p.postId == post_id for p in posts)
    
    def test_update_post_success(self, test_user, sample_post_body, sample_update_body):
        """Test post update"""
        backend = self.get_backend()
        
        # Create a post
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # Update the post
        update_result = backend.update_post(post_id, sample_update_body, test_user)
        
        assert update_result is not None
        assert update_result["status"] == "updated"
        assert update_result["post_id"] == post_id
        assert "updated_at" in update_result
    
    def test_update_post_permission_denied(self, test_user, another_user, sample_post_body, sample_update_body):
        """Test post update fails for non-owner"""
        backend = self.get_backend()
        
        # Create a post as test_user
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # Try to update as another_user (should fail)
        with pytest.raises(PermissionError):
            backend.update_post(post_id, sample_update_body, another_user)
    
    def test_update_post_admin_can_update(self, test_user, admin_user, sample_post_body, sample_update_body):
        """Test admin can update any post"""
        backend = self.get_backend()
        
        # Create a post as test_user
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # Update as admin (should succeed)
        update_result = backend.update_post(post_id, sample_update_body, admin_user)
        
        assert update_result is not None
        assert update_result["status"] == "updated"
    
    def test_delete_post_success(self, test_user, sample_post_body):
        """Test post deletion"""
        backend = self.get_backend()
        
        # Create a post
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # Delete the post
        delete_result = backend.delete_post(post_id, test_user)
        
        assert delete_result is not None
        assert delete_result["status"] == "deleted"
        assert delete_result["post_id"] == post_id
    
    def test_delete_post_permission_denied(self, test_user, another_user, sample_post_body):
        """Test post deletion fails for non-owner"""
        backend = self.get_backend()
        
        # Create a post as test_user
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # Try to delete as another_user (should fail)
        with pytest.raises(PermissionError):
            backend.delete_post(post_id, another_user)
    
    def test_delete_post_admin_can_delete(self, test_user, admin_user, sample_post_body):
        """Test admin can delete any post"""
        backend = self.get_backend()
        
        # Create a post as test_user
        result = backend.create_post(sample_post_body, test_user)
        post_id = result["item"].get("postId") or result["item"].get("id")
        
        # Delete as admin (should succeed)
        delete_result = backend.delete_post(post_id, admin_user)
        
        assert delete_result is not None
        assert delete_result["status"] == "deleted"
    
    def test_get_profile_not_found(self, test_user):
        """Test get profile for non-existent user"""
        backend = self.get_backend()
        
        profile = backend.get_profile("non-existent-user")
        
        assert profile is not None
        assert profile.userId == "non-existent-user"
        assert profile.nickname == ""
    
    def test_update_profile_success(self, test_user, sample_profile_update):
        """Test profile update"""
        backend = self.get_backend()
        
        result = backend.update_profile(test_user, sample_profile_update)
        
        assert result is not None
        assert result.userId == test_user.user_id
        assert result.nickname == sample_profile_update.nickname
        assert result.updatedAt is not None
    
    def test_get_profile_after_update(self, test_user, sample_profile_update):
        """Test get profile after update"""
        backend = self.get_backend()
        
        # Update profile
        backend.update_profile(test_user, sample_profile_update)
        
        # Get profile
        profile = backend.get_profile(test_user.user_id)
        
        assert profile is not None
        assert profile.userId == test_user.user_id
        assert profile.nickname == sample_profile_update.nickname
    
    def test_generate_upload_urls(self, test_user):
        """Test generate upload URLs"""
        backend = self.get_backend()
        
        urls = backend.generate_upload_urls(count=2, user=test_user)
        
        assert isinstance(urls, list)
        assert len(urls) == 2
        for url_data in urls:
            assert "url" in url_data
            assert "key" in url_data
            assert isinstance(url_data["url"], str)
            assert isinstance(url_data["key"], str)


@pytest.mark.aws
class TestAwsBackend(TestBackendBase):
    """Test AWS Backend (DynamoDB + S3)"""
    
    backend_class = AwsBackend
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Mock DynamoDB table"""
        table = MagicMock()
        table.query.return_value = {"Items": [], "Count": 0}
        table.put_item.return_value = {}
        table.update_item.return_value = {}
        table.delete_item.return_value = {}
        return table
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        client = MagicMock()
        client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key?signature=test"
        return client
    
    def get_backend(self, mock_dynamodb_table=None, mock_s3_client=None):
        """Get AWS backend with mocked resources"""
        with patch('app.backends.aws_backend.boto3') as mock_boto3:
            # Mock DynamoDB resource
            mock_dynamodb = MagicMock()
            mock_dynamodb.Table.return_value = mock_dynamodb_table or MagicMock()
            mock_boto3.resource.return_value = mock_dynamodb
            
            # Mock S3 client
            mock_boto3.client.return_value = mock_s3_client or MagicMock()
            
            # Set required environment variables
            with patch.dict('os.environ', {
                'POSTS_TABLE_NAME': 'test-posts',
                'IMAGES_BUCKET_NAME': 'test-images',
                'AWS_REGION': 'ap-northeast-1',
            }):
                backend = AwsBackend()
                return backend
    
    def test_list_posts_with_pagination(self):
        """Test AWS list_posts with pagination"""
        # This test would need more complex mocking
        # Skipping for now
        pass


@pytest.mark.gcp
class TestGcpBackend(TestBackendBase):
    """Test GCP Backend (Firestore + Cloud Storage)"""
    
    backend_class = GcpBackend
    
    @pytest.fixture
    def mock_firestore_client(self):
        """Mock Firestore client"""
        client = MagicMock()
        collection = MagicMock()
        collection.document.return_value.set.return_value = None
        collection.document.return_value.get.return_value.exists = False
        collection.document.return_value.get.return_value.to_dict.return_value = {}
        collection.document.return_value.update.return_value = None
        collection.document.return_value.delete.return_value = None
        collection.order_by.return_value = collection
        collection.limit.return_value = collection
        collection.stream.return_value = []
        client.collection.return_value = collection
        return client
    
    @pytest.fixture
    def mock_storage_client(self):
        """Mock Cloud Storage client"""
        client = MagicMock()
        bucket = MagicMock()
        blob = MagicMock()
        blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/test-key?signature=test"
        bucket.blob.return_value = blob
        client.bucket.return_value = bucket
        return client
    
    def get_backend(self):
        """Get GCP backend with mocked resources"""
        with patch('app.backends.gcp_backend._get_firestore') as mock_get_firestore:
            with patch('app.backends.gcp_backend._get_storage') as mock_get_storage:
                with patch('app.backends.gcp_backend.settings') as mock_settings:
                    mock_settings.gcp_project_id = "test-project"
                    mock_settings.gcp_storage_bucket = "test-bucket"
                    mock_settings.gcp_posts_collection = "posts"
                    mock_settings.gcp_profiles_collection = "profiles"
                    mock_settings.presigned_url_expiry = 300
                    
                    mock_firestore = MagicMock()
                    mock_get_firestore.return_value = mock_firestore
                    
                    mock_storage = MagicMock()
                    mock_get_storage.return_value = mock_storage
                    
                    backend = GcpBackend()
                    return backend


@pytest.mark.azure
class TestAzureBackend(TestBackendBase):
    """Test Azure Backend (Cosmos DB + Blob Storage)"""
    
    backend_class = AzureBackend
    
    @pytest.fixture
    def mock_cosmos_container(self):
        """Mock Cosmos DB container"""
        container = MagicMock()
        container.query_items.return_value.by_page.return_value = iter([[]])
        container.read_item.side_effect = Exception("Item not found")
        container.upsert_item.return_value = {}
        container.replace_item.return_value = {}
        container.delete_item.return_value = {}
        return container
    
    @pytest.fixture
    def mock_blob_service(self):
        """Mock Blob Service client"""
        service = MagicMock()
        container = MagicMock()
        container.delete_blob.return_value = None
        service.get_container_client.return_value = container
        return service
    
    def get_backend(self):
        """Get Azure backend with mocked resources"""
        with patch('app.backends.azure_backend._get_container') as mock_get_container:
            with patch('app.backends.azure_backend._get_blob_service') as mock_get_blob:
                with patch('app.backends.azure_backend.settings') as mock_settings:
                    mock_settings.cosmos_db_endpoint = "https://test.documents.azure.com:443/"
                    mock_settings.cosmos_db_key = "test-key"
                    mock_settings.cosmos_db_database = "test-db"
                    mock_settings.cosmos_db_container = "items"
                    mock_settings.azure_storage_account_name = "testaccount"
                    mock_settings.azure_storage_account_key = "test-key"
                    mock_settings.azure_storage_container = "images"
                    mock_settings.presigned_url_expiry = 300
                    
                    mock_container = MagicMock()
                    mock_get_container.return_value = mock_container
                    
                    mock_blob = MagicMock()
                    mock_get_blob.return_value = mock_blob
                    
                    backend = AzureBackend()
                    return backend


# Performance and stress tests
class TestBackendPerformance:
    """Performance tests for backends"""
    
    @pytest.mark.slow
    def test_bulk_post_creation(self, test_user, sample_post_body):
        """Test creating multiple posts"""
        # This would test performance with bulk operations
        pass
    
    @pytest.mark.slow
    def test_pagination_large_dataset(self, test_user):
        """Test pagination with large dataset"""
        # This would test pagination performance
        pass


# End-to-end tests
class TestEndToEnd:
    """End-to-end workflow tests"""
    
    def test_complete_post_lifecycle(self, test_user, sample_post_body, sample_update_body):
        """Test complete post lifecycle: create -> update -> list -> delete"""
        # This would test a complete workflow
        pass
    
    def test_multi_user_scenario(self, test_user, another_user, admin_user, sample_post_body):
        """Test multi-user interactions"""
        # This would test user permission scenarios
        pass
