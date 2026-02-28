#!/usr/bin/env python3
"""
教材生成テストスクリプト

使用法:
  python scripts/test_material_generation.py

このスクリプトは：
1. 東大2025年度1問の解答PDFをダウンロード
2. 模擬 SolveResponse を生成
3. MaterialGenerator で教材に変換
4. JSON形式で結果を表示
"""

import json
import sys
from pathlib import Path

# Python パスを設定
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))

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
    東大2025年度第1問の模擬解答を生成

    実際の解答PDFから手作業で抽出したテキストをベースに構築
    """
    return SolveResponse(
        request_id="test-2025-tokyo-1",
        status="ok",
        problem_text="""
        問題：関数 f(x) = log(1 + x) について、以下の問いに答えよ。
        (1) f(x) の Taylor 級数展開を求めよ。
        (2) 定積分 ∫_0^1 [log(1 + x) / x] dx を計算せよ。
        """.strip(),
        answer=SolveAnswer(
            final="∫_0^1 [log(1 + x) / x] dx = π²/12",
            latex=r"\frac{\pi^2}{12}",
            steps=[
                "f(x) = log(1 + x) の Taylor 級数展開： f(x) = Σ_{n=1}^{∞} (-1)^{n+1} x^n / n (-1 < x ≤ 1)",
                "log(1 + x) / x = Σ_{n=1}^{∞} (-1)^{n+1} x^{n-1} / n",
                "∫_0^1 [log(1 + x) / x] dx = Σ_{n=1}^{∞} (-1)^{n+1} ∫_0^1 x^{n-1} / n dx",
                "= Σ_{n=1}^{∞} (-1)^{n+1} / (n² ) = η(2) = π²/12",
            ],
            diagram_guide=None,
            plot_data=PlotData(need_plot=False),
            confidence=0.95,
        ),
        meta=SolveMeta(
            ocr_provider="azure",
            ocr_source="azure_di_merged",
            ocr_score=1.389,
            ocr_candidates=5,
            model="gpt-4o",
            latency_ms=4230,
            cost_usd=0.0045,
        ),
    )


def test_material_generation():
    """教材生成テストを実行"""
    print("=" * 80)
    print("AWS Learning Assistant - 教材生成テスト")
    print("=" * 80)
    print()

    # Step 1: Mock SolveResponse を生成
    print("📝 [Step 1] 模擬 SolveResponse を生成中...")
    solve_response = create_mock_solve_response()
    exam = SolveExam(
        university="tokyo",
        year=2025,
        subject="math",
        question_no="1",
    )
    print(f"   ✓ Problem: {solve_response.problem_text[:60]}...")
    print(f"   ✓ Answer: {solve_response.answer.final}")
    print(f"   ✓ Steps: {len(solve_response.answer.steps)} ステップ")
    print(f"   ✓ Exam: {exam.university} {exam.year} 第{exam.question_no}問")
    print()

    # Step 2: MaterialGenerator で教材を生成
    print("🛠️  [Step 2] MaterialGenerator で教材を生成中...")
    generator = MaterialGenerator()
    material = generator.generate_from_solve_response(
        solve_response,
        exam=exam,
        problem_image_url="http://server-test.net/math/tokyo/q_jpg/2025_1.jpg",
    )
    print(f"   ✓ Material ID: {material.material_id}")
    print(f"   ✓ Created: {material.created_at}")
    print()

    # Step 3: 生成された教材の内容を表示
    print("📚 [Step 3] 生成された教材の内容")
    print()

    print(f"  📖 学習アウトライン ({len(material.outline)} ステップ):")
    for outline_step in material.outline:
        print(f"      Step {outline_step.step_number}: {outline_step.brief}")
    print()

    print(f"  🔑 キーコンセプト ({len(material.key_concepts)} 個):")
    for concept in material.key_concepts:
        print(f"      - {concept}")
    print()

    print(f"  ⚠️  よくある間違い ({len(material.common_mistakes)} 個):")
    for mistake in material.common_mistakes:
        print(f"      - {mistake.mistake_description}")
        print(f"        理由: {mistake.why_wrong}")
        print(f"        対策: {mistake.correction}")
    print()

    print(f"  📊 難易度レベル: {material.difficulty_level}")
    print(f"  🎯 学習目標 ({len(material.learning_objectives)} 個):")
    for obj in material.learning_objectives:
        print(f"      - {obj}")
    print()

    print(f"  ❓ クイズ問題 ({len(material.quiz_questions)} 個):")
    for quiz in material.quiz_questions[:2]:
        print(f"      Q: {quiz.question_text[:60]}...")
    print()

    print(f"  🔗 参考問題 ({len(material.reference_problems)} 個):")
    for ref in material.reference_problems:
        print(f"      - {ref.university} {ref.year} 問{ref.question_no}")
    print()

    # Step 4: JSON 出力
    print("💾 [Step 4] JSON形式での出力（学習プラットフォーム用）")
    print()

    material_dict = generator.to_dict(material)
    json_output = json.dumps(material_dict, ensure_ascii=False, indent=2)

    # 出力ファイルに保存
    output_file = Path("/tmp/material_generation_test.json")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json_output)

    print(f"  ✓ 出力ファイル: {output_file}")
    print(f"  ✓ ファイルサイズ: {len(json_output)} 文字")
    print()

    # JSON の先頭を表示
    lines = json_output.split("\n")[:20]
    print("  JSON プレビュー（先頭20行）:")
    for line in lines:
        print(f"    {line}")
    if len(json_output.split("\n")) > 20:
        print(f"    ... ({len(json_output.split(chr(10))) - 20} 行省略)")
    print()

    # Step 5: サマリー
    print("=" * 80)
    print("✅ 教材生成テスト完了")
    print("=" * 80)
    print()
    print("次のステップ:")
    print("  1. ✓ LearningMaterial モデルの定義")
    print("  2. ✓ MaterialGenerator の実装")
    print("  3. ✓ テストスクリプトの実行")
    print("  4. → AWS Bedrock との統合（解説拡張）")
    print("  5. → Polly 音声化サービス")
    print("  6. → FastAPI ルートの実装")
    print()


if __name__ == "__main__":
    try:
        test_material_generation()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
