"""
API Endpoint Integration Tests
Tests actual HTTP endpoints for all cloud providers
Reference: scripts/test-api.sh, scripts/test-e2e.sh
"""
import os
import time

import pytest
import requests

# API Endpoints (can be overridden by environment variables)
ENDPOINTS = {
    "aws": os.getenv("AWS_API_ENDPOINT", "https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com"),
    "gcp": os.getenv("GCP_API_ENDPOINT", "https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app"),
    "azure": os.getenv("AZURE_API_ENDPOINT", "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api"),
}


class TestAPIEndpoints:
    """Test actual deployed API endpoints"""

    @pytest.fixture(params=["aws", "gcp", "azure"])
    def api_endpoint(self, request):
        """Parametrized fixture for all cloud endpoints"""
        provider = request.param
        endpoint = ENDPOINTS[provider]

        # Check if endpoint is accessible
        if not endpoint or endpoint == "":
            pytest.skip(f"{provider.upper()} endpoint not configured")

        return {
            "provider": provider,
            "url": endpoint,
            "timeout": 30,
        }

    @pytest.mark.requires_network
    def test_health_check(self, api_endpoint):
        """Test health check endpoint"""
        url = f"{api_endpoint['url']}/"

        response = requests.get(url, timeout=api_endpoint['timeout'])

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert data.get("provider") == api_endpoint['provider']
        assert "version" in data

    @pytest.mark.requires_network
    def test_list_messages_initial(self, api_endpoint):
        """Test listing messages (initial state)"""
        url = f"{api_endpoint['url']}/api/messages/"

        response = requests.get(url, timeout=api_endpoint['timeout'])

        assert response.status_code == 200
        data = response.json()

        # Should have messages or items array
        assert "messages" in data or "items" in data or "results" in data

        # Should have pagination info
        if "messages" in data:
            assert isinstance(data["messages"], list)
        elif "items" in data:
            assert isinstance(data["items"], list)
        elif "results" in data:
            assert isinstance(data["results"], list)

    @pytest.mark.requires_network
    @pytest.mark.slow
    def test_crud_operations_flow(self, api_endpoint):
        """
        Test complete CRUD flow: Create -> Read -> Update -> Delete
        Reference: scripts/test-api.sh test cases 3-9
        """
        base_url = f"{api_endpoint['url']}/api/messages/"
        timeout = api_endpoint['timeout']
        provider = api_endpoint['provider']

        # 1. CREATE - Create a test message
        create_data = {
            "content": f"Integration Test Message from {provider.upper()}",
            "author": "pytest",
            "tags": ["test", "integration", provider],
        }

        response = requests.post(base_url, json=create_data, timeout=timeout)
        assert response.status_code in [200, 201], f"Create failed: {response.text}"

        created = response.json()
        message_id = created.get("id") or created.get("postId") or created.get("post_id")
        assert message_id is not None, f"No message ID returned. Response: {created}"

        # Small delay for eventual consistency
        time.sleep(1)

        # 2. READ (List) - Verify message appears in list
        response = requests.get(base_url, timeout=timeout)
        assert response.status_code == 200

        data = response.json()
        messages = data.get("messages") or data.get("items") or data.get("results") or []
        message_ids = [m.get("id") or m.get("postId") for m in messages]
        assert message_id in message_ids, "Created message not found in list"

        # 3. READ (Get by ID) - Fetch specific message
        response = requests.get(f"{base_url}{message_id}", timeout=timeout)
        assert response.status_code == 200

        message = response.json()
        assert message.get("content") == create_data["content"]

        # 4. UPDATE - Update the message
        update_data = {
            "content": f"UPDATED Integration Test Message from {provider.upper()} ✅",
        }

        response = requests.put(f"{base_url}{message_id}", json=update_data, timeout=timeout)
        assert response.status_code == 200, f"Update failed: {response.text}"

        # Small delay
        time.sleep(1)

        # 5. VERIFY UPDATE - Fetch and verify updated content
        response = requests.get(f"{base_url}{message_id}", timeout=timeout)
        assert response.status_code == 200

        updated_message = response.json()
        assert "UPDATED" in updated_message.get("content", "")
        assert "✅" in updated_message.get("content", "")

        # 6. DELETE - Delete the message
        response = requests.delete(f"{base_url}{message_id}", timeout=timeout)
        assert response.status_code in [200, 204], f"Delete failed: {response.text}"

        # Small delay
        time.sleep(1)

        # 7. VERIFY DELETION - Should return 404
        response = requests.get(f"{base_url}{message_id}", timeout=timeout)
        assert response.status_code == 404, "Message still exists after deletion"

    @pytest.mark.requires_network
    def test_pagination(self, api_endpoint):
        """
        Test pagination functionality
        Reference: scripts/test-api.sh test case 10
        """
        url = f"{api_endpoint['url']}/api/messages/"

        # Test with page size limit
        response = requests.get(
            url,
            params={"page": 1, "page_size": 5},
            timeout=api_endpoint['timeout']
        )

        assert response.status_code == 200
        data = response.json()

        # Should respect page size (or be smaller if less data exists)
        messages = data.get("messages") or data.get("items") or data.get("results") or []
        assert len(messages) <= 5

        # Should have pagination metadata
        assert "page" in data or "limit" in data or "page_size" in data

    @pytest.mark.requires_network
    def test_invalid_message_id(self, api_endpoint):
        """
        Test error handling for invalid message ID
        Reference: scripts/test-api.sh test case 11
        """
        url = f"{api_endpoint['url']}/api/messages/invalid-id-12345-nonexistent"

        response = requests.get(url, timeout=api_endpoint['timeout'])

        # Accept 404 or 405 (API may not support GET on specific paths)
        assert response.status_code in [404, 405], f"Expected 404 or 405, got {response.status_code}"

    @pytest.mark.requires_network
    def test_empty_content_validation(self, api_endpoint):
        """
        Test validation error for empty content
        Reference: scripts/test-api.sh test case 12
        """
        url = f"{api_endpoint['url']}/api/messages/"

        invalid_data = {
            "content": "",
            "author": "Test",
        }

        response = requests.post(url, json=invalid_data, timeout=api_endpoint['timeout'])

        # Should return validation error (422 or 400)
        assert response.status_code in [400, 422]


