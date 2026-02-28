"""
AWS Bedrock Integration Module
解説を拡張・詳細化するためのBedrockクライアント
"""

import json
import logging
from datetime import datetime

import boto3

logger = logging.getLogger(__name__)


class BedrockIntegration:
    """Bedrock統合クラス - Claude 3 Sonnet を使用"""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        region: str = "us-east-1",
    ):
        """
        Args:
            model_id: BedrockモデルのID
            region: AWSリージョン
        """
        self.model_id = model_id
        self.region = region
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Bedrockクライアントを初期化"""
        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region)
            logger.info(f"✅ Bedrock initialized: {self.model_id}")
        except Exception as e:
            logger.warning(f"⚠️ Bedrock not available: {e}")
            self.client = None

    def generate_detailed_explanation(self, material: dict) -> str | None:
        """
        PHASE 1の教材から詳細な解説を生成

        Args:
            material: LearningMaterial dict

        Returns:
            詳細な説明テキスト
        """
        if not self.client:
            return self._generate_mock_explanation(material)

        try:
            prompt = self._build_explanation_prompt(material)
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-06-01",
                        "max_tokens": 2048,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            response_body = json.loads(response["body"].read())
            explanation = response_body["content"][0]["text"]

            logger.info("✅ Generated explanation for material")
            return explanation

        except Exception as e:
            logger.error(f"❌ Bedrock API error: {e}")
            return self._generate_mock_explanation(material)

    def generate_concept_deepdive(self, material: dict, concept: str) -> str | None:
        """
        特定の概念について深掘り解説を生成

        Args:
            material: LearningMaterial dict
            concept: 概念名（例: "置換積分"）

        Returns:
            深掘り解説テキスト
        """
        if not self.client:
            return self._generate_mock_deepdive(concept)

        try:
            prompt = self._build_deepdive_prompt(material, concept)
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-06-01",
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            response_body = json.loads(response["body"].read())
            deepdive = response_body["content"][0]["text"]

            logger.info(f"✅ Generated deep dive for concept: {concept}")
            return deepdive

        except Exception as e:
            logger.error(f"❌ Bedrock API error: {e}")
            return self._generate_mock_deepdive(concept)

    def analyze_common_mistakes(self, material: dict) -> list[str] | None:
        """
        よくある間違いを詳細分析

        Args:
            material: LearningMaterial dict

        Returns:
            間違い分析のリスト
        """
        if not self.client:
            return self._generate_mock_mistake_analysis(material)

        try:
            prompt = self._build_mistake_analysis_prompt(material)
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-06-01",
                        "max_tokens": 1200,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            response_body = json.loads(response["body"].read())
            analysis_text = response_body["content"][0]["text"]
            analyses = [
                line.strip() for line in analysis_text.split("\n") if line.strip()
            ]

            logger.info("✅ Generated mistake analysis")
            return analyses

        except Exception as e:
            logger.error(f"❌ Bedrock API error: {e}")
            return self._generate_mock_mistake_analysis(material)

    def enhance_full_material(self, material: dict) -> dict:
        """
        教材全体をBedrockで拡張

        Args:
            material: LearningMaterial dict

        Returns:
            拡張された教材dict
        """
        enhanced = material.copy()

        # 詳細解説を生成
        enhanced["detailedExplanation"] = self.generate_detailed_explanation(material)

        # 重要概念の深掘り
        enhanced["conceptDeepDives"] = {}
        for concept in material.get("keyConcepts", []):
            enhanced["conceptDeepDives"][concept] = self.generate_concept_deepdive(
                material, concept
            )

        # 間違い分析
        enhanced["mistakeAnalysis"] = self.analyze_common_mistakes(material)

        # メタデータ
        enhanced["enhancement_timestamp"] = datetime.utcnow().isoformat()
        enhanced["enhancement_model"] = self.model_id
        enhanced["is_enhanced"] = True

        logger.info(f"✅ Material enhancement complete: {material.get('materialId')}")

        return enhanced

    # ==================== プロンプト構築メソッド ====================

    def _build_explanation_prompt(self, material: dict) -> str:
        """詳細解説用プロンプトを構築"""
        problem = material.get("problemText", "")
        outline = material.get("outline", [])
        key_concepts = material.get("keyConcepts", [])

        outline_text = "\n".join(
            [f"{i + 1}. {step.get('brief', '')}" for i, step in enumerate(outline[:5])]
        )

        concepts_text = "、".join(key_concepts) if key_concepts else "（なし）"

        return f"""
以下の数学問題の解答について、学習者向けの詳細な説明を生成してください。
各ステップをわかりやすく説明し、重要な概念や注意点を含めてください。

【問題】
{problem}

【解答ステップ】
{outline_text}

【重要概念】
{concepts_text}

【出力形式】
1. **概要**: 問題のポイント（2-3文）
2. **ステップ解説**: 各ステップの詳細説明（各100-150字）
3. **重要概念**: この問題で学べる数学概念（詳細説明）
4. **参考**: 関連する公式や定理
5. **学習のコツ**: 類似問題に対応するためのヒント

