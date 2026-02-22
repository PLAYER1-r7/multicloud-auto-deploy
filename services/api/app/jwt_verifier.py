"""
JWT Token Verification for Multi-Cloud Authentication

Supports:
- AWS Cognito
- Firebase Authentication (GCP)
- Azure AD / Azure AD B2C
"""

import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Optional

import requests
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class JWTVerifier:
    """JWT verification for multiple cloud providers"""

    def __init__(self, provider: str, config: dict[str, Any]):
        """
        Initialize JWT verifier

        Args:
            provider: 'cognito', 'firebase', or 'azure'
            config: Provider-specific configuration
        """
        self.provider = provider
        self.config = config
        self._jwks_cache: Optional[dict] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._jwks_cache_duration = timedelta(hours=1)

    @lru_cache(maxsize=10)  # noqa: B019
    def get_jwks_uri(self) -> str:
        """Get JWKS URI based on provider"""
        if self.provider == "cognito":
            region = self.config.get("region", "ap-northeast-1")
            user_pool_id = self.config["user_pool_id"]
            return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"

        elif self.provider == "firebase":
            # Firebase uses Google's public keys
            return "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"

        elif self.provider == "azure":
            tenant_id = self.config["tenant_id"]
            # For Azure AD B2C, use different discovery endpoint
            if self.config.get("is_b2c", False):
                tenant_name = self.config["tenant_name"]
                policy = self.config.get("policy", "B2C_1_signupsignin")
                return f"https://{tenant_name}.b2clogin.com/{tenant_name}.onmicrosoft.com/{policy}/discovery/v2.0/keys"
            else:
                return (
                    f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
                )

        raise ValueError(f"Unsupported provider: {self.provider}")

    def get_jwks(self) -> dict:
        """Get JWKS with caching"""
        now = datetime.now()

        # Check cache
        if (
            self._jwks_cache is not None
            and self._jwks_cache_time is not None
            and now - self._jwks_cache_time < self._jwks_cache_duration
        ):
            return self._jwks_cache

        # Fetch from provider
        try:
            jwks_uri = self.get_jwks_uri()
            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()

            self._jwks_cache = response.json()
            self._jwks_cache_time = now

            return self._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # If cache exists, use it even if expired
            if self._jwks_cache:
                logger.warning("Using expired JWKS cache")
                return self._jwks_cache
            raise

    def get_issuer(self) -> str:
        """Get expected issuer for token validation"""
        if self.provider == "cognito":
            region = self.config.get("region", "ap-northeast-1")
            user_pool_id = self.config["user_pool_id"]
            return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"

        elif self.provider == "firebase":
            project_id = self.config["project_id"]
            return f"https://securetoken.google.com/{project_id}"

        elif self.provider == "azure":
            tenant_id = self.config["tenant_id"]
            if self.config.get("is_b2c", False):
                tenant_name = self.config["tenant_name"]
                policy = self.config.get("policy", "B2C_1_signupsignin")
                return f"https://{tenant_name}.b2clogin.com/{tenant_id}/{policy}/v2.0/"
            else:
                return f"https://login.microsoftonline.com/{tenant_id}/v2.0"

        raise ValueError(f"Unsupported provider: {self.provider}")

    def get_audience(self) -> str:
        """Get expected audience for token validation"""
        if self.provider == "cognito":
            return self.config["client_id"]
        elif self.provider == "firebase":
            return self.config["project_id"]
        elif self.provider == "azure":
            return self.config["client_id"]
        raise ValueError(f"Unsupported provider: {self.provider}")

    def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        Verify JWT token and return claims

        Args:
            token: JWT token string

        Returns:
            Token claims if valid, None otherwise
        """
        try:
            # Get JWKS
            jwks = self.get_jwks()

            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                logger.error("Token missing 'kid' in header")
                return None

            # Find matching key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break

            if not key:
                logger.error(f"No matching key found for kid: {kid}")
                return None

            # Verify and decode token
            issuer = self.get_issuer()
            audience = self.get_audience()

            # Check if token has 'aud' claim before verifying it.
            # Cognito access tokens may omit 'aud'; in that case relax audience verification.
            try:
                unverified_claims = jwt.get_unverified_claims(token)
            except Exception:
                unverified_claims = {}
            has_aud = "aud" in unverified_claims

            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=audience if has_aud else None,
                issuer=issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": has_aud,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    # id_token contains at_hash (hash of access_token).
                    # We decode id_token standalone (no access_token companion),
                    # so disable at_hash verification.
                    "verify_at_hash": False,
                },
            )

            logger.info(
                f"Token verified successfully for user: {claims.get('sub')}")
            return claims

        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    def extract_user_info(self, claims: dict[str, Any]) -> dict[str, Any]:
        """
        Extract user information from token claims

        Returns standardized user info regardless of provider
        """
        user_info = {
            "user_id": claims.get("sub"),
            "email": None,
            "groups": [],
        }

        if self.provider == "cognito":
            user_info["email"] = claims.get("email")
            # access_token uses 'username', id_token uses 'cognito:username'
            if not user_info["user_id"]:
                user_info["user_id"] = claims.get("username")
            user_info["groups"] = claims.get("cognito:groups", [])

        elif self.provider == "firebase":
            user_info["email"] = claims.get("email")
            # Firebase custom claims for groups
            user_info["groups"] = claims.get("groups", [])

        elif self.provider == "azure":
            user_info["email"] = claims.get(
                "preferred_username") or claims.get("email")
            user_info["groups"] = claims.get("groups", [])

        return user_info
