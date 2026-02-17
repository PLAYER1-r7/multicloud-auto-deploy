# Azure Backend Implementation
# TODO: Implement based on ashnova.v2

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, UpdatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo
from typing import Optional, Tuple

class AzureBackend(BackendBase):
    """Azure実装 (Cosmos DB + Blob Storage + Azure AD)"""
    
    def __init__(self):
        # TODO: Initialize Azure clients (Cosmos DB, Blob Storage)
        pass
    
    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        # TODO: Implement using Cosmos DB query
        raise NotImplementedError("Azure backend not yet implemented")
    
    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        # TODO: Implement using Cosmos DB create_item
        raise NotImplementedError("Azure backend not yet implemented")
    
    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        # TODO: Implement using Cosmos DB delete_item
        raise NotImplementedError("Azure backend not yet implemented")
    
    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        # TODO: Implement using Cosmos DB patch_item or replace_item
        raise NotImplementedError("Azure backend not yet implemented")
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        # TODO: Implement using Cosmos DB read_item
        raise NotImplementedError("Azure backend not yet implemented")
    
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        # TODO: Implement using Cosmos DB upsert_item
        raise NotImplementedError("Azure backend not yet implemented")
    
    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        # TODO: Implement using Blob Storage SAS URLs
        raise NotImplementedError("Azure backend not yet implemented")
