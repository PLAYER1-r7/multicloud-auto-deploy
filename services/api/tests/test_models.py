"""
Models Module Tests
Tests app/models.py functionality: data models, validation, serialization
"""

from app.models import (
    CloudProvider,
    CreatePostBody,
    HealthResponse,
    ListPostsResponse,
    Post,
    ProfileResponse,
    ProfileUpdateRequest,
    UpdatePostBody,
    UploadUrlsRequest,
    UploadUrlsResponse,
)


class TestCloudProviderEnum:
    """Test CloudProvider enum"""

    def test_cloud_provider_enum_values(self):
        """Test CloudProvider enum has all values"""
        assert CloudProvider.LOCAL.value == "local"
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.AZURE.value == "azure"
        assert CloudProvider.GCP.value == "gcp"

    def test_cloud_provider_enum_count(self):
        """Test CloudProvider enum has expected members"""
        assert len(CloudProvider) == 4


class TestPostModel:
    """Test Post data model"""

    def test_post_creation_with_snake_case(self):
        """Test Post creation with snake_case fields"""
        post = Post(
            postId="post-1",
            userId="user-1",
            content="Test content",
            createdAt="2026-03-03T00:00:00",
        )
        assert post.id == "post-1"
        assert post.user_id == "user-1"
        assert post.content == "Test content"

    def test_post_creation_with_camel_case_alias(self):
        """Test Post model alias handling"""
        post = Post(
            id="post-1",
            user_id="user-1",
            content="Test content",
            created_at="2026-03-03T00:00:00",
        )
        assert post.id == "post-1"
        assert post.user_id == "user-1"

    def test_post_with_all_fields(self):
        """Test Post with all optional fields"""
        post = Post(
            postId="post-1",
            userId="user-1",
            nickname="test_user",
            content="Test content",
            isMarkdown=True,
            imageUrls=["img1.jpg", "img2.jpg"],
            tags=["python", "testing"],
            createdAt="2026-03-03T00:00:00",
            updatedAt="2026-03-03T12:00:00",
        )
        assert post.id == "post-1"
        assert post.user_id == "user-1"
        assert post.nickname == "test_user"
        assert post.is_markdown is True
        assert post.image_urls == ["img1.jpg", "img2.jpg"]
        assert post.tags == ["python", "testing"]

    def test_post_with_none_optional_fields(self):
        """Test Post with None optional fields"""
        post = Post(
            postId="post-1",
            userId="user-1",
            content="Test content",
            createdAt="2026-03-03T00:00:00",
            nickname=None,
            imageUrls=None,
            tags=None,
            updatedAt=None,
        )
        assert post.nickname is None
        assert post.image_urls is None
        assert post.tags is None
        assert post.updated_at is None

    def test_post_serialize_model(self):
        """Test Post model serialization with camelCase and snake_case"""
        post = Post(
            postId="post-1",
            userId="user-1",
            nickname="author",
            content="Test content",
            isMarkdown=False,
            imageUrls=["image.jpg"],
            tags=["tag1"],
            createdAt="2026-03-03T00:00:00",
            updatedAt="2026-03-03T12:00:00",
        )
        serialized = post.model_dump()

        # Check camelCase fields
        assert serialized["postId"] == "post-1"
        assert serialized["userId"] == "user-1"
        assert serialized["isMarkdown"] is False
        assert serialized["imageUrls"] == ["image.jpg"]
        assert serialized["createdAt"] == "2026-03-03T00:00:00"
        assert serialized["updatedAt"] == "2026-03-03T12:00:00"

        # Check snake_case fields
        assert serialized["id"] == "post-1"
        assert serialized["author"] == "user-1"
        assert serialized["created_at"] == "2026-03-03T00:00:00"
        assert serialized["image_url"] == "image.jpg"

    def test_post_serialize_with_no_images(self):
        """Test Post serialization when imageUrls is None"""
        post = Post(
            postId="post-1",
            userId="user-1",
            content="No images",
            createdAt="2026-03-03T00:00:00",
            imageUrls=None,
        )
        serialized = post.model_dump()
        assert serialized["image_url"] is None


