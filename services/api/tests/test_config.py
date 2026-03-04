"""
Configuration Module Tests
Tests config.py: Settings initialization, validation, environment variables
Tests the global settings singleton without instantiating new Settings objects
"""

from app.config import settings
from app.models import CloudProvider


class TestSettingsSingleton:
    """Test the global settings singleton"""

    def test_settings_exists(self):
        """Test that settings singleton is available"""
        assert settings is not None

    def test_settings_cloud_provider_is_enum(self):
        """Test that cloud_provider is a CloudProvider enum"""
        assert isinstance(settings.cloud_provider, CloudProvider)

    def test_settings_cloud_provider_valid_values(self):
        """Test that cloud_provider is one of valid enum values"""
        valid_providers = [
            CloudProvider.LOCAL,
            CloudProvider.AWS,
            CloudProvider.AZURE,
            CloudProvider.GCP,
        ]
        assert settings.cloud_provider in valid_providers

    def test_auth_disabled_is_boolean(self):
        """Test that auth_disabled setting is boolean"""
        assert isinstance(settings.auth_disabled, bool)

    def test_cors_origins_is_string(self):
        """Test that cors_origins setting is string"""
        assert isinstance(settings.cors_origins, str)

    def test_rate_limit_enabled_is_boolean(self):
        """Test that rate_limit_enabled setting is boolean"""
        assert isinstance(settings.rate_limit_enabled, bool)

    def test_rate_limit_requests_per_window_is_integer(self):
        """Test that rate_limit_requests_per_window setting is integer"""
        assert isinstance(settings.rate_limit_requests_per_window, int)
        assert settings.rate_limit_requests_per_window > 0

    def test_rate_limit_window_seconds_is_integer(self):
        """Test that rate_limit_window_seconds setting is integer"""
        assert isinstance(settings.rate_limit_window_seconds, int)
        assert settings.rate_limit_window_seconds > 0

    def test_max_images_per_post_is_integer(self):
        """Test that max_images_per_post setting is integer"""
        assert isinstance(settings.max_images_per_post, int)
        assert settings.max_images_per_post > 0


class TestCloudProviderConfiguration:
    """Test cloud provider specific configurations"""

    def test_aws_settings_attributes_exist(self):
        """Test that AWS settings attributes exist"""
        assert hasattr(settings, "aws_region")
        assert hasattr(settings, "cognito_user_pool_id")
        assert hasattr(settings, "cognito_client_id")
        assert hasattr(settings, "posts_table_name")
        assert hasattr(settings, "images_bucket_name")

    def test_azure_settings_attributes_exist(self):
        """Test that Azure settings attributes exist"""
        assert hasattr(settings, "azure_tenant_id")
        assert hasattr(settings, "azure_client_id")
        assert hasattr(settings, "azure_storage_account_name")
        assert hasattr(settings, "azure_storage_account_key")
        assert hasattr(settings, "cosmos_db_endpoint")
        assert hasattr(settings, "cosmos_db_key")
        assert hasattr(settings, "cosmos_db_database")
        assert hasattr(settings, "cosmos_db_container")

    def test_gcp_settings_attributes_exist(self):
        """Test that GCP settings attributes exist"""
        assert hasattr(settings, "gcp_project_id")
        assert hasattr(settings, "gcp_client_id")
        assert hasattr(settings, "gcp_service_account")
        assert hasattr(settings, "gcp_storage_bucket")
        assert hasattr(settings, "gcp_posts_collection")
        assert hasattr(settings, "gcp_profiles_collection")

    def test_local_settings_attributes_exist(self):
        """Test that LOCAL settings attributes exist"""
        assert hasattr(settings, "dynamodb_endpoint")
        assert hasattr(settings, "dynamodb_table_name")
        assert hasattr(settings, "minio_endpoint")
        assert hasattr(settings, "minio_bucket")


class TestAuthConfiguration:
    """Test authentication settings"""

    def test_auth_provider_types(self):
        """Test auth provider settings are strings or None"""
        if settings.auth_provider is not None:
            assert isinstance(settings.auth_provider, str)
        if settings.auth_issuer is not None:
            assert isinstance(settings.auth_issuer, str)
        if settings.auth_jwks_url is not None:
            assert isinstance(settings.auth_jwks_url, str)

    def test_cognito_settings_type(self):
        """Test Cognito settings are strings or None"""
        if settings.cognito_user_pool_id is not None:
            assert isinstance(settings.cognito_user_pool_id, str)
        if settings.cognito_client_id is not None:
            assert isinstance(settings.cognito_client_id, str)

    def test_azure_ad_settings_type(self):
        """Test Azure AD settings are strings or None"""
        if settings.azure_tenant_id is not None:
            assert isinstance(settings.azure_tenant_id, str)
        if settings.azure_client_id is not None:
            assert isinstance(settings.azure_client_id, str)

    def test_gcp_credentials_type(self):
        """Test GCP credentials are strings or None"""
        if settings.gcp_project_id is not None:
            assert isinstance(settings.gcp_project_id, str)
        if settings.gcp_client_id is not None:
            assert isinstance(settings.gcp_client_id, str)


