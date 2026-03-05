#!/usr/bin/env python3
"""
教材生成デモ - モックデータを使用したテスト
(Azure設定なしでもテスト可能)

このスクリプトは、実際のAzure解答の代わりにモックデータを使用して、
MaterialGeneratorの動作を示します。
"""

import json
import sys
from pathlib import Path

# プロジェクトrootをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import (
    PlotData,
    SolveAnswer,
    SolveExam,
    SolveMeta,
    SolveResponse,
)
from app.services.material_generator import MaterialGenerator


def create_mock_solve_response() -> SolveResponse:
    """
    実際のAzure解答の代わりにモックデータを生成

    テストケース: 東大2025年 数学第1問の例
    """

    problem_text = """
    次の不定積分を求めよ。

    $\\int \\frac{x}{\\sqrt{x^2 + 1}} dx$
    """

    steps = [
        "$u = x^2 + 1$ と置換する。",
        "$\\frac{du}{dx} = 2x$ より、$dx = \\frac{du}{2x}$",
        "与式は $\\int \\frac{x}{\\sqrt{u}} \\cdot \\frac{du}{2x} = \\int \\frac{1}{2\\sqrt{u}} du$",
        "$= \\frac{1}{2} \\cdot 2\\sqrt{u} + C = \\sqrt{u} + C$",
        "$u = x^2 + 1$ を代入すると、$\\sqrt{x^2 + 1} + C$",
    ]

    answer = SolveAnswer(
        final="$\\sqrt{x^2 + 1} + C$",
        latex="\\sqrt{x^2 + 1} + C",
        steps=steps,
        diagram_guide=None,
        plot_data=PlotData(need_plot=False),
        confidence=0.95,
    )

    meta = SolveMeta(
        ocr_provider="azure",
        ocr_source="azure_di_merged",
        ocr_score=0.98,
        ocr_candidates=1,
        model="gpt-4o",
        latency_ms=3200,
        cost_usd=0.0045,
    )

    return SolveResponse(
        request_id="test-req-001",
        status="ok",
        problem_text=problem_text,
        answer=answer,
        meta=meta,
    )


def test_material_generation():
    """教材生成をテスト"""

    print("=" * 80)
    print("🧪 Material Generation Demo (Mock Data)")
    print("=" * 80)

    # ============================================================
    # STEP 1: モック SolveResponse を生成
    # ============================================================
    print("\n⏳ STEP 1: Creating mock SolveResponse...")

    solve_response = create_mock_solve_response()

    exam_metadata = SolveExam(
        university="tokyo", year=2025, subject="math", question_no="1"
    )

    problem_image_url = "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg"

    print("✅ Mock data created")
    print(f"   Problem: {solve_response.problem_text[:60].strip()}...")
    print(f"   Answer: {solve_response.answer.final}")
    print(f"   Steps: {len(solve_response.answer.steps)}")
    print(f"   Confidence: {solve_response.answer.confidence:.0%}")

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

    print("✅ Material generated successfully")
    print(f"   Material ID: {material.material_id}")
    print(f"   Created: {material.created_at}")
    print(f"   Difficulty: {material.difficulty_level}")
    print(f"   OCR Provider: {material.ocr_provider}")

    # ============================================================
    # STEP 3: 結果を JSON で保存
    # ============================================================
    print("\n⏳ STEP 3: Saving results to JSON...")

    output_dir = Path(__file__).parent / "test_results"
    output_dir.mkdir(exist_ok=True)

    # JSON出力
    material_json = material.model_dump(by_alias=True, exclude_none=True)

    output_file = output_dir / "learning_material_demo.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(material_json, f, ensure_ascii=False, indent=2)

    print(f"✅ Results saved: {output_file}")

    # ============================================================
    # STEP 4: 詳細構造を表示
    # ============================================================
    print("\n" + "=" * 80)
    print("📄 Generated Learning Material Structure")
    print("=" * 80)

    print("\n### 問題と解答")
    print(f"問題: {material.problem_text.strip()[:100]}")
    print(f"最終答: {material.solution_final}")
    print(f"信頼度: {material.solution_confidence:.0%}")

    if material.outline:
        print(f"\n### 学習アウトライン ({len(material.outline)} steps)")
        for step in material.outline:
            print(f"  Step {step.step_number}: {step.brief}")
            if step.key_formula:
                print(f"             → {step.key_formula}")

    if material.key_concepts:
        print(f"\n### 重要概念 ({len(material.key_concepts)} items)")
        for concept in material.key_concepts:
            print(f"  • {concept}")

    if material.learning_objectives:
        print(f"\n### 学習目標 ({len(material.learning_objectives)} items)")
        for i, obj in enumerate(material.learning_objectives, 1):
            print(f"  {i}. {obj}")

    if material.common_mistakes:
        print(f"\n### よくある間違い ({len(material.common_mistakes)} items)")
        for i, mistake in enumerate(material.common_mistakes, 1):
            print(f"  {i}. ❌ {mistake.mistake_description}")
            print(f"     理由: {mistake.why_wrong}")
            print(f"     対策: {mistake.correction}")
            if mistake.prevention_tip:
                print(f"     💡 {mistake.prevention_tip}")

    if material.quiz_questions:
        print(f"\n### クイズ問題 ({len(material.quiz_questions)} items)")
        for i, q in enumerate(material.quiz_questions, 1):
            print(f"  {i}. [{q.question_type}] {q.question_text[:60]}...")
            if q.options:
                for opt in q.options[:2]:
                    print(f"      - {opt}")

    if material.reference_problems:
        print(f"\n### 参考問題 ({len(material.reference_problems)} items)")
        for ref in material.reference_problems:
            print(f"  • {ref.university} {ref.year} Q{ref.question_no}")
            print(f"    相似度: {ref.similarity_score:.0%}")

    print("\n### メタデータ")
    print(f"  Material ID: {material.material_id}")
    print(f"  作成日時: {material.created_at}")
    print(f"  難易度: {material.difficulty_level}")
    print(f"  OCR提供者: {material.ocr_provider}")
    print(f"  AWS Personalization スコア: {material.aws_personalization_score:.2f}")

    # ============================================================
    # STEP 5: JSON プレビュー
    # ============================================================
    print("\n" + "=" * 80)
    print("📄 JSON Output Preview")
    print("=" * 80)

    # JSON の一部を表示
    preview = {
        "material_id": material.material_id,
        "exam_metadata": material.exam_metadata.model_dump(by_alias=True),
        "difficulty_level": material.difficulty_level,
        "key_concepts": material.key_concepts,
        "outline_count": len(material.outline),
        "quiz_questions_count": len(material.quiz_questions),
        "common_mistakes_count": len(material.common_mistakes),
        "reference_problems_count": len(material.reference_problems),
    }

    print(json.dumps(preview, ensure_ascii=False, indent=2))

    print("\n" + "=" * 80)
    print("✅ Demo completed successfully!")
    print(f"📁 Full JSON output saved to: {output_file}")
    print("=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = test_material_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
