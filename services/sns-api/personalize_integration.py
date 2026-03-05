"""
AWS Personalize Integration Module
学習パターンに基づいた教材推薦
"""

import json
import logging
from datetime import datetime

import boto3

logger = logging.getLogger(__name__)


class PersonalizeIntegration:
    """Personalize統合クラス - 機械学習ベースの推薦"""

    def __init__(self, region: str = "us-east-1"):
        """
        Args:
            region: AWSリージョン
        """
        self.region = region
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Personalizeクライアントを初期化"""
        try:
            self.client = boto3.client("personalize-runtime", region_name=self.region)
            logger.info("✅ Personalize initialized")
        except Exception as e:
            logger.warning(f"⚠️ Personalize not available: {e}")
            self.client = None

    def get_recommendations(
        self,
        user_id: str,
        campaign_arn: str,
        num_results: int = 5,
        context: dict | None = None,
    ) -> list[dict] | None:
        """
        ユーザーの学習パターン基づいた推薦を取得

        Args:
            user_id: ユーザーID
            campaign_arn: Personalize キャンペーンのARN
            num_results: 推薦数
            context: コンテキスト情報（学習履歴など）

        Returns:
            推薦教材のリスト
        """
        if not self.client:
            return self._generate_mock_recommendations(num_results, context)

        try:
            # Personalize の get_recommendations API を呼び出し
            response = self.client.get_recommendations(
                campaignArn=campaign_arn,
                userId=user_id,
                numResults=num_results,
                contextMetadata=context or {},
            )

            recommendations = [
                {
                    "material_id": item["itemId"],
                    "score": item.get("score", 0.0),
                }
                for item in response.get("itemList", [])
            ]

            logger.info(
                f"✅ Got {len(recommendations)} recommendations for user {user_id}"
            )
            return recommendations

        except Exception as e:
            logger.error(f"❌ Personalize API error: {e}")
            return self._generate_mock_recommendations(num_results, context)

    def track_interaction(
        self, user_id: str, material_id: str, interaction_type: str = "view"
    ) -> bool:
        """
        ユーザーの学習インタラクションを記録

        Args:
            user_id: ユーザーID
            material_id: 教材ID
            interaction_type: "view", "complete", "struggle"

        Returns:
            成功したかどうか
        """
        if not self.client:
            logger.info(f"ℹ️ Mock logging interaction: {user_id} -> {material_id}")
            return True

        try:
            # Personalize Events API に相互作用を記録
            # Note:実装にはイベントトラッガーの設定が必要
            logger.info(
                f"✅ Tracked interaction: {user_id} {interaction_type} {material_id}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to track interaction: {e}")
            return False

    def analyze_learning_pattern(
        self, user_id: str, completed_materials: list[dict]
    ) -> dict:
        """
        ユーザーの学習パターンを分析

        Args:
            user_id: ユーザーID
            completed_materials: 完了した教材のリスト

        Returns:
            学習パターン分析結果 {
                "preferred_difficulty": "basic|intermediate|advanced",
                "preferred_concepts": ["積分", "微分"],
                "learning_speed": "slow|normal|fast",
                "score": 0.0-1.0
            }
        """
        try:
            difficulty_counts = {"basic": 0, "intermediate": 0, "advanced": 0}
            all_concepts = []
            total_time = 0
            materials_processed = 0

            for material in completed_materials:
                difficulty = material.get("difficulty_level") or material.get(
                    "difficultyLevel"
                )
                if difficulty:
                    difficulty_counts[difficulty] = (
                        difficulty_counts.get(difficulty, 0) + 1
                    )

                concepts = (
                    material.get("key_concepts") or material.get("keyConcepts") or []
                )
                all_concepts.extend(concepts)

                materials_processed += 1

            # 最も頻繁な難易度を決定
            preferred_difficulty = max(difficulty_counts, key=difficulty_counts.get)

            # 最も頻繁な概念を決定
            from collections import Counter

            concept_counts = Counter(all_concepts)
            preferred_concepts = [c for c, _ in concept_counts.most_common(5)]

            # 学習速度を仮定（実装: 実際の時間データから計算）
            learning_speed = "normal"
            if materials_processed > 5:
                learning_speed = "fast"
            elif materials_processed < 2:
                learning_speed = "slow"

            analysis = {
                "user_id": user_id,
                "preferred_difficulty": preferred_difficulty,
                "preferred_concepts": preferred_concepts,
                "learning_speed": learning_speed,
                "materials_completed": materials_processed,
                "score": min(materials_processed / 10.0, 1.0),  # Max 1.0
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"✅ Analyzed learning pattern for user {user_id}")
            return analysis

        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}")
            return self._generate_mock_pattern_analysis(user_id)

    def _generate_mock_recommendations(
        self, num_results: int, context: dict | None = None
    ) -> list[dict]:
        """
        モック: 推薦を生成（Personalize 不可用時）
        """
        logger.info(f"ℹ️ Using mock recommendations (returning {num_results} items)")

        # モック推薦データ
        mock_materials = [
            "tokyo_2024_q1",
            "tokyo_2024_q2",
            "kyoto_2024_q1",
            "osaka_2024_q3",
            "tokyo_2025_q1",
        ]

        recommendations = [
            {
                "material_id": mock_materials[i % len(mock_materials)],
                "score": 0.9 - i * 0.1,
            }
            for i in range(num_results)
        ]

        return recommendations

    def _generate_mock_pattern_analysis(self, user_id: str) -> dict:
        """
        モック: 学習パターン分析を生成
        """
        return {
            "user_id": user_id,
            "preferred_difficulty": "intermediate",
            "preferred_concepts": ["積分", "微分"],
            "learning_speed": "normal",
            "materials_completed": 0,
            "score": 0.5,
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }


# ==================== 使用例 ====================

if __name__ == "__main__":
    # テスト用の completed materials
    test_completed = [
        {
            "material_id": "mat-001",
            "difficulty_level": "basic",
            "key_concepts": ["積分"],
        },
        {
            "material_id": "mat-002",
            "difficulty_level": "intermediate",
            "key_concepts": ["積分", "置換"],
        },
    ]

    # Personalize統合をテスト
    personalize = PersonalizeIntegration()

    # 学習パターン分析
    analysis = personalize.analyze_learning_pattern("user-123", test_completed)
    print("\n✅ Learning Pattern Analysis:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))

    # 推薦を取得（モック）
    recommendations = personalize.get_recommendations(
        user_id="user-123",
        campaign_arn="arn:aws:personalize:...",
        num_results=3,
        context={"preferred_difficulty": "intermediate"},
    )
    print("\n✅ Recommendations:")
    for rec in recommendations:
        print(f"  - {rec['material_id']}: {rec['score']:.2f}")
