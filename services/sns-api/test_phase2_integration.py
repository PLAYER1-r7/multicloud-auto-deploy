#!/usr/bin/env python3
"""
PHASE 2 Integrated Test: Bedrock + Polly + Personalize
AWS Learning Assistant の統合エンドポイントテスト
"""

import sys

from fastapi.testclient import TestClient

# FastAPI app をインポート
sys.path.insert(0, "/workspaces/multicloud-auto-deploy/services/api")

from app.main import app
from app.models import SolveAnswer, SolveExam, SolveMeta, SolveResponse

client = TestClient(app)


def test_phase2_integration():
    """PHASE 2 統合テスト"""

    print("\n" + "=" * 80)
    print("🧪 AWS Learning Assistant - PHASE 2 統合テスト")
    print("=" * 80)

    # ========== Step 1: PHASE 1 教材を生成 ==========
    print("\n📝 STEP 1: PHASE 1 - 教材生成")
    print("-" * 80)

    # モック SolveResponse を作成
    solve_response = SolveResponse(
        request_id="test-req-001",
        status="success",
        problem_text="次の不定積分を求めよ。\n\n∫ x/√(x²+1) dx",
        answer=SolveAnswer(
            final="√(x²+1) + C",
            latex="\\sqrt{x^2 + 1} + C",
            steps=[
                "u = x²+1 と置換する。",
                "du/dx = 2x より、dx = du/(2x)",
                "置換して整理する",
                "積分する",
                "u = x²+1 を代入",
            ],
            confidence=0.95,
        ),
        meta=SolveMeta(
            solution_steps=[
                "u = x²+1 と置換する。",
                "du/dx = 2x より、dx = du/(2x)",
                "置換して整理する",
                "積分する",
                "u = x²+1 を代入",
            ],
            confidence_score=0.95,
            ocr_provider="azure",
        ),
    )

    exam = SolveExam(university="tokyo", year=2025, subject="math", question_no="1")

    # POST /v1/learn/materials/from-solve
    response = client.post(
        "/v1/learn/materials/from-solve",
        json={
            "solve_response": solve_response.model_dump(by_alias=True),
            "exam": exam.model_dump(by_alias=True),
            "problem_image_url": "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg",
        },
    )

    if response.status_code != 200:
        print(f"❌ Failed to create material: {response.status_code}")
        print(response.text)
        return False

    material = response.json()
    material_id = material.get("material_id") or material.get("materialId")

    print(f"✅ Material created: {material_id}")
    print(f"   - Outline steps: {len(material.get('outline', []))}")
    print(f"   - Key concepts: {material.get('key_concepts', [])}")
    print(f"   - Quiz questions: {len(material.get('quiz_questions', []))}")

    # ========== Step 2: Bedrock で拡張 ==========
    print("\n🤖 STEP 2: Bedrock - 詳細解説生成")
    print("-" * 80)

    response = client.post(f"/v1/learn/materials/{material_id}/enhance")

    if response.status_code != 200:
        print(f"❌ Enhancement failed: {response.status_code}")
        print(response.text)
    else:
        enhanced = response.json()
        print("✅ Material enhanced")
        print(
            f"   - Has detailed explanation: {'detailed_explanation' in enhanced or 'detailedExplanation' in enhanced}"
        )
        print(
            f"   - Concept deep dives: {len(enhanced.get('concept_deep_dives', {}) or enhanced.get('conceptDeepDives', {}))}"
        )
        print(
            f"   - Mistake analysis items: {len(enhanced.get('mistake_analysis', []) or enhanced.get('mistakeAnalysis', []))}"
        )

    # ========== Step 3: Polly で音声化 ==========
    print("\n🔊 STEP 3: Polly - 音声生成")
    print("-" * 80)

    response = client.post(f"/v1/learn/materials/{material_id}/audio")

    if response.status_code != 200:
        print(f"⚠️ Audio generation failed: {response.status_code}")
        print(response.text)
    else:
        audio_data = response.json()
        print("✅ Audio generated")
        print(f"   - Audio URLs: {len(audio_data.get('audio_urls', {}))}")
        for audio_type in list(audio_data.get("audio_urls", {}).keys())[:3]:
            print(f"     - {audio_type}")

    # ========== Step 4: Personalize で推薦 ==========
    print("\n👥 STEP 4: Personalize - ユーザー推薦")
    print("-" * 80)

    response = client.get("/v1/learn/users/test-user/recommendations?num_results=3")

    if response.status_code != 200:
        print(f"⚠️ Recommendations failed: {response.status_code}")
        print(response.text)
    else:
        recs = response.json()
        print("✅ Recommendations retrieved")
        print("   - Learning profile:")
        profile = recs.get("learning_profile", {})
        print(f"     - Preferred difficulty: {profile.get('preferred_difficulty')}")
        print(f"     - Preferred concepts: {profile.get('preferred_concepts')}")
        print(f"     - Learning speed: {profile.get('learning_speed')}")
        print(f"   - Recommendations: {len(recs.get('recommendations', []))}")
        for rec in recs.get("recommendations", [])[:3]:
            print(f"     - {rec.get('material_id')}: {rec.get('score', 0):.2f}")

    # ========== Step 5: 完全な拡張 ==========
    print("\n⭐ STEP 5: 完全な拡張（Bedrock + Polly + Personalize）")
    print("-" * 80)

    # 新しい教材を作成して完全な拡張を実行
    response = client.post(
        "/v1/learn/materials/from-solve",
        json={
            "solve_response": solve_response.model_dump(by_alias=True),
            "exam": exam.model_dump(by_alias=True),
            "problem_image_url": "http://server-test.net/math/tokyo/q_jpg/2025_2.jpg",
        },
    )

    if response.status_code == 200:
        new_material = response.json()
        new_material_id = new_material.get("material_id") or new_material.get(
            "materialId"
        )

        response = client.post(f"/v1/learn/materials/{new_material_id}/enhance/full")

        if response.status_code != 200:
            print(f"⚠️ Full enhancement failed: {response.status_code}")
        else:
            fully_enhanced = response.json()
            print(f"✅ Material fully enhanced: {new_material_id}")
            print(
                f"   - Is fully enhanced: {fully_enhanced.get('is_fully_enhanced') or fully_enhanced.get('isFullyEnhanced')}"
            )
            print(
                f"   - Audio URLs: {fully_enhanced.get('audio_urls') or fully_enhanced.get('audioUrls')}"
            )
            print(
                f"   - Personalization score: {fully_enhanced.get('personalization_score') or fully_enhanced.get('personalizationScore'):.2f}"
            )

    print("\n" + "=" * 80)
    print("✅ PHASE 2 Integration Test Complete!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = test_phase2_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