class TestCloudStorageConfiguration:
    """Test cloud storage settings"""

    def test_aws_storage_settings_type(self):
        """Test AWS storage settings are strings or None"""
        if settings.images_bucket_name is not None:
            assert isinstance(settings.images_bucket_name, str)
        if settings.images_cdn_url is not None:
            assert isinstance(settings.images_cdn_url, str)

    def test_azure_storage_settings_type(self):
        """Test Azure storage settings are strings or None"""
        if settings.azure_storage_account_name is not None:
            assert isinstance(settings.azure_storage_account_name, str)
        if settings.azure_storage_account_key is not None:
            assert isinstance(settings.azure_storage_account_key, str)

    def test_gcp_storage_settings_type(self):
        """Test GCP storage settings are strings or None"""
        if settings.gcp_storage_bucket is not None:
            assert isinstance(settings.gcp_storage_bucket, str)

    def test_minio_storage_settings_type(self):
        """Test MinIO storage settings are strings or None"""
        if settings.minio_endpoint is not None:
            assert isinstance(settings.minio_endpoint, str)
        if settings.minio_access_key is not None:
            assert isinstance(settings.minio_access_key, str)
        if settings.minio_secret_key is not None:
            assert isinstance(settings.minio_secret_key, str)
        assert isinstance(settings.minio_bucket, str)


class TestDatabaseConfiguration:
    """Test database settings"""

    def test_dynamodb_settings_type(self):
        """Test DynamoDB settings are strings or None"""
        assert isinstance(settings.dynamodb_table_name, str)
        if settings.dynamodb_endpoint is not None:
            assert isinstance(settings.dynamodb_endpoint, str)

    def test_cosmos_settings_type(self):
        """Test Cosmos DB settings are strings or None"""
        if settings.cosmos_db_endpoint is not None:
            assert isinstance(settings.cosmos_db_endpoint, str)
        if settings.cosmos_db_key is not None:
            assert isinstance(settings.cosmos_db_key, str)
        assert isinstance(settings.cosmos_db_database, str)
        assert isinstance(settings.cosmos_db_container, str)

    def test_firestore_collections_type(self):
        """Test Firestore collections are strings"""
        assert isinstance(settings.gcp_posts_collection, str)
        assert isinstance(settings.gcp_profiles_collection, str)


class TestApplicationSettings:
    """Test general application settings"""

    def test_log_level_is_string(self):
        """Test that log_level is a string"""
        assert isinstance(settings.log_level, str)

    def test_presigned_url_expiry_is_integer(self):
        """Test that presigned_url_expiry is integer"""
        assert isinstance(settings.presigned_url_expiry, int)
        assert settings.presigned_url_expiry > 0

    def test_admin_group_is_string(self):
        """Test that admin_group is string"""
        assert isinstance(settings.admin_group, str)

    def test_minio_bucket_is_string(self):
        """Test that minio_bucket is string"""
        assert isinstance(settings.minio_bucket, str)

    def test_azure_storage_container_is_string(self):
        """Test that azure_storage_container is string"""
        assert isinstance(settings.azure_storage_container, str)


class TestEnvironmentVariableHandling:
    """Test environment variable handling in settings"""

    def test_settings_reads_from_env(self):
        """Test that settings reads from environment variables"""
        # The settings singleton should have loaded from .env or environment
        assert settings is not None
        # Verify at least one setting is set (cloud_provider should always be set)
        assert settings.cloud_provider is not None

    def test_settings_has_default_cloud_provider(self):
        """Test that settings defaults to a valid cloud provider"""
        assert settings.cloud_provider in [
            CloudProvider.LOCAL,
            CloudProvider.AWS,
            CloudProvider.AZURE,
            CloudProvider.GCP,
        ]

    def test_aws_region_has_value(self):
        """Test that aws_region has a default value"""
        assert settings.aws_region is not None
        assert isinstance(settings.aws_region, str)


class TestSettingsValidation:
    """Test settings validation and type safety"""

    def test_rate_limit_settings_consistency(self):
        """Test that rate limit settings are consistent"""
        # If rate limiting is enabled, values should be positive
        if settings.rate_limit_enabled:
            assert settings.rate_limit_requests_per_window > 0
            assert settings.rate_limit_window_seconds > 0

    def test_cloud_provider_string_representation(self):
        """Test cloud provider can be represented as string"""
        provider_str = str(settings.cloud_provider)
        assert len(provider_str) > 0

    def test_settings_immutable_attributes(self):
        """Test that critical settings are read"""
        # Accessing settings multiple times should return same values
        provider1 = settings.cloud_provider
        provider2 = settings.cloud_provider
        assert provider1 == provider2

    def test_settings_always_has_required_fields(self):
        """Test that required fields are always set"""
        assert settings.cloud_provider is not None
        assert settings.auth_disabled is not None
        assert settings.rate_limit_enabled is not None
        assert settings.max_images_per_post is not None

    def test_cloud_provider_based_config(self):
        """Test cloud provider specific config is available"""
        if settings.cloud_provider == CloudProvider.AWS:
            assert settings.aws_region is not None
            assert (
                settings.dynamodb_table_name is not None
                or settings.posts_table_name is not None
            )
        elif settings.cloud_provider == CloudProvider.AZURE:
            assert settings.azure_tenant_id is not None
            assert settings.cosmos_db_database is not None
        elif settings.cloud_provider == CloudProvider.GCP:
            assert settings.gcp_project_id is not None
            assert settings.gcp_posts_collection is not None
