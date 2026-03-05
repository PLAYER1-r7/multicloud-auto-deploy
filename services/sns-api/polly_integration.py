"""
AWS Polly Integration Module
音声生成による教材の音声化
"""

import logging
from io import BytesIO

import boto3

logger = logging.getLogger(__name__)


class PollyIntegration:
    """Polly統合クラス - テキスト音声変換"""

    def __init__(self, voice_id: str = "Mizuki", region: str = "us-east-1"):
        """
        Args:
            voice_id: Polly の音声ID（日本語: "Mizuki" または "Takumi"）
            region: AWSリージョン
        """
        self.voice_id = voice_id
        self.region = region
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Pollyクライアントを初期化"""
        try:
            self.client = boto3.client("polly", region_name=self.region)
            logger.info(f"✅ Polly initialized: voice_id={self.voice_id}")
        except Exception as e:
            logger.warning(f"⚠️ Polly not available: {e}")
            self.client = None

    def generate_speech(self, text: str, output_format: str = "mp3") -> BytesIO | None:
        """
        テキストを音声に変換

        Args:
            text: 変換するテキスト
            output_format: "mp3", "ogg_vorbis", "pcm"

        Returns:
            音声ファイルのバイナリデータ
        """
        if not self.client:
            logger.warning("⚠️ Polly client not available")
            return None

        try:
            # テキストを制限（Polly max 3000 characters）
            text = text[: min(len(text), 3000)]

            response = self.client.synthesize_speech(
                Text=text, OutputFormat=output_format, VoiceId=self.voice_id
            )

            # AudioStream を BytesIO に変換
            audio_data = BytesIO(response["AudioStream"].read())
            audio_data.seek(0)

            logger.info(f"✅ Generated speech: {len(text)} chars")
            return audio_data

        except Exception as e:
            logger.error(f"❌ Polly API error: {e}")
            return None

    def generate_material_audio(self, material: dict) -> dict[str, bytes] | None:
        """
        教材全体の音声を生成

        Args:
            material: LearningMaterial dict （または EnhancedLearningMaterial）

        Returns:
            各種の音声データ：{
                "explanation": b'...',
                "step_1": b'...',
                "concept_1": b'...',
            }
        """
        if not self.client:
            return self._generate_mock_audio(material)

        audio_data = {}

        try:
            # 詳細解説の音声化
            detailed_explanation = material.get("detailed_explanation") or material.get(
                "detailedExplanation"
            )
            if detailed_explanation:
                audio = self.generate_speech(detailed_explanation)
                if audio:
                    audio_data["explanation"] = audio.getvalue()
                    logger.info("✅ Generated explanation audio")

            # 各ステップの音声化
            outline = material.get("outline", [])
            for i, step in enumerate(outline[:5]):  # Max 5 steps
                if isinstance(step, dict):
                    brief = step.get("brief", "")
                else:
                    brief = getattr(step, "brief", "")

                if brief:
                    audio = self.generate_speech(brief)
                    if audio:
                        audio_data[f"step_{i + 1}"] = audio.getvalue()

            # キーコンセプトの音声化
            key_concepts = material.get("key_concepts", []) or material.get(
                "keyConcepts", []
            )
            for i, concept in enumerate(key_concepts[:3]):  # Max 3 concepts
                concept_text = f"重要概念：{concept}"
                audio = self.generate_speech(concept_text)
                if audio:
                    audio_data[f"concept_{i + 1}"] = audio.getvalue()

            logger.info(f"✅ Generated {len(audio_data)} audio files")
            return audio_data if audio_data else None

        except Exception as e:
            logger.error(f"❌ Material audio generation failed: {e}")
            return None

    def _generate_mock_audio(self, material: dict) -> dict[str, bytes]:
        """
        モック: 音声データを生成（Polly 不可用時）
        """
        logger.info("ℹ️ Using mock audio generation")

        mock_audio = {}

        # モック音声データ（実際には無音 MP3 の小さなバイナリ）
        # このデモでは、ダミーのバイナリデータを返す
        silent_audio = b"ID3\x04\x00\x00\x00\x00\x00\x00"  # MP3 ヘッダ

        if material.get("detailed_explanation") or material.get("detailedExplanation"):
            mock_audio["explanation"] = silent_audio

        outline = material.get("outline", [])
        for i in range(min(len(outline), 5)):
            mock_audio[f"step_{i + 1}"] = silent_audio

        key_concepts = material.get("key_concepts", []) or material.get(
            "keyConcepts", []
        )
        for i in range(min(len(key_concepts), 3)):
            mock_audio[f"concept_{i + 1}"] = silent_audio

        return mock_audio if mock_audio else None


# ==================== 使用例 ====================

if __name__ == "__main__":
    # テスト用のモック教材
    test_material = {
        "material_id": "test-001",
        "detailed_explanation": "この問題は置換積分の重要な応用例です。",
        "outline": [
            {"step_number": 1, "brief": "最初のステップは置換です"},
            {"step_number": 2, "brief": "次に微分をします"},
        ],
        "key_concepts": ["積分", "置換"],
    }

    # Polly統合をテスト
    polly = PollyIntegration()
    audio_files = polly.generate_material_audio(test_material)

    print("\n✅ Generated Audio Files:")
    if audio_files:
        for name, data in audio_files.items():
            print(f"  - {name}: {len(data)} bytes")
    else:
        print("  (No audio files generated - mock mode)")
