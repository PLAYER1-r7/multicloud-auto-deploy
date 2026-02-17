from fastapi import APIRouter, Depends, Query

from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.models import CreatePostBody, ListPostsResponse

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("")
def list_posts(
    limit: int = Query(20, ge=1, le=50),
    nextToken: str | None = None,
    tag: str | None = None,
) -> ListPostsResponse:
    backend = get_backend()
    posts, output_next_token = backend.list_posts(limit, nextToken, tag)
    return ListPostsResponse(items=posts, limit=limit, nextToken=output_next_token)


@router.post("")
def create_post(body: CreatePostBody, user: UserInfo = Depends(require_user)) -> dict:
    backend = get_backend()
    return backend.create_post(body, user)


@router.delete("/{post_id}")
def delete_post(post_id: str, user: UserInfo = Depends(require_user)) -> dict:
    backend = get_backend()
    return backend.delete_post(post_id, user)
