from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.models import Post, CreatePostBody, UpdatePostBody, ProfileResponse, ProfileUpdateRequest
from app.auth import UserInfo


class BackendBase(ABC):
    """
    バックエンドの抽象基底クラス
    
    すべてのクラウドプロバイダー実装はこのインターフェースに従う
    """
    
    @abstractmethod
    def list_posts(
        self,
        limit: int,
        next_token: Optional[str],
        tag: Optional[str],
    ) -> Tuple[list[Post], Optional[str]]:
        """
        投稿一覧を取得
        
        Args:
            limit: 取得件数
            next_token: ページネーショントークン
            tag: タグフィルター
            
        Returns:
            (投稿リスト, 次のページのトークン)
        """
        pass
    
    @abstractmethod
    def create_post(self, body: CreatePostBody, user: UserInfo) -> dict:
        """
        投稿を作成
        
        Args:
            body: 投稿内容
            user: ユーザー情報
            
        Returns:
            作成された投稿情報
        """
        pass
    
    @abstractmethod
    def delete_post(self, post_id: str, user: UserInfo) -> dict:
        """
        投稿を削除
        
        Args:
            post_id: 投稿ID
            user: ユーザー情報
            
        Returns:
            削除結果
        """
        pass
    
    @abstractmethod
    def update_post(self, post_id: str, body: UpdatePostBody, user: UserInfo) -> dict:
        """
        投稿を更新
        
        Args:
            post_id: 投稿ID
            body: 更新内容
            user: ユーザー情報
            
        Returns:
            更新された投稿情報
        """
        pass
    
    @abstractmethod
    def get_profile(self, user_id: str) -> ProfileResponse:
        """
        プロフィールを取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            プロフィール情報
        """
        pass
    
    @abstractmethod
    def update_profile(
        self,
        user: UserInfo,
        body: ProfileUpdateRequest,
    ) -> ProfileResponse:
        """
        プロフィールを更新
        
        Args:
            user: ユーザー情報
            body: 更新内容
            
        Returns:
            更新後のプロフィール
        """
        pass
    
    @abstractmethod
    def generate_upload_urls(self, count: int, user: UserInfo) -> list[dict[str, str]]:
        """
        画像アップロード用の署名付きURLを生成
        
        Args:
            count: URL数
            user: ユーザー情報
            
        Returns:
            [{"uploadUrl": "...", "key": "..."}, ...]
        """
        pass