class TestCreatePostBody:
    """Test CreatePostBody validation"""

    def test_create_post_minimum_fields(self):
        """Test CreatePostBody with only required field"""
        body = CreatePostBody(content="Test post")
        assert body.content == "Test post"
        assert body.is_markdown is False
        assert body.image_keys is None
        assert body.tags is None

    def test_create_post_with_all_fields(self):
        """Test CreatePostBody with all fields"""
        body = CreatePostBody(
            content="Test post",
            isMarkdown=True,
            imageKeys=["img1.jpg", "img2.jpg"],
            tags=["python", "testing"],
        )
        assert body.content == "Test post"
        assert body.is_markdown is True
        assert body.image_keys == ["img1.jpg", "img2.jpg"]
        assert body.tags == ["python", "testing"]

    def test_create_post_content_min_length(self):
        """Test CreatePostBody content minimum length validation"""
        try:
            CreatePostBody(content="")
            assert False, "Should raise validation error for empty content"
        except ValueError:
            pass

    def test_create_post_content_max_length(self):
        """Test CreatePostBody content maximum length validation"""
        try:
            CreatePostBody(content="x" * 10001)
            assert False, "Should raise validation error for too long content"
        except ValueError:
            pass

    def test_create_post_tags_max_length(self):
        """Test CreatePostBody tags maximum count"""
        try:
            CreatePostBody(content="Test", tags=[f"tag{i}" for i in range(11)])
            assert False, "Should raise validation error for too many tags"
        except ValueError:
            pass


class TestUpdatePostBody:
    """Test UpdatePostBody with optional fields"""

    def test_update_post_empty_body(self):
        """Test UpdatePostBody with no fields provided"""
        body = UpdatePostBody()
        assert body.content is None
        assert body.is_markdown is None
        assert body.image_keys is None
        assert body.tags is None

    def test_update_post_content_only(self):
        """Test UpdatePostBody with content only"""
        body = UpdatePostBody(content="Updated content")
        assert body.content == "Updated content"
        assert body.is_markdown is None
        assert body.image_keys is None

    def test_update_post_all_fields(self):
        """Test UpdatePostBody with all fields"""
        body = UpdatePostBody(
            content="Updated content",
            isMarkdown=True,
            imageKeys=["new_image.jpg"],
            tags=["updated"],
        )
        assert body.content == "Updated content"
        assert body.is_markdown is True
        assert body.image_keys == ["new_image.jpg"]
        assert body.tags == ["updated"]

    def test_update_post_content_min_length(self):
        """Test UpdatePostBody content validation"""
        try:
            UpdatePostBody(content="")
            assert False, "Should raise validation error"
        except ValueError:
            pass


class TestListPostsResponse:
    """Test ListPostsResponse model"""

    def test_list_posts_response_creation(self):
        """Test ListPostsResponse with items"""
        posts = [
            Post(
                postId="post-1",
                userId="user-1",
                content="Post 1",
                createdAt="2026-03-03T00:00:00",
            ),
            Post(
                postId="post-2",
                userId="user-2",
                content="Post 2",
                createdAt="2026-03-03T01:00:00",
            ),
        ]
        response = ListPostsResponse(items=posts, limit=10)
        assert len(response.items) == 2
        assert response.limit == 10
        assert response.next_token is None

    def test_list_posts_response_with_next_token(self):
        """Test ListPostsResponse with pagination token"""
        response = ListPostsResponse(
            items=[],
            limit=10,
            nextToken="token-123",
        )
        assert response.next_token == "token-123"

    def test_list_posts_response_serialize(self):
        """Test ListPostsResponse serialization for compatibility"""
        posts = [
            Post(
                postId="post-1",
                userId="user-1",
                content="Post 1",
                createdAt="2026-03-03T00:00:00",
            )
        ]
        response = ListPostsResponse(items=posts, limit=10, nextToken="token-123")
        serialized = response.model_dump()

        # Check compatibility aliases
        assert serialized["items"] is not None
        assert serialized["results"] is not None  # ashnova.v1 compat
        assert serialized["messages"] is not None  # frontend_react compat
        assert serialized["limit"] == 10
        assert serialized["nextToken"] == "token-123"
        assert serialized["total"] == 1  # frontend_react compat
        assert serialized["page"] == 1  # frontend_react compat
        assert serialized["page_size"] == 10  # frontend_react compat


