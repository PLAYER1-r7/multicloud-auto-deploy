/** 拡張教材表示コンポーネント（PHASE 2） */

import { useState } from "react";
import MathText from "./MathText";
import type { EnhancedLearningMaterial } from "../types/learning";

interface EnhancedMaterialCardProps {
  material: EnhancedLearningMaterial;
  onLoadAudio?: (materialId: string) => void;
  onShowDeepDive?: (concept: string, explanation: string) => void;
}

/**
 * 拡張教材カードコンポーネント
 * - PHASE 1: 基本教材表示（問題、解答、ステップ、概念、クイズ）
 * - PHASE 2: Bedrock 拡張（詳細説明、概念掘り下げ、誤り分析）
 */
export default function EnhancedMaterialCard({
  material,
  onLoadAudio,
  onShowDeepDive,
}: EnhancedMaterialCardProps) {
  const [expandedSections, setExpandedSections] = useState<
    Record<string, boolean>
  >({
    outline: true,
    explanation: false,
    concepts: false,
    mistakes: false,
    quiz: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleDeepDive = (concept: string) => {
    const explanation =
      material.conceptDeepDives?.[concept] || "概念の詳細説明が利用できません";
    onShowDeepDive?.(concept, explanation);
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-white rounded-lg shadow-lg overflow-hidden">
      {/* ── ヘッダー ──────────────────────────────────── */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 text-white">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold mb-2">
              {material.baseMaterial.examMetadata.university.toUpperCase()}{" "}
              {material.baseMaterial.examMetadata.year}
            </h2>
            <p className="text-sm text-blue-100">
              {material.baseMaterial.examMetadata.subject} · Q
              {material.baseMaterial.examMetadata.questionNo}
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold">
              難度:{" "}
              <span className="badge">
                {material.baseMaterial.difficultyLevel}
              </span>
            </div>
            {material.isFullyEnhanced && (
              <div className="mt-2 text-xs bg-green-500/20 px-2 py-1 rounded">
                ✓ 完全拡張済み
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 問題文 ────────────────────────────────────── */}
      <div className="border-b border-gray-200 px-6 py-4 bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">問題</h3>
        <div className="prose prose-sm max-w-none">
          <MathText text={material.baseMaterial.problemText} />
        </div>
      </div>

      {/* ── 解答 ──────────────────────────────────────── */}
      <div className="border-b border-gray-200 px-6 py-4 bg-green-50">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">解答</h3>
        <div className="prose prose-sm max-w-none text-green-900">
          <MathText text={material.baseMaterial.solutionLatex} />
        </div>
        <p className="text-xs text-green-700 mt-2">
          確信度: {(material.baseMaterial.solutionConfidence * 100).toFixed(0)}%
        </p>
      </div>

      {/* ── アウトライン（ステップ） ────────────────────────────────── */}
      <div className="border-b border-gray-200">
        <button
          onClick={() => toggleSection("outline")}
          className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition"
        >
          <div className="flex items-center gap-3">
            <span aria-hidden="true">📘</span>
            <span className="font-semibold text-gray-800">解法ステップ</span>
            <span className="text-sm text-gray-500">
              ({material.baseMaterial.outline.length} ステップ)
            </span>
          </div>
          <span>{expandedSections.outline ? "▲" : "▼"}</span>
        </button>

        {expandedSections.outline && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
            <ol className="space-y-3">
              {material.baseMaterial.outline.map((step) => (
                <li key={step.stepNumber} className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                    {step.stepNumber}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{step.brief}</p>
                    <p className="text-sm text-gray-600 mt-1">{step.details}</p>
                    {step.keyFormula && (
                      <div className="mt-2 bg-white p-2 rounded border-l-2 border-blue-400">
                        <MathText text={step.keyFormula} />
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {/* ── Bedrock 拡張: 詳細説明 ────────────────────────────────── */}
      {material.detailedExplanation && (
        <div className="border-b border-gray-200">
          <button
            onClick={() => toggleSection("explanation")}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition"
          >
            <div className="flex items-center gap-3">
              <span className="text-lg">🤖</span>
              <span className="font-semibold text-gray-800">
                Bedrock 詳細解説
              </span>
              <span className="text-xs text-gray-500">(AI 生成)</span>
            </div>
            <span>{expandedSections.explanation ? "▲" : "▼"}</span>
          </button>

          {expandedSections.explanation && (
            <div className="px-6 py-4 bg-amber-50 border-t border-gray-200">
              <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
                {material.detailedExplanation}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Bedrock 拡張: 概念掘り下げ ────────────────────────────────── */}
      {Object.keys(material.conceptDeepDives || {}).length > 0 && (
        <div className="border-b border-gray-200">
          <button
            onClick={() => toggleSection("concepts")}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition"
          >
            <div className="flex items-center gap-3">
              <span className="text-lg">🔍</span>
              <span className="font-semibold text-gray-800">概念の深掘り</span>
              <span className="text-xs text-gray-500">
                ({Object.keys(material.conceptDeepDives).length})
              </span>
            </div>
            <span>{expandedSections.concepts ? "▲" : "▼"}</span>
          </button>

          {expandedSections.concepts && (
            <div className="px-6 py-4 bg-purple-50 border-t border-gray-200 space-y-3">
              {Object.entries(material.conceptDeepDives).map(
                ([concept]) => (
                  <button
                    key={concept}
                    onClick={() => handleDeepDive(concept)}
                    className="block w-full text-left p-3 bg-white rounded border border-purple-200 hover:border-purple-400 hover:bg-purple-100 transition"
                  >
                    <p className="font-semibold text-purple-900">{concept}</p>
                    <p className="text-xs text-purple-700 mt-1">
                      クリックで詳細を表示
                    </p>
                  </button>
                ),
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Bedrock 拡張: 誤り分析 ────────────────────────────────── */}
      {(material.mistakeAnalysis || material.baseMaterial.commonMistakes)
        .length > 0 && (
        <div className="border-b border-gray-200">
          <button
            onClick={() => toggleSection("mistakes")}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition"
          >
            <div className="flex items-center gap-3">
              <span aria-hidden="true">⚠️</span>
              <span className="font-semibold text-gray-800">よくある誤り</span>
              <span className="text-xs text-gray-500">
                (
                {(material.mistakeAnalysis?.length || 0) +
                  material.baseMaterial.commonMistakes.length}
                )
              </span>
            </div>
            <span>{expandedSections.mistakes ? "▲" : "▼"}</span>
          </button>

          {expandedSections.mistakes && (
            <div className="px-6 py-4 bg-red-50 border-t border-gray-200 space-y-4">
              {material.baseMaterial.commonMistakes.map((mistake, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-white rounded border-l-4 border-red-400"
                >
                  <p className="font-semibold text-red-900">
                    {mistake.mistakeDescription}
                  </p>
                  <p className="text-sm text-red-700 mt-1">
                    <strong>なぜ間違い？</strong> {mistake.whyWrong}
                  </p>
                  <p className="text-sm text-green-700 mt-1">
                    <strong>正しい解答:</strong> {mistake.correction}
                  </p>
                  <p className="text-xs text-gray-600 mt-1 italic">
                    💡 {mistake.preventionTip}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── クイズ ────────────────────────────────────── */}
      {material.baseMaterial.quizQuestions.length > 0 && (
        <div className="border-b border-gray-200">
          <button
            onClick={() => toggleSection("quiz")}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition"
          >
            <div className="flex items-center gap-3">
              <span className="text-lg">📝</span>
              <span className="font-semibold text-gray-800">クイズ問題</span>
              <span className="text-xs text-gray-500">
                ({material.baseMaterial.quizQuestions.length})
              </span>
            </div>
            <span>{expandedSections.quiz ? "▲" : "▼"}</span>
          </button>

          {expandedSections.quiz && (
            <div className="px-6 py-4 bg-blue-50 border-t border-gray-200 space-y-4">
              {material.baseMaterial.quizQuestions.map((q, idx) => (
                <div
                  key={q.questionId}
                  className="p-3 bg-white rounded border border-blue-200"
                >
                  <p className="font-semibold text-gray-900">
                    Q{idx + 1}: {q.questionText}
                  </p>
                  {q.options && (
                    <ul className="mt-2 space-y-1">
                      {q.options.map((opt, oidx) => (
                        <li key={oidx} className="text-sm text-gray-700">
                          ○ {opt}
                        </li>
                      ))}
                    </ul>
                  )}
                  <details className="mt-2">
                    <summary className="text-sm text-blue-600 cursor-pointer hover:underline">
                      解答・解説を表示
                    </summary>
                    <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
                      <p>
                        <strong>解答:</strong> {q.answer}
                      </p>
                      <p className="mt-1">
                        <strong>解説:</strong> {q.explanation}
                      </p>
                    </div>
                  </details>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── フッター ──────────────────────────────────── */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center">
        <div className="text-xs text-gray-500">
          Material ID: {material.baseMaterial.materialId.substring(0, 8)}...
        </div>
        <button
          onClick={() => onLoadAudio?.(material.baseMaterial.materialId)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition text-sm font-medium"
        >
          🔊 音声を再生
        </button>
      </div>
    </div>
  );
}
