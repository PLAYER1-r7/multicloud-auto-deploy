"""教材生成エンジン：Azure/GCP SolveResponse → LearningMaterial"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.models import (
    CommonMistake,
    LearningMaterial,
    LearningOutlineStep,
    QuizQuestion,
    ReferenceProblem,
    SolveResponse,
)


class MaterialGenerator:
    """Azure/GCP の解答から学習教材を生成する"""

    def __init__(self):
        pass

    def generate_from_solve_response(
        self,
        solve_response: SolveResponse,
        exam: Any,
        problem_image_url: str | None = None,
    ) -> LearningMaterial:
        """
        Azure/GCP の SolveResponse から学習教材を生成

        Args:
            solve_response: 解答API のレスポンス
            exam: SolveExam メタデータ
            problem_image_url: オプション：問題画像のURL

        Returns:
            LearningMaterial: 教材化されたデータ
        """
        material_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # ステップを簡潔化
        outline = self._extract_outline(solve_response.answer.steps)

        # キーコンセプトを抽出
        key_concepts = self._extract_key_concepts(
            solve_response.problem_text, solve_response.answer.steps
        )

        # よくある間違いを集約
        common_mistakes = self._generate_common_mistakes(
            solve_response.answer.steps, key_concepts
        )

        # 難易度を判定
        difficulty = self._assess_difficulty(solve_response.answer.steps)

        # 学習目標を生成
        learning_objectives = self._generate_learning_objectives(
            solve_response.problem_text, key_concepts, difficulty
        )

        # クイズを自動生成（簡易版）
        quiz_questions = self._generate_quiz_questions(
            solve_response.answer.steps, solve_response.problem_text
        )

        # 参考問題（関連する大学/年度の問題）
        reference_problems = self._find_reference_problems(exam)

        return LearningMaterial(
            material_id=material_id,
            created_at=now,
            source_solve_response_id=solve_response.request_id,
            exam_metadata=exam,
            problem_text=solve_response.problem_text,
            problem_image_url=problem_image_url,
            solution_final=solve_response.answer.final,
            solution_steps=solve_response.answer.steps,
            solution_latex=solve_response.answer.latex,
            solution_confidence=solve_response.answer.confidence,
            ocr_provider=solve_response.meta.ocr_provider,
            outline=outline,
            key_concepts=key_concepts,
            quiz_questions=quiz_questions,
            common_mistakes=common_mistakes,
            difficulty_level=difficulty,
            learning_objectives=learning_objectives,
            reference_problems=reference_problems,
            aws_personalization_score=0.5,  # 後で Personalize で更新
        )

    def _extract_outline(self, steps: list[str]) -> list[LearningOutlineStep]:
        """
        各ステップを1行に簡潔化してアウトラインを生成

        例:
            Input: ["ステップ1: xxx という方法で yyyyyy を計算する", ...]
            Output: [
                {stepNumber: 1, brief: "xxx で yyyyyy を計算"},
                ...
            ]
        """
        outline = []
        for i, step in enumerate(steps, 1):
            # 最初の100文字を取る、長すぎれば省略
            brief = step[:100]
            if len(step) > 100:
                brief = brief.rsplit(" ", 1)[0] + "…"

            outline.append(
                LearningOutlineStep(
                    step_number=i,
                    brief=brief,
                    details=step,
                )
            )
        return outline

    def _extract_key_concepts(
        self, problem_text: str, solution_steps: list[str]
    ) -> list[str]:
        """
        問題と解答ステップから重要概念を抽出

        簡易版: よくある数学概念をキーワード検索
        """
        concepts = set()

        # 数学的キーワードのパターン
        patterns = [
            r"微分",
            r"積分",
            r"極限",
            r"微分方程式",
            r"不等式",
            r"連立方程式",
            r"行列式",
            r"固有値",
            r"三角関数",
            r"対数",
            r"指数",
            r"確率",
            r"ベクトル",
            r"平面",
            r"円",
            r"双曲線",
            r"楕円",
            r"放物線",
            r"複素数",
            r"連分数",
            r"合同",
            r"モジュロ",
            r"グラフ",
            r"関数",
            r"定理",
            r"公式",
        ]

        full_text = problem_text + " " + " ".join(solution_steps)
        for pattern in patterns:
            if re.search(pattern, full_text):
                concepts.add(pattern)

        return sorted(list(concepts))

    def _generate_common_mistakes(
        self, solution_steps: list[str], key_concepts: list[str]
    ) -> list[CommonMistake]:
        """
        よくある間違いを生成（簡易版）

        解法ステップから、数学的に陥りやすい誤りをテンプレートで生成
        """
        mistakes = []

        # 簡易版: 一般的な間違いパターン
        if any("積分" in c for c in key_concepts):
            mistakes.append(
                CommonMistake(
                    mistake_description="積分定数を忘れる",
                    why_wrong="不定積分は常に任意定数 C を含む",
                    correction="∫f(x)dx = F(x) + C (C は任意定数)",
                    prevention_tip="積分計算の最後に必ず +C を記入",
                )
            )

        if any("微分" in c for c in key_concepts):
            mistakes.append(
                CommonMistake(
                    mistake_description="合成関数の微分で連鎖律を適用し忘れ",
                    why_wrong="合成関数 f(g(x)) の微分には連鎖律が必須",
                    correction="{d/dx}f(g(x)) = f'(g(x)) · g'(x)",
                    prevention_tip="複雑な関数は必ず連鎖律を意識",
                )
            )

        if any("不等式" in c for c in key_concepts):
            mistakes.append(
                CommonMistake(
                    mistake_description="負の数で両辺をかけるとき不等号の向きを変え忘れ",
                    why_wrong="負数乗算で不等号方向が反転する",
                    correction="a < b かつ c < 0 なら a·c > b·c",
                    prevention_tip="負数乗算・除算時は必ず不等号を反転",
                )
            )

        return mistakes[:3]  # 最大3つまで

    def _assess_difficulty(self, steps: list[str]) -> str:
        """
        解答ステップ数とテキスト長から難易度を判定
        """
        step_count = len(steps)
        total_length = sum(len(s) for s in steps)
        avg_length = total_length / step_count if step_count > 0 else 0

        # 簡易ヒューリスティック
        if step_count <= 2 or avg_length < 50:
            return "basic"
        elif step_count <= 5 or avg_length < 150:
            return "intermediate"
        else:
            return "advanced"

    def _generate_learning_objectives(
        self, problem_text: str, key_concepts: list[str], difficulty: str
    ) -> list[str]:
        """学習目標を生成"""
        objectives = []

        # 難易度に応じた目標
        if difficulty == "basic":
            objectives.append("基本公式を理解する")
            objectives.append("単純な計算手順を習得する")
        elif difficulty == "intermediate":
            objectives.append("複数の概念を統合する")
            objectives.append("段階的な問題解決能力を養う")
        else:
            objectives.append("高度な数学的推論を習得する")
            objectives.append("複雑な問題の分解と統合を学ぶ")

        # 概念ベースの目標
        if key_concepts:
            top_concepts = key_concepts[:2]
            for concept in top_concepts:
                objectives.append(f"「{concept}」に関する深い理解を身につける")

        return objectives[:4]  # 最大4つまで

    def _generate_quiz_questions(
        self, solution_steps: list[str], problem_text: str
    ) -> list[QuizQuestion]:
        """
        クイズ問題を自動生成（簡易版）

        # 実装の都合上、テンプレートに貼り込み
        # 本番環境では Bedrock で動的生成
        """
        questions = []

        # クイズ1: 最終答案
        questions.append(
            QuizQuestion(
                question_id=str(uuid.uuid4()),
                question_type="short_answer",
                question_text="この問題の最終答案を書いてください",
                answer="（解答を確認してください）",
                explanation="上記の解法プロセスを参考に、答案を作成しましょう",
            )
        )

        # クイズ2: 最初のステップ確認
        if solution_steps:
            first_step = solution_steps[0]
            steps_preview = first_step[:100]

            questions.append(
                QuizQuestion(
                    question_id=str(uuid.uuid4()),
                    question_type="fill_blank",
                    question_text=f"最初のステップは「{steps_preview}....」です。この方針の理由は何ですか？",
                    answer="（上記解説を参考に論述してください）",
                    explanation="問題の条件と必要な計算方法を関連付けることが大切です",
                )
            )

        return questions

    def _find_reference_problems(self, exam: Any) -> list[ReferenceProblem]:
        """
        関連する参考問題を見つける（簡易版）

        実装では、同じ大学の別年度の問題を参考として提案
        # TODO: 実際には DB や 外部 API と連携して参考問題を検索
        """
        problems = []

        if exam.university and exam.year:
            # 同じ大学の前年・翌年の問題を参考として提案
            for offset in [-1, 1]:
                ref_year = exam.year + offset
                if ref_year > 2000:  # 1990年以降のデータを想定
                    problems.append(
                        ReferenceProblem(
                            university=exam.university,
                            year=ref_year,
                            question_no=exam.question_no or "1",
                            similarity_score=0.85 - abs(offset) * 0.1,
                        )
                    )

        return problems

    def to_dict(self, material: LearningMaterial) -> dict[str, Any]:
        """LearningMaterial を辞書に変換（JSON出力用）"""
        return material.model_dump(by_alias=True, exclude_none=True)
