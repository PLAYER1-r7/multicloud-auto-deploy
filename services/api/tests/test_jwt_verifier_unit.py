"""Unit tests for app.jwt_verifier."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from jose import JWTError

from app.jwt_verifier import JWTVerifier


class TestJWTVerifierConfig:
    def test_get_jwks_uri_cognito(self):
        verifier = JWTVerifier(
            "cognito",
            {
                "region": "ap-northeast-1",
                "user_pool_id": "pool123",
                "client_id": "client",
            },
        )
        assert verifier.get_jwks_uri() == (
            "https://cognito-idp.ap-northeast-1.amazonaws.com/pool123/.well-known/jwks.json"
        )

    def test_get_jwks_uri_firebase(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        assert (
            verifier.get_jwks_uri()
            == "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
        )

    def test_get_jwks_uri_azure_standard(self):
        verifier = JWTVerifier(
            "azure", {"tenant_id": "tenant-id", "client_id": "client"}
        )
        assert (
            verifier.get_jwks_uri()
            == "https://login.microsoftonline.com/tenant-id/discovery/v2.0/keys"
        )

    def test_get_jwks_uri_azure_b2c(self):
        verifier = JWTVerifier(
            "azure",
            {
                "tenant_id": "tenant-id",
                "tenant_name": "mytenant",
                "client_id": "client",
                "is_b2c": True,
                "policy": "B2C_1_signupsignin",
            },
        )
        assert verifier.get_jwks_uri() == (
            "https://mytenant.b2clogin.com/mytenant.onmicrosoft.com/B2C_1_signupsignin/discovery/v2.0/keys"
        )

    def test_get_jwks_uri_unsupported_provider(self):
        verifier = JWTVerifier("unknown", {})
        with pytest.raises(ValueError):
            verifier.get_jwks_uri()

    def test_get_issuer_and_audience_cognito(self):
        verifier = JWTVerifier(
            "cognito",
            {
                "region": "us-east-1",
                "user_pool_id": "pool-id",
                "client_id": "client-id",
            },
        )
        assert (
            verifier.get_issuer()
            == "https://cognito-idp.us-east-1.amazonaws.com/pool-id"
        )
        assert verifier.get_audience() == "client-id"

    def test_get_issuer_and_audience_firebase(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj-1"})
        assert verifier.get_issuer() == "https://securetoken.google.com/proj-1"
        assert verifier.get_audience() == "proj-1"

    def test_get_issuer_and_audience_azure(self):
        verifier = JWTVerifier(
            "azure", {"tenant_id": "tenant-1", "client_id": "client-1"}
        )
        assert (
            verifier.get_issuer() == "https://login.microsoftonline.com/tenant-1/v2.0"
        )
        assert verifier.get_audience() == "client-1"


class TestJWTVerifierJWKS:
    @patch("app.jwt_verifier.requests.get")
    def test_get_jwks_uses_cache(self, mock_get):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})

        mock_response = Mock()
        mock_response.json.return_value = {"keys": [{"kid": "k1"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        first = verifier.get_jwks()
        second = verifier.get_jwks()

        assert first == second
        assert mock_get.call_count == 1

    @patch("app.jwt_verifier.requests.get")
    def test_get_jwks_uses_expired_cache_on_fetch_error(self, mock_get):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        verifier._jwks_cache = {"keys": [{"kid": "cached"}]}
        verifier._jwks_cache_time = datetime.now() - timedelta(hours=2)
        mock_get.side_effect = RuntimeError("network error")

        result = verifier.get_jwks()
        assert result == {"keys": [{"kid": "cached"}]}


class TestJWTVerifierTokenVerification:
    def test_verify_token_missing_kid(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})

        with patch.object(verifier, "get_jwks", return_value={"keys": [{"kid": "k1"}]}):
            with patch("app.jwt_verifier.jwt.get_unverified_header", return_value={}):
                assert verifier.verify_token("token") is None

    def test_verify_token_no_matching_key(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})

        with (
            patch.object(
                verifier, "get_jwks", return_value={"keys": [{"kid": "other"}]}
            ),
            patch(
                "app.jwt_verifier.jwt.get_unverified_header", return_value={"kid": "k1"}
            ),
        ):
            assert verifier.verify_token("token") is None

    def test_verify_token_success_without_aud_claim(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        key = {"kid": "k1"}
        claims = {"sub": "user-1", "email": "u@example.com"}

        with patch.object(verifier, "get_jwks", return_value={"keys": [key]}):
            with patch(
                "app.jwt_verifier.jwt.get_unverified_header", return_value={"kid": "k1"}
            ):
                with patch(
                    "app.jwt_verifier.jwt.get_unverified_claims",
                    return_value={"sub": "user-1"},
                ):
                    with patch("app.jwt_verifier.jwt.decode", return_value=claims):
                        result = verifier.verify_token("token")

        assert result == claims

    def test_verify_token_jwt_error_returns_none(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        key = {"kid": "k1"}

        with patch.object(verifier, "get_jwks", return_value={"keys": [key]}):
            with patch(
                "app.jwt_verifier.jwt.get_unverified_header", return_value={"kid": "k1"}
            ):
                with patch(
                    "app.jwt_verifier.jwt.get_unverified_claims",
                    return_value={"aud": "proj"},
                ):
                    with patch(
                        "app.jwt_verifier.jwt.decode", side_effect=JWTError("bad token")
                    ):
                        assert verifier.verify_token("token") is None

    def test_verify_token_unverified_claims_exception_handled(self):
        """Test that exception in get_unverified_claims is handled gracefully"""
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        key = {"kid": "k1"}
        claims = {"sub": "user-1"}

        with patch.object(verifier, "get_jwks", return_value={"keys": [key]}):
            with patch(
                "app.jwt_verifier.jwt.get_unverified_header", return_value={"kid": "k1"}
            ):
                with patch(
                    "app.jwt_verifier.jwt.get_unverified_claims",
                    side_effect=Exception("decode error"),
                ):
                    with patch("app.jwt_verifier.jwt.decode", return_value=claims):
                        result = verifier.verify_token("token")
                        assert result == claims

    def test_verify_token_general_exception_returns_none(self):
        """Test that general exceptions in decode are caught and return None"""
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        key = {"kid": "k1"}

        with patch.object(verifier, "get_jwks", return_value={"keys": [key]}):
            with patch(
                "app.jwt_verifier.jwt.get_unverified_header", return_value={"kid": "k1"}
            ):
                with patch(
                    "app.jwt_verifier.jwt.get_unverified_claims",
                    return_value={"sub": "user-1"},
                ):
                    with patch(
                        "app.jwt_verifier.jwt.decode",
                        side_effect=RuntimeError("signature error"),
                    ):
                        assert verifier.verify_token("token") is None


class TestJWTVerifierUserExtraction:
    def test_extract_user_info_cognito_with_fallback_username(self):
        verifier = JWTVerifier(
            "cognito", {"client_id": "client", "user_pool_id": "pool"}
        )
        claims = {
            "username": "cognito-user",
            "email": "cog@example.com",
            "cognito:groups": ["Admins"],
        }
        user_info = verifier.extract_user_info(claims)
        assert user_info["user_id"] == "cognito-user"
        assert user_info["email"] == "cog@example.com"
        assert user_info["groups"] == ["Admins"]

    def test_extract_user_info_firebase(self):
        verifier = JWTVerifier("firebase", {"project_id": "proj"})
        claims = {"sub": "uid-1", "email": "fb@example.com", "groups": ["Users"]}
        user_info = verifier.extract_user_info(claims)
        assert user_info == {
            "user_id": "uid-1",
            "email": "fb@example.com",
            "groups": ["Users"],
        }

    def test_extract_user_info_azure_prefers_preferred_username(self):
        verifier = JWTVerifier("azure", {"tenant_id": "tenant", "client_id": "client"})
        claims = {
            "sub": "azure-user",
            "preferred_username": "azure@example.com",
            "email": "fallback@example.com",
            "groups": ["Dev"],
        }
        user_info = verifier.extract_user_info(claims)
        assert user_info["user_id"] == "azure-user"
        assert user_info["email"] == "azure@example.com"
        assert user_info["groups"] == ["Dev"]
