# GCP Backend Implementation
# TODO: Implement based on ashnova.v2

from app.backends.base import BackendBase
from app.models import Post, CreatePostBody, UpdatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo
from typing import Optional, Tuple

class GcpBackend(BackendBase):
    """GCP実装 (Firestore + Cloud Storage + Firebase Auth)"""
    
    def __init__(self):
        # TODO: Initialize GCP clients (Firestore, Cloud Storage)
        pass
    
    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        # TODO: Implement using Firestore query
        raise NotImplementedError("GCP backend not yet implemented")
    
    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        # TODO: Implement using Firestore add
        raise NotImplementedError("GCP backend not yet implemented")
    
    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        # TODO: Implement using Firestore delete
        raise NotImplementedError("GCP backend not yet implemented")
    
    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        # TODO: Implement using Firestore update
        raise NotImplementedError("GCP backend not yet implemented")
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        # TODO: Implement using Firestore get
        raise NotImplementedError("GCP backend not yet implemented")
    
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        # TODO: Implement using Firestore set with merge
        raise NotImplementedError("GCP backend not yet implemented")
    
    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        # TODO: Implement using Cloud Storage signed URLs
        raise NotImplementedError("GCP backend not yet implemented")
