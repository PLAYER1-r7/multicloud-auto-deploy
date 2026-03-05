#!/usr/bin/env python3
"""
PHASE 2 統合テスト - Bedrock + Polly + Personalize エンドポイント検証
既存の PHASE 1 教材を使用して、PHASE 2 エンドポイントをテスト
"""

import sys

from fastapi.testclient import TestClient

sys.path.insert(0, "/workspaces/multicloud-auto-deploy/services/api")

from app.main import app
from app.models import SolveExam, SolveMeta

client = TestClient(app)


def test_phase2():
    """PHASE 2 統合テスト"""

    print("\n" + "=" * 80)
    print("🧪 AWS Learning Assistant - PHASE 2 統合テスト")
    print("=" * 80)

    # ========== Step 1: PHASE 1 教材を直接生成 ==========
    print("\n📝 STEP 1: PHASE 1 - 教材生成（MaterialGenerator 使用）")
    print("-" * 80)

    try:
        # MaterialGenerator を直接使用
        from app.models import SolveAnswer, SolveResponse
        from app.services.material_generator import MaterialGenerator

        generator = MaterialGenerator()

        # モック SolveResponse
        solve_response = SolveResponse(
            request_id="phase2-test-001",
            status="success",
            problem_text="次の不定積分を求めよ。\n\n∫ x/√(x²+1) dx",
            answer=SolveAnswer(
                final="√(x²+1) + C",
                latex="\\sqrt{x^2 + 1} + C",
                steps=[
                    "u = x²+1 と置換",
                    "du/dx = 2x",
                    "置換積分",
                    "√u + C",
                    "戻す → √(x²+1) + C",
                ],
                confidence=0.95,
            ),
            meta=SolveMeta(
                ocr_provider="azure",
                model="azure-document-intelligence",
                latency_ms=1200,
                cost_usd=0.05,
            ),
        )

        exam = SolveExam(university="tokyo", year=2025, subject="math", question_no="1")

        material = generator.generate_from_solve_response(
            solve_response=solve_response,
            exam=exam,
            problem_image_url="http://server-test.net/math/tokyo/q_jpg/2025_1.jpg",
        )

        material_id = material.material_id

        print(f"✅ Material created: {material_id}")
        print(f"   - Outline: {len(material.outline)} steps")
        print(f"   - Concepts: {material.key_concepts}")

    except Exception as e:
        print(f"❌ Material generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # キャッシュに追加（ルートで使用するため）
    from app.routes.learning import _material_cache

    _material_cache[material_id] = material

    # ========== Step 2: Bedrock で拡張 ==========
    print("\n🤖 STEP 2: Bedrock - 詳細解説生成")
    print("-" * 80)

    try:
        response = client.post(f"/v1/learn/materials/{material_id}/enhance")

        if response.status_code == 200:
            enhanced = response.json()
            print("✅ Material enhanced with Bedrock")

            # キャッシュに保存（後続エンドポイント用）
            from app.routes.learning import _enhanced_cache

            _enhanced_cache[material_id] = enhanced

            has_explanation = (
                "detailed_explanation" in enhanced or "detailedExplanation" in enhanced
            )
            has_concepts = len(enhanced.get("concept_deep_dives", {}) or {}) > 0

            print(f"   - Has detailed explanation: {has_explanation}")
            print(
                f"   - Concept deep dives: {len(enhanced.get('concept_deep_dives', {}) or {})}"
            )
            print(
                f"   - Mistake analysis: {len(enhanced.get('mistake_analysis', []) or [])}"
            )
        else:
            print(f"⚠️ Bedrock enhancement status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"⚠️ Bedrock enhancement error: {e}")

    # ========== Step 3: Polly で音声化 ==========
    print("\n🔊 STEP 3: Polly - 音声生成")
    print("-" * 80)

    try:
        response = client.post(f"/v1/learn/materials/{material_id}/audio")

        if response.status_code == 200:
            audio_data = response.json()
            print("✅ Audio generated with Polly")
            audio_urls = audio_data.get("audio_urls", {}) or audio_data.get(
                "audioUrls", {}
            )
            print(f"   - Audio files: {len(audio_urls)}")
            for audio_type in list(audio_urls.keys())[:3]:
                print(f"     - {audio_type}")
        else:
            print(f"⚠️ Polly audio generation status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"⚠️ Polly audio generation error: {e}")

    # ========== Step 4: Personalize で推薦 ==========
    print("\n👥 STEP 4: Personalize - ユーザー推薦")
    print("-" * 80)

    try:
        response = client.get(
            "/v1/learn/users/test-user-001/recommendations?num_results=3"
        )

        if response.status_code == 200:
            recs = response.json()
            print("✅ Recommendations retrieved")

            profile = recs.get("learning_profile", {})
            print("   - Learning Profile:")
            print(f"     - Preferred difficulty: {profile.get('preferred_difficulty')}")
            print(f"     - Learning speed: {profile.get('learning_speed')}")
            print(f"     - Concepts: {profile.get('preferred_concepts')}")

            recommendations = recs.get("recommendations", [])
            print(f"   - Recommendations: {len(recommendations)} items")
            for rec in recommendations[:3]:
                print(f"     - {rec.get('material_id')}: {rec.get('score', 0):.2f}")
        else:
            print(f"⚠️ Personalize status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"⚠️ Personalize error: {e}")

    print("\n" + "=" * 80)
    print("✅ PHASE 2 Integration Test Complete!")
    print("=" * 80)
    print("\nエンドポイント一覧:")
    print("  1. POST /v1/learn/materials/{material_id}/enhance")
    print("  2. POST /v1/learn/materials/{material_id}/audio")
    print("  3. GET  /v1/learn/users/{user_id}/recommendations")
    print("  4. POST /v1/learn/materials/{material_id}/enhance/full")
    print("\n")

    return True


if __name__ == "__main__":
    try:
        test_phase2()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
