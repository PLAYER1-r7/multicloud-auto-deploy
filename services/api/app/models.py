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


class PlotCurve(BaseModel):
    """図示用パラメトリック曲線または関数"""

    type: str = "parametric"  # "parametric" | "function"
    x: str | None = None  # mathjs 式 (t の関数)
    y: str | None = None  # mathjs 式 (t の関数)
    fn: str | None = None  # mathjs 式 (x の関数)
    t_min: float | None = Field(None, alias="tMin")
    t_max: float | None = Field(None, alias="tMax")
    label: str | None = None

    model_config = {"populate_by_name": True}


class PlotPoint(BaseModel):
    """図示用点"""

    x: float
    y: float
    label: str | None = None


class PlotSegment(BaseModel):
    """図示用線分"""

    from_point: list[float] = Field(alias="from")
    to: list[float]
    label: str | None = None

    model_config = {"populate_by_name": True}


class PlotViewBox(BaseModel):
    """図示用ビューボックス"""

    x_min: float = Field(alias="xMin")
    x_max: float = Field(alias="xMax")
    y_min: float = Field(alias="yMin")
    y_max: float = Field(alias="yMax")

    model_config = {"populate_by_name": True}


class PlotData(BaseModel):
    """AI が生成する図示データ"""

    need_plot: bool = Field(True, alias="needPlot")
    curves: list[PlotCurve] = Field(default_factory=list)
    segments: list[PlotSegment] = Field(default_factory=list)
    points: list[PlotPoint] = Field(default_factory=list)
    view_box: PlotViewBox | None = Field(None, alias="viewBox")

    model_config = {"populate_by_name": True}


class SolveAnswer(BaseModel):
    """AI解答"""

    final: str
    latex: str | None = None
    steps: list[str] = Field(default_factory=list)
    diagram_guide: str | None = Field(None, alias="diagramGuide")
    plot_data: PlotData | None = Field(None, alias="plotData")
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


# ========================================================================== #
# Learning Material Models (AWS Learning Assistant)
# ========================================================================== #


class LearningOutlineStep(BaseModel):
    """学習アウトラインの各ステップ"""

    step_number: int = Field(alias="stepNumber")
    brief: str  # 1行簡潔版
    details: str | None = None  # オプション：詳細説明
    key_formula: str | None = Field(None, alias="keyFormula")

    model_config = {"populate_by_name": True}


class QuizQuestion(BaseModel):
    """自動生成クイズ問題"""

    question_id: str = Field(alias="questionId")
    question_type: str = Field(
        alias="questionType"
    )  # "fill_blank", "multiple_choice", "short_answer"
    question_text: str = Field(alias="questionText")
    options: list[str] | None = None  # Multiple choice の場合のみ
    answer: str
    explanation: str | None = None

    model_config = {"populate_by_name": True}


class CommonMistake(BaseModel):
    """よくある間違いと対策"""

    mistake_description: str = Field(alias="mistakeDescription")
    why_wrong: str = Field(alias="whyWrong")
    correction: str
    prevention_tip: str | None = Field(None, alias="preventionTip")

    model_config = {"populate_by_name": True}


class ReferenceProblem(BaseModel):
    """関連する参考問題（別の大学/年度）"""

    university: str
    year: int | None = None
    question_no: str = Field(alias="questionNo")
    similarity_score: float = Field(alias="similarityScore")  # 0.0-1.0

    model_config = {"populate_by_name": True}


class LearningMaterial(BaseModel):
    """AWS Learning Assistant 向け統合学習教材"""

    # Basic ID & Metadata
    material_id: str = Field(alias="materialId")
    created_at: str = Field(alias="createdAt")
    source_solve_response: str | None = Field(
        None, alias="sourceSolveResponseId"
    )  # 元の SolveResponse ID

    # Problem & Solution (from Azure/GCP SolveResponse)
    exam_metadata: SolveExam = Field(alias="examMetadata")
    problem_text: str = Field(alias="problemText")
    problem_image_url: str | None = Field(None, alias="problemImageUrl")

    # Solution from Azure/GCP
    solution_final: str = Field(alias="solutionFinal")
    solution_steps: list[str] = Field(alias="solutionSteps")
    solution_latex: str | None = Field(None, alias="solutionLatex")
    solution_confidence: float = Field(ge=0.0, le=1.0, alias="solutionConfidence")
    ocr_provider: str = Field(alias="ocrProvider")  # "azure" or "gcp"

    # Learning Material Enhancements (generated/extracted)
    outline: list[LearningOutlineStep] = Field(
        default_factory=list
    )  # 各ステップを簡潔化
    key_concepts: list[str] = Field(default_factory=list, alias="keyConcepts")
    quiz_questions: list[QuizQuestion] = Field(
        default_factory=list, alias="quizQuestions"
    )
    common_mistakes: list[CommonMistake] = Field(
        default_factory=list, alias="commonMistakes"
    )
    additional_examples: list[str] = Field(
        default_factory=list, alias="additionalExamples"
    )
    reference_problems: list[ReferenceProblem] = Field(
        default_factory=list, alias="referenceProblems"
    )

    # Difficulty & Learning Goals
    difficulty_level: str = Field("intermediate")  # "basic", "intermediate", "advanced"
    learning_objectives: list[str] = Field(
        default_factory=list, alias="learningObjectives"
    )

    # AWS Personalization tracking
    aws_personalization_score: float = Field(
        default=0.5, alias="awsPersonalizationScore"
    )

    model_config = {"populate_by_name": True}


class EnhancedLearningMaterial(BaseModel):
    """PHASE 2: Bedrock/Polly/Personalize で拡張された学習教材"""

    # PHASE 1 の基本教材
    base_material: LearningMaterial = Field(alias="baseMaterial")

    # PHASE 2: Bedrock による詳細解説
    detailed_explanation: str | None = Field(None, alias="detailedExplanation")
    concept_deep_dives: dict[str, str] = Field(
        default_factory=dict, alias="conceptDeepDives"
    )
    mistake_analysis: list[str] = Field(default_factory=list, alias="mistakeAnalysis")

    # PHASE 2: Polly による音声化
    audio_urls: dict[str, str] | None = Field(
        None, alias="audioUrls"
    )  # "explanation", "step_1", etc.
    audio_format: str = Field("mp3", alias="audioFormat")  # "mp3", "wav"
    generated_at: str | None = Field(None, alias="generatedAt")

    # PHASE 2: Personalize による推薦
    personalized_recommendations: list[str] = Field(
        default_factory=list, alias="personalizedRecommendations"
    )
    related_materials: list[str] = Field(default_factory=list, alias="relatedMaterials")
    personalization_score: float = Field(default=0.0, alias="personalizationScore")

    # Enhancement metadata
    enhancement_timestamp: str | None = Field(None, alias="enhancementTimestamp")
    enhancement_models: dict[str, str] = Field(
        default_factory=dict, alias="enhancementModels"
    )  # {"bedrock": "...", "polly": "...", ...}
    is_fully_enhanced: bool = Field(False, alias="isFullyEnhanced")

    model_config = {"populate_by_name": True}
