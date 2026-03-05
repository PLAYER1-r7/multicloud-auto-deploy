from enum import Enum

from pydantic import BaseModel, Field


class CloudProvider(str, Enum):
    """クラウドプロバイダーの列挙型"""

    LOCAL = "local"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str
    provider: str


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
    """AI が生成する図示データ (2D)"""

    need_plot: bool = Field(True, alias="needPlot")
    dimension: int = Field(2, ge=2, le=3)
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
    ocr_debug_texts: list[dict] | None = Field(default=None, alias="ocrDebugTexts")
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
