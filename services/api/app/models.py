from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_serializer


class CloudProvider(str, Enum):
    """クラウドプロバイダーの列挙型"""

    LOCAL = "local"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class Post(BaseModel):
    """投稿モデル"""

    id: str = Field(..., alias="postId")
    user_id: str = Field(..., alias="userId")
    nickname: str | None = None
    content: str
    is_markdown: bool = Field(False, alias="isMarkdown")
    image_urls: list[str] | None = Field(None, alias="imageUrls")
    tags: list[str] | None = None
    created_at: str = Field(..., alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}

    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """後方互換性: snake_case と camelCase 両方のフィールド名を返す"""
        return {
            # camelCase (ashnova.v3 形式)
            "postId": self.id,
            "userId": self.user_id,
            "nickname": self.nickname,
            "content": self.content,
            "isMarkdown": self.is_markdown,
            "imageUrls": self.image_urls,
            "tags": self.tags,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            # snake_case (frontend_react 形式)
            "id": self.id,
            "author": self.user_id,  # userId を author としても返す
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "image_url": self.image_urls[0] if self.image_urls else None,
        }


class CreatePostBody(BaseModel):
    """投稿作成リクエスト"""

    content: str = Field(..., min_length=1, max_length=10000)
    is_markdown: bool = Field(False, alias="isMarkdown")
    image_keys: list[str] | None = Field(
        None, alias="imageKeys"
    )  # 枚数制限はルートで settings.max_images_per_post により強制
    tags: list[str] | None = Field(None, max_length=10)

    model_config = {"populate_by_name": True}


class UpdatePostBody(BaseModel):
    """投稿更新リクエスト（全フィールドオプション）"""

    content: str | None = Field(None, min_length=1, max_length=10000)
    is_markdown: bool | None = Field(None, alias="isMarkdown")
    image_keys: list[str] | None = Field(None, alias="imageKeys")
    tags: list[str] | None = Field(None, max_length=10)

    model_config = {"populate_by_name": True}


class ListPostsResponse(BaseModel):
    """投稿一覧レスポンス"""

    items: list[Post]
    limit: int
    next_token: str | None = Field(None, alias="nextToken")

    model_config = {"populate_by_name": True}

    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """後方互換性: results と messages フィールドを追加"""
        return {
            "items": self.items,
            "results": self.items,  # ashnova.v1 互換
            "messages": self.items,  # frontend_react 互換
            "limit": self.limit,
            "nextToken": self.next_token,
            "total": len(self.items),  # frontend_react 互換
            "page": 1,  # frontend_react 互換
            "page_size": self.limit,  # frontend_react 互換
        }


class ProfileResponse(BaseModel):
    """プロフィールレスポンス"""

    user_id: str = Field(..., alias="userId")
    nickname: str | None = None
    bio: str | None = None
    avatar_url: str | None = Field(None, alias="avatarUrl")
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class ProfileUpdateRequest(BaseModel):
    """プロフィール更新リクエスト"""

    nickname: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    avatar_key: str | None = Field(None, alias="avatarKey")

    model_config = {"populate_by_name": True}


class UploadUrlsRequest(BaseModel):
    """アップロードURL生成リクエスト"""

    count: int = Field(
        ..., ge=1, le=100
    )  # 絶対上限 100、実際の制限は settings.max_images_per_post
    content_types: list[str] | None = Field(
        None,
        alias="contentTypes",
        description="各ファイルのContent-Type (image/jpeg, image/png 等)",
    )

    model_config = {"populate_by_name": True}


class UploadUrlsResponse(BaseModel):
    """アップロードURLレスポンス"""

    urls: list[dict[str, str]]  # [{"uploadUrl": "...", "key": "..."}]


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str
    provider: str
    version: str = "3.0.0"


class SolveInput(BaseModel):
    """数学問題画像入力"""

    image_base64: str | None = Field(None, alias="imageBase64")
    image_url: str | None = Field(None, alias="imageUrl")
    source: str = Field("paste", pattern="^(paste|upload|url)$")

    model_config = {"populate_by_name": True}


class SolveExam(BaseModel):
    """試験メタデータ"""

    university: str = "tokyo"
    year: int | None = None
    subject: str = "math"
    question_no: str | None = Field(None, alias="questionNo")

    model_config = {"populate_by_name": True}


class SolveOptions(BaseModel):
    """解答オプション"""

    mode: str = Field("fast", pattern="^(fast|accurate)$")
    need_steps: bool = Field(True, alias="needSteps")
    need_latex: bool = Field(True, alias="needLatex")
    max_tokens: int = Field(2000, alias="maxTokens", ge=256, le=16384)
    debug_ocr: bool = Field(False, alias="debugOcr")

    model_config = {"populate_by_name": True}


class SolveRequest(BaseModel):
    """数学問題解答リクエスト"""

    input: SolveInput
    exam: SolveExam = Field(default_factory=SolveExam)
    options: SolveOptions = Field(default_factory=SolveOptions)


class SolveAnswer(BaseModel):
    """AI解答"""

    final: str
    latex: str | None = None
    steps: list[str] = Field(default_factory=list)
    diagram_guide: str | None = Field(None, alias="diagramGuide")
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"populate_by_name": True}


class SolveMeta(BaseModel):
    """実行メタ情報"""

    ocr_provider: str = Field(alias="ocrProvider")
    ocr_source: str | None = Field(default=None, alias="ocrSource")
    ocr_score: float | None = Field(default=None, alias="ocrScore")
    ocr_candidates: int | None = Field(default=None, alias="ocrCandidates")
    ocr_top_candidates: list[dict[str, float | str]] | None = Field(
        default=None, alias="ocrTopCandidates"
    )
    ocr_debug_texts: list[dict] | None = Field(default=None, alias="ocrDebugTexts")
    structured_problem: dict | None = Field(default=None, alias="structuredProblem")
    ocr_replacement_ratio: float | None = Field(
        default=None, alias="ocrReplacementRatio"
    )
    ocr_non_ascii_ratio: float | None = Field(default=None, alias="ocrNonAsciiRatio")
    ocr_needs_review: bool | None = Field(default=None, alias="ocrNeedsReview")
    model: str
    latency_ms: int = Field(alias="latencyMs")
    cost_usd: float = Field(alias="costUsd")

    model_config = {"populate_by_name": True}


class SolveResponse(BaseModel):
    """数学問題解答レスポンス"""

    request_id: str = Field(alias="requestId")
    status: str
    problem_text: str = Field(alias="problemText")
    answer: SolveAnswer
    meta: SolveMeta

    model_config = {"populate_by_name": True}