日本語で、中学～高校レベルの学習者が理解できる表現を使用してください。
"""

    def _build_deepdive_prompt(self, material: dict, concept: str) -> str:
        """概念の深掘り用プロンプトを構築"""
        problem = material.get("problemText", "")

        return f"""
以下の数学問題における「{concept}」という概念について、詳しく説明してください。

【問題】
{problem}

【説明内容】
1. **定義**: {concept}の定義を簡潔に説明
2. **背景**: なぜこの概念が必要か
3. **応用**: この問題でどのように使われているか
4. **関連概念**: 関連する他の数学概念
5. **よくある誤解**: 学習者が陥りやすい誤解と対策

詳しく、学習者向けの文体で説明してください。
"""

    def _build_mistake_analysis_prompt(self, material: dict) -> str:
        """間違い分析用プロンプトを構築"""
        problem = material.get("problemText", "")
        steps = material.get("solutionSteps", [])
        common_mistakes = material.get("commonMistakes", [])

        steps_text = "\n".join([f"- {step}" for step in steps[:3]])
        mistakes_text = "\n".join(
            [
                f"- {m.get('mistakeDescription', '')}: {m.get('correction', '')}"
                for m in common_mistakes
            ]
        )

        return f"""
以下の数学問題については、学習者が陥りやすい間違いを分析してください。

【問題】
{problem}

【正しい解法】
{steps_text}

【既知の間違いパターン】
{mistakes_text}

【分析内容】
1. これらの間違いが起きる心理的理由
2. 各間違いを防ぐための具体的な方法
3. 間違いから学べることは何か
4. 類似問題での応用方法

それぞれ1-2文で簡潔に説明してください。
"""

    # ==================== モック実装（Bedrockが不可用時） ====================

    def _generate_mock_explanation(self, material: dict) -> str:
        """モック: 詳細解説を生成"""
        problem = material.get("problemText", "問題なし")
        outline = material.get("outline", [])

        outline_str = "\n".join(
            [
                f"  Step {s.get('stepNumber', i + 1)}: {s.get('brief', '')}"
                for i, s in enumerate(outline[:5])
            ]
        )

        return f"""
【詳細解説】

**概要**
この問題は {material.get("keyConcepts", ["数学"])[0]} 関連の計算問題です。
正確な手順を踏むことが重要です。

**ステップ解説**
{outline_str}

**重要ポイント**
- 各ステップで計算を確認すること
- {material.get("commonMistakes", [{}])[0].get("mistakeDescription", "符号ミス")} に注意
- 答えは定義を満たすか確認する

**参考**
関連する基本公式や定理を復習することをお勧めします。
"""

    def _generate_mock_deepdive(self, concept: str) -> str:
        """モック: 概念の深掘り"""
        return f"""
【{concept}の深掘り解説】

**定義**
{concept}は数学における重要な概念です。

**背景**
この概念は多くの問題で使用されます。

**応用**
この問題でも{concept}の理解が鍵となります。

**関連概念**
{concept}と関連する他の概念があります。

**よくある誤解**
{concept}について、学習者が陥りやすい誤解があります。
"""

    def _generate_mock_mistake_analysis(self, material: dict) -> list[str]:
        """モック: 間違い分析"""
        mistakes = material.get("commonMistakes", [])

        analyses = []
        for mistake in mistakes:
            desc = mistake.get("mistakeDescription", "計算ミス")
            analyses.append(
                f"❌ {desc}: {mistake.get('prevention_tip', '丁寧に計算する')}"
            )

        if not analyses:
            analyses = [
                "❌ 計算ミス: 各ステップを丁寧に確認する",
                "❌ 理解不足: 概念を復習する",
            ]

        return analyses


# ==================== 使用例 ====================

if __name__ == "__main__":
    # テスト用のモック教材
    test_material = {
        "materialId": "test-001",
        "problemText": "∫ x/√(x²+1) dx を求めよ",
        "outline": [
            {"stepNumber": 1, "brief": "u = x²+1 と置換する"},
            {"stepNumber": 2, "brief": "du/dx = 2x より dx = du/(2x)"},
            {"stepNumber": 3, "brief": "置換積分を実行"},
        ],
        "keyConcepts": ["置換積分", "積分計算"],
        "commonMistakes": [
            {
                "mistakeDescription": "積分定数を忘れる",
                "correction": "∫f(x)dx = F(x) + C",
                "prevention_tip": "計算の最後に必ず +C を記入",
            }
        ],
    }

    # Bedrock統合をテスト
    bedrock = BedrockIntegration()
    enhanced = bedrock.enhance_full_material(test_material)

    print("\n✅ Enhanced Material:")
    print(f"  - Material ID: {enhanced.get('materialId')}")
    print(f"  - Has detailed explanation: {'detailedExplanation' in enhanced}")
    print(f"  - Has concept deep dives: {bool(enhanced.get('conceptDeepDives'))}")
    print(f"  - Has mistake analysis: {bool(enhanced.get('mistakeAnalysis'))}")
    print(f"  - Enhancement timestamp: {enhanced.get('enhancement_timestamp')}")
