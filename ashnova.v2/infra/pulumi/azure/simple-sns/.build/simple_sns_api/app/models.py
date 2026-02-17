import re
from typing import List, Optional

from pydantic import BaseModel, field_validator

MAX_CONTENT_LENGTH = 5000
MAX_TAGS = 100
MAX_TAG_LENGTH = 50
MAX_IMAGES = 16
MAX_BASE64_IMAGES = 10

TAG_REGEX = re.compile(r"^[\w\-\.あ-んア-ヶー一-龯]{1,50}$")
IMAGE_KEY_REGEX = re.compile(
    r"^images/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}-\d+-[a-f0-9]{16}\.(jpeg|jpg|png|heic|heif)$",
    re.I,
)
DATA_URL_REGEX = re.compile(
    r"^data:image/(jpeg|jpg|png|gif|webp);base64,", re.I)
BASE64_REGEX = re.compile(r"^[A-Za-z0-9+/=]+$")
DANGEROUS_CONTENT_PATTERNS = [
    re.compile(r"<script[\s\S]*?>[\s\S]*?</script>", re.I),
    re.compile(r"javascript:", re.I),
    re.compile(r"on\w+\s*=", re.I),
]
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
}


class CreatePostBody(BaseModel):
    content: str
    imageKeys: Optional[List[str]] = None
    image: Optional[str] = None
    images: Optional[List[str]] = None
    isMarkdown: Optional[bool] = None
    tags: Optional[List[str]] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("content is required")
        if len(value) > MAX_CONTENT_LENGTH:
            raise ValueError(
                f"content too long (max {MAX_CONTENT_LENGTH} chars)")
        if any(pattern.search(value) for pattern in DANGEROUS_CONTENT_PATTERNS):
            raise ValueError("Content contains potentially unsafe patterns")
        return value

    @field_validator("imageKeys")
    @classmethod
    def validate_image_keys(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        if len(value) > MAX_IMAGES:
            raise ValueError(f"Too many images (max {MAX_IMAGES})")
        if len(set(value)) != len(value):
            raise ValueError("Duplicate image keys are not allowed")
        for key in value:
            if not IMAGE_KEY_REGEX.match(key):
                raise ValueError("Invalid image key format")
        return value

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not DATA_URL_REGEX.match(value):
            raise ValueError("Invalid or unsupported image format")
        if len(value) > 7 * 1024 * 1024:
            raise ValueError("Image too large (max 7MB)")
        base64_data = value.split(",", 1)[1] if "," in value else ""
        if not base64_data or not BASE64_REGEX.match(base64_data):
            raise ValueError("Invalid base64 image data")
        return value

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        if len(value) > MAX_BASE64_IMAGES:
            raise ValueError(f"Too many images (max {MAX_BASE64_IMAGES})")
        for image in value:
            cls.validate_image(image)
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        if len(value) > MAX_TAGS:
            raise ValueError(f"Too many tags (max {MAX_TAGS})")
        if len(set(value)) != len(value):
            raise ValueError("Duplicate tags are not allowed")
        for tag in value:
            if len(tag) > MAX_TAG_LENGTH or not TAG_REGEX.match(tag):
                raise ValueError("Invalid tag format")
        return value


class UploadUrlsRequest(BaseModel):
    count: int
    contentTypes: Optional[List[str]] = None

    @field_validator("count")
    @classmethod
    def validate_count(cls, value: int) -> int:
        if value < 1 or value > MAX_IMAGES:
            raise ValueError(f"count must be between 1 and {MAX_IMAGES}")
        return value

    @field_validator("contentTypes")
    @classmethod
    def validate_content_types(
        cls, value: Optional[List[str]], info
    ) -> Optional[List[str]]:
        if value is None:
            return value
        if len(value) == 0:
            raise ValueError("contentTypes must not be empty")
        count = info.data.get("count") if info and info.data else None
        if isinstance(count, int) and len(value) != count:
            raise ValueError("contentTypes length must match count")
        for content_type in value:
            if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                raise ValueError("Unsupported image content type")
        return value


class ProfileUpdateRequest(BaseModel):
    nickname: str

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 1:
            raise ValueError("nickname is required")
        if len(value) > 50:
            raise ValueError("nickname must be <= 50 chars")
        return value


class Post(BaseModel):
    postId: str
    userId: str
    nickname: Optional[str] = None
    content: str
    createdAt: str
    imageUrls: Optional[List[str]] = None
    isMarkdown: Optional[bool] = None
    tags: Optional[List[str]] = None


class ListPostsResponse(BaseModel):
    items: List[Post]
    limit: int
    nextToken: Optional[str] = None


class ProfileResponse(BaseModel):
    userId: str
    nickname: str
    updatedAt: Optional[str] = None
    createdAt: Optional[str] = None
