#!/usr/bin/env python3
"""
教材生成テストスクリプト

テストケース:
- 問題画像: http://server-test.net/math/tokyo/q_jpg/2025_1.jpg
- 解答PDF: https://www5a.biglobe.ne.jp/~t-konno/math/tokyo/2025_tokyo_rz_1.pdf
"""

import asyncio
import json
import sys
from pathlib import Path

# プロジェクトrootをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.models import SolveExam
from app.services.azure_math_solver import AzureMathSolver
from app.services.material_generator import MaterialGenerator


async def test_material_generation():
    """教材生成を実行してテストするメイン関数"""

    print("=" * 80)
    print("🧪 AWS Learning Material Generation Test")
    print("=" * 80)

    # テストケース
    problem_image_url = "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg"
    reference_pdf_url = (
        "https://www5a.biglobe.ne.jp/~t-konno/math/tokyo/2025_tokyo_rz_1.pdf"
    )

    exam_metadata = SolveExam(
        university="tokyo", year=2025, subject="math", question_no="1"
    )

    print("\n📋 Test Parameters:")
    print(f"   Problem Image: {problem_image_url}")
    print(f"   Reference PDF: {reference_pdf_url}")
    print(
        f"   Exam: {exam_metadata.university} {exam_metadata.year} Q{exam_metadata.question_no}"
    )

    try:
        # ============================================================
        # STEP 1: Azure で解答を取得
        # ============================================================
        print("\n⏳ STEP 1: Retrieving solution from Azure...")

        solver = AzureMathSolver()

        # SolveRequest を構築
        from app.models import SolveInput, SolveOptions, SolveRequest

        request = SolveRequest(
            input=SolveInput(image_url=problem_image_url, source="url"),
            exam=exam_metadata,
            options=SolveOptions(
                mode="accurate", need_steps=True, need_latex=True, max_tokens=4000
            ),
        )

        # Azure で問題を解く
        solve_response = solver.solve(request)

        print("✅ Solution retrieved from Azure")
        print(f"   OCR Provider: {solve_response.meta.ocr_provider}")
        print(f"   Problem Text: {solve_response.problem_text[:80]}...")
        print(f"   Final Answer: {solve_response.answer.final[:60]}...")
        print(f"   Solution Steps: {len(solve_response.answer.steps)} steps")
        print(f"   Confidence: {solve_response.answer.confidence:.2%}")

        # ============================================================
        # STEP 2: MaterialGenerator で教材を生成
        # ============================================================
        print("\n⏳ STEP 2: Generating learning material...")

        generator = MaterialGenerator()

        material = generator.generate_from_solve_response(
            solve_response=solve_response,
            exam=exam_metadata,
            problem_image_url=problem_image_url,
        )

        print("✅ Learning material generated")
        print(f"   Material ID: {material.material_id}")
        print(f"   Difficulty: {material.difficulty_level}")
        print(f"   Key Concepts: {', '.join(material.key_concepts)}")
        print(f"   Learning Objectives: {len(material.learning_objectives)} items")
        print(f"   Quiz Questions: {len(material.quiz_questions)} items")
        print(f"   Common Mistakes: {len(material.common_mistakes)} items")
        print(f"   Reference Problems: {len(material.reference_problems)} items")

        # ============================================================
        # STEP 3: 結果を JSON で保存・表示
        # ============================================================
        print("\n⏳ STEP 3: Saving results...")

        # JSON出力ディレクトリ
        output_dir = Path(__file__).parent.parent / "test_results"
        output_dir.mkdir(exist_ok=True)

        # educationMaterialをJSON形式で保存
        material_json = material.model_dump(by_alias=True, exclude_none=True)

        output_file = output_dir / "learning_material_test_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(material_json, f, ensure_ascii=False, indent=2)

        print(f"✅ Results saved to: {output_file}")

        # ============================================================
        # STEP 4: 詳細な構造を表示
        # ============================================================
        print("\n" + "=" * 80)
        print("📄 Generated Material Structure")
        print("=" * 80)

        print("\n### Problem & Solution")
        print(f"Problem: {material.problem_text[:100]}...")
        print(f"Final Answer: {material.solution_final[:100]}...")

        if material.outline:
            print(f"\n### Learning Outline ({len(material.outline)} steps)")
            for step in material.outline[:3]:  # 最初の3ステップを表示
                print(f"  Step {step.step_number}: {step.brief}")
                if step.key_formula:
                    print(f"    Formula: {step.key_formula}")

        if material.key_concepts:
            print("\n### Key Concepts")
            for concept in material.key_concepts[:5]:
                print(f"  • {concept}")

        if material.learning_objectives:
            print("\n### Learning Objectives")
            for i, obj in enumerate(material.learning_objectives, 1):
                print(f"  {i}. {obj}")

        if material.common_mistakes:
            print("\n### Common Mistakes")
            for mistake in material.common_mistakes[:2]:
                print(f"  ❌ {mistake.mistake_description}")
                print(f"     Why: {mistake.why_wrong}")
                print(f"     Fix: {mistake.correction}")

        if material.quiz_questions:
            print(f"\n### Quiz Questions ({len(material.quiz_questions)})")
            for q in material.quiz_questions[:2]:
                print(f"  Q: {q.question_text[:60]}...")
                print(f"     Type: {q.question_type}")

        if material.reference_problems:
            print("\n### Reference Problems")
            for ref in material.reference_problems[:3]:
                print(f"  • {ref.university} {ref.year} Q{ref.question_no}")
                print(f"    Similarity: {ref.similarity_score:.2%}")

        print("\n" + "=" * 80)
        print("✅ Test completed successfully!")
        print(f"💾 Full results: {output_file}")
        print("=" * 80)

        return True

    except Exception as e:
        print("\n❌ Error during test:")
        print(f"   {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Azure 環境変数確認
    if (
        not settings.azure_document_intelligence_endpoint
        or not settings.azure_document_intelligence_key
    ):
        print("❌ Azure Document Intelligence not configured")
        print(
            "   Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY"
        )
        sys.exit(1)

    print(f"✅ Using provider: {settings.cloud_provider}")

    # 非同期実行
    success = asyncio.run(test_material_generation())

    sys.exit(0 if success else 1)
