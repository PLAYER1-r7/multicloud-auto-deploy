"""
AWS Learning Assistant - Learning Material API ルート

エンドポイント:
  POST /v1/learn/materials/from-solve
  GET  /v1/learn/materials/{material_id}
  POST /v1/learn/materials/{material_id}/enhance
  POST /v1/learn/materials/{material_id}/audio
  GET  /v1/learn/users/{user_id}/recommendations
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models import (
    EnhancedLearningMaterial,
    LearningMaterial,
    SolveExam,
    SolveResponse,
)
from app.services.material_generator import MaterialGenerator
from bedrock_integration import BedrockIntegration
from personalize_integration import PersonalizeIntegration
from polly_integration import PollyIntegration

logger = logging.getLogger(__name__)

# 統合インスタンス（キャッシュ）
_bedrock_client: BedrockIntegration | None = None
_polly_client: PollyIntegration | None = None
_personalize_client: PersonalizeIntegration | None = None

# キャッシュ（拡張教材と音声）
_enhanced_cache: dict[str, EnhancedLearningMaterial] = {}
_audio_cache: dict[str, dict] = {}

router = APIRouter(prefix="/v1/learn", tags=["learning"])

# インメモリキャッシュ（実装: Material を一時保存）
_material_cache: dict[str, LearningMaterial] = {}


@router.post("/materials/from-solve")
async def create_material_from_solve_response(
    solve_response: SolveResponse,
    exam: SolveExam | None = None,
    problem_image_url: str | None = None,
) -> LearningMaterial:
    """
    Azure/GCP の SolveResponse から学習教材を生成

    リクエストボディ:
    ```json
    {
      "solveResponse": {...},  # SolveResponse オブジェクト
      "exam": {                 # オプション: SolveExam
        "university": "tokyo",
        "year": 2025,
        "subject": "math",
        "questionNo": "1"
      },
      "problemImageUrl": "http://..."  # オプション
    }
    ```

    レスポンス: LearningMaterial
    """
    if not exam:
        # デフォルト値を使用
        exam = SolveExam(university="tokyo")

    try:
        generator = MaterialGenerator()
        material = generator.generate_from_solve_response(
            solve_response=solve_response,
            exam=exam,
            problem_image_url=problem_image_url,
        )

        # キャッシュに保存
        _material_cache[material.material_id] = material

        return material
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"教材生成エラー: {str(e)}")


@router.get("/materials/{material_id}")
async def get_material(material_id: str) -> LearningMaterial:
    """
    生成済み教材を取得

    パラメータ:
      material_id: 教材ID

    レスポンス: LearningMaterial
    """
    if material_id not in _material_cache:
        raise HTTPException(status_code=404, detail="教材が見つかりません")

    return _material_cache[material_id]


@router.get("/materials/{material_id}/outline")
async def get_material_outline(material_id: str) -> dict:
    """
    教材の学習アウトラインを取得

    レスポンス:
    ```json
    {
      "materialId": "...",
      "outline": [...],
      "keyConcepts": [...],
      "difficultyLevel": "intermediate",
      "learningObjectives": [...]
    }
    ```
    """
    if material_id not in _material_cache:
        raise HTTPException(status_code=404, detail="教材が見つかりません")

    material = _material_cache[material_id]
    return {
        "material_id": material.material_id,
        "outline": [
            {
                "step_number": step.step_number,
                "brief": step.brief,
            }
            for step in material.outline
        ],
        "key_concepts": material.key_concepts,
        "difficulty_level": material.difficulty_level,
        "learning_objectives": material.learning_objectives,
    }


@router.get("/materials/{material_id}/quiz")
async def get_material_quiz(material_id: str) -> dict:
    """
    教材のクイズ問題を取得

    レスポンス:
    ```json
    {
      "materialId": "...",
      "quizQuestions": [...]
    }
    ```
    """
    if material_id not in _material_cache:
        raise HTTPException(status_code=404, detail="教材が見つかりません")

    material = _material_cache[material_id]
    return {
        "material_id": material.material_id,
        "quiz_questions": material.quiz_questions,
    }


@router.get("/materials/{material_id}/mistakes")
async def get_material_common_mistakes(material_id: str) -> dict:
    """
    教材のよくある間違いリストを取得

    レスポンス:
    ```json
    {
      "materialId": "...",
      "commonMistakes": [...]
    }
    ```
    """
    if material_id not in _material_cache:
        raise HTTPException(status_code=404, detail="教材が見つかりません")

    material = _material_cache[material_id]
    return {
        "material_id": material.material_id,
        "common_mistakes": material.common_mistakes,
    }


@router.get("/materials/{material_id}/references")
async def get_material_references(material_id: str) -> dict:
    """
    教材の参考問題を取得

    レスポンス:
    ```json
    {
      "materialId": "...",
      "referenceProblems": [...]
    }
    ```
    """
    if material_id not in _material_cache:
        raise HTTPException(status_code=404, detail="教材が見つかりません")

    material = _material_cache[material_id]
    return {
        "material_id": material.material_id,
        "reference_problems": material.reference_problems,
    }


@router.post("/materials/{material_id}/enhance")
async def enhance_material_with_bedrock(material_id: str) -> EnhancedLearningMaterial:
    """
    PHASE 2: Bedrock で教材を拡張（詳細解説、概念深掘り、間違い分析）

    パラメータ:
      material_id: 拡張する教材ID

    レスポンス: EnhancedLearningMaterial
    """
    global _bedrock_client

    if material_id not in _material_cache:
        raise HTTPException(status_code=404, detail="教材が見つかりません")

    base_material = _material_cache[material_id]

    try:
        # Bedrock クライアントを初期化
        if _bedrock_client is None:
            _bedrock_client = BedrockIntegration()

        # 教材を Bedrock で拡張
        logger.info(f"🔄 Enhancing material {material_id} with Bedrock...")

        # Bedrock から拡張データを取得
        detailed_explanation = _bedrock_client.generate_detailed_explanation(
            base_material.model_dump(by_alias=True)
        )
        concept_deep_dives = {}
        for concept in base_material.key_concepts:
            deepdive = _bedrock_client.generate_concept_deepdive(
                base_material.model_dump(by_alias=True), concept
            )
            if deepdive:
                concept_deep_dives[concept] = deepdive

        mistake_analysis = (
            _bedrock_client.analyze_common_mistakes(
                base_material.model_dump(by_alias=True)
            )
            or []
        )

        # 拡張教材を構築
        enhanced_material = EnhancedLearningMaterial(
            base_material=base_material,
            detailed_explanation=detailed_explanation,
            concept_deep_dives=concept_deep_dives,
            mistake_analysis=mistake_analysis,
            enhancement_timestamp=base_material.created_at,
            enhancement_models={
                "bedrock": "anthropic.claude-3-sonnet-20240229-v1:0",
            },
            is_fully_enhanced=True,
        )

        # キャッシュに保存（enhance/audio エンドポイント用）
        _enhanced_cache[material_id] = enhanced_material

        logger.info(f"✅ Material {material_id} enhanced successfully")
        return enhanced_material

    except Exception as e:
        logger.error(f"❌ Enhancement failed: {str(e)}")
        # フォールバック: モック拡張を返す
        return EnhancedLearningMaterial(
            base_material=base_material,
            detailed_explanation="（Bedrock 接続エラー）詳細解説が利用できません。基本教材をご参照ください。",
            concept_deep_dives={},
            mistake_analysis=["❌ システムエラー: 間違い分析が利用できません。"],
            enhancement_models={},
            is_fully_enhanced=False,
        )


@router.post("/materials/{material_id}/audio")
async def generate_material_audio(material_id: str) -> dict:
    """
    PHASE 2: Polly で教材を音声化

    パラメータ:
      material_id: 音声化する教材ID

    レスポンス:
    ```json
    {
      "materialId": "...",
      "audioUrls": {
        "explanation": "s3://...",
        "step_1": "s3://...",
      },
      "audioFormat": "mp3",
      "generatedAt": "2026-02-28T..."
    }
    ```
    """
    global _polly_client, _enhanced_cache

    # 拡張教材を探す
    if material_id not in _enhanced_cache:
        raise HTTPException(
            status_code=404,
            detail="拡張教材が見つかりません。先に /enhance エンドポイントを実行してください。",
        )

    enhanced_material = _enhanced_cache[material_id]

    try:
        # Polly クライアントを初期化
        if _polly_client is None:
            _polly_client = PollyIntegration()

        # 音声を生成
        logger.info(f"🔄 Generating audio for material {material_id}...")

        # 拡張教材を dict に変換
        if isinstance(enhanced_material, EnhancedLearningMaterial):
            material_dict = enhanced_material.model_dump(by_alias=True)
        else:
            material_dict = enhanced_material

        audio_files = _polly_client.generate_material_audio(material_dict)

        if not audio_files:
            raise Exception("No audio files generated")

        # キャッシュに保存
        _audio_cache[material_id] = audio_files

        # S3 URL をモック（実装時は実際に S3 にアップロード）
        audio_urls = {
            name: f"s3://learning-materials/{material_id}/{name}.mp3"
            for name in audio_files.keys()
        }

        logger.info(f"✅ Generated audio for {len(audio_files)} items")

        return {
            "material_id": material_id,
            "audio_urls": audio_urls,
            "audio_format": "mp3",
            "generated_at": (
                enhanced_material.enhancement_timestamp
                if hasattr(enhanced_material, "enhancement_timestamp")
                else enhanced_material.get("enhancement_timestamp")
                if isinstance(enhanced_material, dict)
                else None
            ),
        }

    except Exception as e:
        logger.error(f"❌ Audio generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"音声生成エラー: {str(e)}")


@router.get("/users/{user_id}/recommendations")
async def get_user_recommendations(user_id: str, num_results: int = 5) -> dict:
    """
    PHASE 2: Personalize でユーザー向けの推薦を取得

    パラメータ:
      user_id: ユーザーID
      num_results: 推薦数（デフォルト: 5）

    レスポンス:
    ```json
    {
      "userId": "...",
      "recommendations": [
        {"materialId": "...", "score": 0.95},
        ...
      ],
      "learningProfile": {
        "preferredDifficulty": "intermediate",
        "preferredConcepts": ["積分", ...],
        "learningSpeed": "normal"
      }
    }
    ```
    """
    global _personalize_client

    try:
        # Personalize クライアントを初期化
        if _personalize_client is None:
            _personalize_client = PersonalizeIntegration()

        # ユーザーの学習パターンを分析（簡略版: キャッシュから完了教材を取得）
        completed_materials = [
            material.model_dump(by_alias=True) for material in _material_cache.values()
        ]

        learning_analysis = _personalize_client.analyze_learning_pattern(
            user_id, completed_materials
        )

        # ユーザーの推薦を取得
        context = {
            "preferred_difficulty": learning_analysis.get("preferred_difficulty"),
            "completed_count": learning_analysis.get("materials_completed"),
        }

        recommendations = _personalize_client.get_recommendations(
            user_id=user_id,
            campaign_arn="arn:aws:personalize:us-east-1:account:campaign/learning-recommendations",
            num_results=num_results,
            context=context,
        )

        logger.info(f"✅ Got recommendations for user {user_id}")

        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "learning_profile": {
                "preferred_difficulty": learning_analysis.get("preferred_difficulty"),
                "preferred_concepts": learning_analysis.get("preferred_concepts"),
                "learning_speed": learning_analysis.get("learning_speed"),
                "materials_completed": learning_analysis.get("materials_completed"),
            },
        }

    except Exception as e:
        logger.error(f"❌ Recommendation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"推薦生成エラー: {str(e)}")


@router.post("/materials/{material_id}/enhance/full")
async def enhance_material_fully(material_id: str) -> EnhancedLearningMaterial:
    """
    PHASE 2: 教材を完全に拡張（Bedrock + Polly + Personalize）

    工程:
    1. Bedrock で詳細解説を生成
    2. Polly で音声を生成
    3. Personalize で推薦情報を追加

    パラメータ:
      material_id: 拡張する教材ID

    レスポンス: EnhancedLearningMaterial
    """
    global _enhanced_cache

    # Step 1: Bedrock で拡張
    enhanced = await enhance_material_with_bedrock(material_id)

    # Step 2: キャッシュに保存
    _enhanced_cache[material_id] = enhanced

    # Step 3: Polly で音声化（オプション）
    try:
        await generate_material_audio(material_id)
        audio_generated = True
    except Exception as e:
        logger.warning(f"⚠️ Audio generation skipped: {e}")
        audio_generated = False

    # Step 4: 推薦データを取得（オプション）
    personalization_score = 0.5
    try:
        if _personalize_client is None:
            _personalize_client = PersonalizeIntegration()

        analysis = _personalize_client.analyze_learning_pattern(
            user_id="system",
            completed_materials=[enhanced.base_material.model_dump(by_alias=True)],
        )
        personalization_score = analysis.get("score", 0.5)
    except Exception as e:
        logger.warning(f"⚠️ Personalization skipped: {e}")

    # 最終的な拡張教材を返す
    enhanced.is_fully_enhanced = True
    enhanced.audio_urls = (
        {
            k: f"s3://learning-materials/{material_id}/{k}.mp3"
            for k in _audio_cache.get(material_id, {}).keys()
        }
        if audio_generated
        else None
    )
    enhanced.personalization_score = personalization_score

    logger.info(f"✅ Full enhancement complete for {material_id}")
    return enhanced
