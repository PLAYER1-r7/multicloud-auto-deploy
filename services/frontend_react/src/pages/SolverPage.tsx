import { useState } from "react";
import { solveMath } from "../api/solve";
import type { SolveResponse } from "../types/solve";

// ═══════════════════════════════════════════
// 東大 2025 数学 第1問 固定デモ
// ═══════════════════════════════════════════
const DEMO_EXAM = {
  university: "tokyo",
  year: 2025,
  subject: "math",
  questionNo: "1",
} as const;

const PROBLEM_IMAGE_URL =
  "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg";

// ─────────────────────────────────────────
export default function SolverPage() {
  const [result, setResult] = useState<SolveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [imgError, setImgError] = useState(false);
  const [ocrExpanded, setOcrExpanded] = useState(false);

  const handleSolve = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await solveMath({
        input: { source: "url", imageUrl: PROBLEM_IMAGE_URL },
        exam: DEMO_EXAM,
        options: { mode: "fast", needSteps: true, needLatex: false },
      });
      setResult(res);
    } catch (e: unknown) {
      type AxiosLike = { response?: { data?: { detail?: string } } };
      const detail = (e as AxiosLike).response?.data?.detail;
      setError(detail ?? (e as Error).message ?? "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="solver-page">
      {/* ── ヘッダー ─────────────────────────── */}
      <div className="solver-header">
        <span className="solver-badge">大学入試 AI 解答デモ</span>
        <h2 className="solver-title">東京大学 2025年度 前期 数学 第1問</h2>
        <p className="solver-desc">
          OCR × Gemini による自動解答サービスのデモページです。
          <br />
          問題文の読み取り結果と AI による解説付き解答を表示します。
        </p>
      </div>

      {/* ── 本体 (2カラム) ──────────────────── */}
      <div className="solver-body">
        {/* 左: 問題画像 */}
        <div className="solver-panel">
          <h3 className="panel-title">問題文</h3>
          {!imgError ? (
            <img
              src={PROBLEM_IMAGE_URL}
              alt="東京大学 2025年度 数学 第1問"
              className="problem-image"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="image-fallback">
              <svg
                className="icon"
                viewBox="0 0 24 24"
                width="40"
                height="40"
                aria-hidden="true"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9l5 5 4-4 4 4 5-5" />
              </svg>
              <p>画像を読み込めませんでした</p>
              <p className="muted" style={{ fontSize: "0.8rem" }}>
                (HTTP mixed-content ブロックの可能性があります)
              </p>
              <a
                href="http://server-test.net/math/tokyo/q_pdf/2025_1.pdf"
                target="_blank"
                rel="noreferrer"
                className="link"
              >
                PDF を開く →
              </a>
            </div>
          )}
        </div>

        {/* 右: 解答パネル */}
        <div className="solver-panel">
          <h3 className="panel-title">AI 解答</h3>

          {/* 解答取得ボタン */}
          {!result && !loading && (
            <div className="solver-cta">
              <p className="solver-hint">
                ボタンを押すと OCR で問題文を読み取り、AI が解答します。
              </p>
              <button
                type="button"
                className="button primary solver-btn"
                onClick={handleSolve}
              >
                AI 解答を取得
                <span className="solver-btn-sub">（約 30〜60 秒）</span>
              </button>
            </div>
          )}

          {/* ローディング */}
          {loading && (
            <div className="solver-loading">
              <div className="spinner" />
              <p>OCR + AI 解析中です。しばらくお待ちください…</p>
            </div>
          )}

          {/* エラー */}
          {error && (
            <div className="alert error" style={{ marginTop: "1rem" }}>
              <strong>エラー:</strong> {error}
              <br />
              <button
                type="button"
                className="button ghost"
                style={{ marginTop: "0.75rem" }}
                onClick={handleSolve}
              >
                再試行
              </button>
            </div>
          )}

          {/* 結果 */}
          {result && (
            <div className="solve-result">
              {/* ── OCR テキスト (折りたたみ) ─── */}
              <div className="result-section">
                <button
                  type="button"
                  className="section-toggle"
                  onClick={() => setOcrExpanded((p) => !p)}
                  aria-expanded={ocrExpanded}
                >
                  <span>OCR 読み取り結果</span>
                  <span className="ocr-meta">
                    {result.meta.ocrSource ?? "—"}{" "}
                    {result.meta.ocrScore != null
                      ? `· スコア ${result.meta.ocrScore.toFixed(2)}`
                      : ""}
                  </span>
                  <span className="toggle-arrow">
                    {ocrExpanded ? "▲" : "▼"}
                  </span>
                </button>
                {ocrExpanded && (
                  <pre className="ocr-text">{result.problemText}</pre>
                )}
              </div>

              {/* ── AI 解答 ───────────────────── */}
              <div className="result-section answer-box">
                <div className="answer-header">
                  <h4 className="answer-title">解答</h4>
                  <span
                    className={`conf-badge ${
                      result.answer.confidence >= 0.8
                        ? "high"
                        : result.answer.confidence >= 0.5
                          ? "mid"
                          : "low"
                    }`}
                  >
                    確信度 {Math.round(result.answer.confidence * 100)}%
                  </span>
                </div>
                <div className="answer-final">{result.answer.final}</div>

                {result.answer.steps.length > 0 && (
                  <div className="answer-steps">
                    <h5 className="steps-title">解説ステップ</h5>
                    <ol className="steps-list">
                      {result.answer.steps.map((step, i) => (
                        <li key={i} className="step-item">
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>

              {/* ── メタ情報 ─────────────────── */}
              <div className="result-meta">
                <span>🤖 {result.meta.model}</span>
                <span>⏱ {(result.meta.latencyMs / 1000).toFixed(1)}s</span>
                <span>💲 ${result.meta.costUsd.toFixed(4)}</span>
              </div>

              {/* 再取得ボタン */}
              <button
                type="button"
                className="button ghost"
                style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}
                onClick={handleSolve}
              >
                再取得
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
