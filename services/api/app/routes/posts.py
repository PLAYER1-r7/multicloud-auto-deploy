from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import UserInfo, require_user
from app.backends import get_backend
from app.models import CreatePostBody, ListPostsResponse, UpdatePostBody

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=ListPostsResponse)
def list_posts(
    limit: int = Query(20, ge=1, le=50, description="取得件数"),
    nextToken: str | None = Query(None, description="ページネーショントークン"),
    tag: str | None = Query(None, description="タグフィルター"),
) -> ListPostsResponse:
    """投稿一覧を取得"""
    backend = get_backend()
    posts, output_next_token = backend.list_posts(limit, nextToken, tag)
    return ListPostsResponse(items=posts, limit=limit, nextToken=output_next_token)


@router.get("/{post_id}")
def get_post(post_id: str) -> dict:
    """投稿を1件取得"""
    backend = get_backend()
    try:
        return backend.get_post(post_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Post not found") from exc


@router.post("", status_code=201)
def create_post(
    body: CreatePostBody,
    user: UserInfo = Depends(require_user),
) -> dict:
    """投稿を作成"""
    backend = get_backend()
    return backend.create_post(body, user)


@router.delete("/{post_id}")
def delete_post(
    post_id: str,
    user: UserInfo = Depends(require_user),
) -> dict:
    """投稿を削除"""
    backend = get_backend()
    return backend.delete_post(post_id, user)


@router.put("/{post_id}")
def update_post(
    post_id: str,
    body: UpdatePostBody,
    user: UserInfo = Depends(require_user),
) -> dict:
    """投稿を更新"""
    backend = get_backend()
    return backend.update_post(post_id, body, user)