@pytest.mark.requires_network
class TestMultiCloudEndpoints:
    """
    Multi-cloud endpoint tests
    Reference: scripts/test-endpoints.sh
    """

    def test_all_cloud_health_checks(self):
        """Test health checks for all cloud providers"""
        results = {}

        for provider, endpoint in ENDPOINTS.items():
            if not endpoint:
                continue

            try:
                response = requests.get(f"{endpoint}/", timeout=10)
                results[provider] = {
                    "status_code": response.status_code,
                    "accessible": response.status_code == 200,
                    "response": response.json() if response.status_code == 200 else None,
                }
            except Exception as e:
                results[provider] = {
                    "status_code": None,
                    "accessible": False,
                    "error": str(e),
                }

        # At least one cloud should be accessible
        accessible_count = sum(1 for r in results.values() if r.get("accessible"))
        assert accessible_count > 0, f"No clouds accessible: {results}"

        # Print results for debugging
        print("\n=== Multi-Cloud Health Check Results ===")
        for provider, result in results.items():
            status = "✅" if result.get("accessible") else "❌"
            print(f"{status} {provider.upper()}: {result}")


@pytest.mark.requires_network
@pytest.mark.slow
class TestCrosCloudConsistency:
    """
    Test consistency across cloud providers
    Ensures all backends behave identically
    """

    def test_response_format_consistency(self):
        """Test that all clouds return consistent response formats"""
        results = {}

        for provider, endpoint in ENDPOINTS.items():
            if not endpoint:
                continue

            try:
                response = requests.get(f"{endpoint}/api/messages/", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    results[provider] = {
                        "has_messages": "messages" in data or "items" in data or "results" in data,
                        "has_pagination": any(k in data for k in ["page", "limit", "nextToken", "page_size"]),
                        "keys": list(data.keys()),
                    }
            except Exception as e:
                results[provider] = {"error": str(e)}

        if not results:
            pytest.skip("No endpoints configured")

        # All accessible clouds should have similar structure
        has_messages_count = sum(1 for r in results.values() if r.get("has_messages"))
        if has_messages_count > 0:
            assert has_messages_count == len([r for r in results.values() if "error" not in r]), \
                f"Inconsistent response formats: {results}"

    def test_api_version_consistency(self):
        """Test that all clouds report the same API version"""
        versions = {}

        for provider, endpoint in ENDPOINTS.items():
            if not endpoint:
                continue

            try:
                response = requests.get(f"{endpoint}/", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    versions[provider] = data.get("version")
            except Exception:
                pass

        if len(versions) > 1:
            # All versions should be the same
            unique_versions = set(versions.values())
            assert len(unique_versions) == 1, f"Inconsistent versions: {versions}"