class TestProfileResponse:
    """Test ProfileResponse model"""

    def test_profile_response_creation(self):
        """Test ProfileResponse with basic fields"""
        profile = ProfileResponse(
            userId="user-1",
            nickname="testuser",
            bio="Test bio",
            avatarUrl="avatar.jpg",
            createdAt="2026-03-03T00:00:00",
        )
        assert profile.user_id == "user-1"
        assert profile.nickname == "testuser"
        assert profile.bio == "Test bio"
        assert profile.avatar_url == "avatar.jpg"

    def test_profile_response_with_none_fields(self):
        """Test ProfileResponse with None optional fields"""
        profile = ProfileResponse(
            userId="user-1",
            nickname=None,
            bio=None,
            avatarUrl=None,
            createdAt=None,
            updatedAt=None,
        )
        assert profile.nickname is None
        assert profile.bio is None
        assert profile.avatar_url is None


class TestProfileUpdateRequest:
    """Test ProfileUpdateRequest validation"""

    def test_profile_update_empty(self):
        """Test ProfileUpdateRequest with no fields"""
        request = ProfileUpdateRequest()
        assert request.nickname is None
        assert request.bio is None
        assert request.avatar_key is None

    def test_profile_update_nickname(self):
        """Test ProfileUpdateRequest with nickname"""
        request = ProfileUpdateRequest(nickname="newname")
        assert request.nickname == "newname"

    def test_profile_update_nickname_max_length(self):
        """Test ProfileUpdateRequest nickname validation"""
        try:
            ProfileUpdateRequest(nickname="x" * 101)
            assert False, "Should raise validation error"
        except ValueError:
            pass

    def test_profile_update_bio_max_length(self):
        """Test ProfileUpdateRequest bio validation"""
        try:
            ProfileUpdateRequest(bio="x" * 501)
            assert False, "Should raise validation error"
        except ValueError:
            pass

    def test_profile_update_all_fields(self):
        """Test ProfileUpdateRequest with all fields"""
        request = ProfileUpdateRequest(
            nickname="newname",
            bio="New bio",
            avatarKey="avatar.jpg",
        )
        assert request.nickname == "newname"
        assert request.bio == "New bio"
        assert request.avatar_key == "avatar.jpg"


class TestUploadUrlsRequest:
    """Test UploadUrlsRequest validation"""

    def test_upload_urls_request_count_validation(self):
        """Test UploadUrlsRequest count field"""
        request = UploadUrlsRequest(count=5)
        assert request.count == 5

    def test_upload_urls_request_count_minimum(self):
        """Test UploadUrlsRequest count minimum"""
        try:
            UploadUrlsRequest(count=0)
            assert False, "Should raise validation error"
        except ValueError:
            pass

    def test_upload_urls_request_count_maximum(self):
        """Test UploadUrlsRequest count maximum"""
        try:
            UploadUrlsRequest(count=101)
            assert False, "Should raise validation error"
        except ValueError:
            pass

    def test_upload_urls_request_with_content_types(self):
        """Test UploadUrlsRequest with content types"""
        request = UploadUrlsRequest(
            count=2,
            contentTypes=["image/jpeg", "image/png"],
        )
        assert request.count == 2
        assert request.content_types == ["image/jpeg", "image/png"]


class TestUploadUrlsResponse:
    """Test UploadUrlsResponse model"""

    def test_upload_urls_response_creation(self):
        """Test UploadUrlsResponse with URLs"""
        urls = [
            {"uploadUrl": "https://s3.amazonaws.com/bucket/key1", "key": "key1"},
            {"uploadUrl": "https://s3.amazonaws.com/bucket/key2", "key": "key2"},
        ]
        response = UploadUrlsResponse(urls=urls)
        assert len(response.urls) == 2
        assert response.urls[0]["key"] == "key1"


class TestHealthResponse:
    """Test HealthResponse model"""

    def test_health_response_creation(self):
        """Test HealthResponse with required fields"""
        response = HealthResponse(status="healthy", provider="aws")
        assert response.status == "healthy"
        assert response.provider == "aws"
        assert response.version == "3.0.0"

    def test_health_response_with_custom_version(self):
        """Test HealthResponse with custom version"""
        response = HealthResponse(
            status="degraded",
            provider="gcp",
            version="2.5.0",
        )
        assert response.version == "2.5.0"

    def test_health_response_default_version(self):
        """Test HealthResponse uses default version"""
        response = HealthResponse(status="ok", provider="local")
        assert response.version == "3.0.0"
