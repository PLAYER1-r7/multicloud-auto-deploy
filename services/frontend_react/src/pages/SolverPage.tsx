import { useState } from "react";
import { solveMath } from "../api/solve";
import type { SolveResponse } from "../types/solve";
import MathText from "../components/MathText";
import MathGraph from "../components/MathGraph";

// ═══════════════════════════════════════════
// 東大 2025 数学 第1問 固定デモ
// ═══════════════════════════════════════════
const DEMO_EXAM = {
  university: "tokyo",
  year: 2025,
  subject: "math",
  questionNo: "1",
} as const;

const PROBLEM_IMAGE_URL = "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg";

// 東大 2025 数学 第1問 LaTeX 問題文
const PROBLEM_LATEX = `座標平面上の点 $A(0, 0)$，$B(0, 1)$，$C(1, 1)$，$D(1, 0)$ を考える。\
実数 $0 < t < 1$ に対して，線分 $AB$，$BC$，$CD$ を $t : (1-t)$ に内分する点をそれぞれ $P_t$，$Q_t$，$R_t$ とし，\
線分 $P_tQ_t$，$Q_tR_t$ を $t : (1-t)$ に内分する点をそれぞれ $S_t$，$T_t$ とする。\
さらに，線分 $S_tT_t$ を $t : (1-t)$ に内分する点を $U_t$ とする。\
また，点 $A$ を $U_0$，点 $D$ を $U_1$ とする。

(1) 点 $U_t$ の座標を求めよ。

(2) $t$ が $0 \\leqq t \\leqq 1$ の範囲を動くときに点 $U_t$ が描く曲線と，線分 $AD$ で囲まれた部分の面積を求��よ。

(3) $a$ を $0 < a < 1$ を満たす実数とする。$t$ が $0 \\leqq t \\leqq a$ の範囲を動くときに点 $U_t$ が描く曲線の長さを，$a$ の多項式の形で求めよ。`;

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
        options: {
          mode: "accurate",
          needSteps: true,
          needLatex: true,
          maxTokens: 8192,
        },
      });
      setResult(res);
    } catch (e: unknown) {
      type ApiDetail = { loc?: unknown[]; msg?: string };
      type AxiosLike = { response?: { data?: { detail?: unknown } } };
      const raw = (e as AxiosLike).response?.data?.detail;
      const detail = Array.isArray(raw)
        ? (raw as ApiDetail[])
            .map(
              (d) =>
                `${d.loc ? d.loc.join(".") + ": " : ""}${d.msg ?? JSON.stringify(d)}`,
            )
            .join("\n")
        : typeof raw === "string"
          ? raw
          : raw != null
            ? JSON.stringify(raw)
            : null;
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
          {/* LaTeX 問題文（常に表示） */}
          <div className="problem-latex">
            <MathText text={PROBLEM_LATEX} />
          </div>

          {/* 問題画像（読み込み成功時のみ表示） */}
          {!imgError ? (
            <details className="problem-image-details">
              <summary className="problem-image-summary">
                問題画像を見る
              </summary>
              <img
                src={PROBLEM_IMAGE_URL}
                alt="東京大学 2025年度 数学 第1問"
                className="problem-image"
                onError={() => setImgError(true)}
              />
            </details>
          ) : (
            <p
              className="muted"
              style={{ fontSize: "0.8rem", marginTop: "0.5rem" }}
            >
              ※ 画像は mixed-content のためブロックされました。
              <a
                href="http://server-test.net/math/tokyo/q_pdf/2025_1.pdf"
                target="_blank"
                rel="noreferrer"
                className="link"
                style={{ marginLeft: "0.3em" }}
              >
                PDF を開く →
              </a>
            </p>
          )}
          {/* 注記: PROBLEM_IMAGE_URL は http:// のため HTTPS ページでは mixed-content ブロックされます */}
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
                <div className="answer-final">
                  <MathText text={result.answer.final} />
                </div>

                {/* LaTeX 最終答案ブロック */}
                {result.answer.latex && (
                  <div className="answer-latex-block">
                    <span className="answer-latex-label">LaTeX</span>
                    <MathText text={`$$${result.answer.latex}$$`} />
                  </div>
                )}

                {/* 図示ガイド */}
                {result.answer.diagramGuide && (
                  <div className="answer-diagram-guide">
                    <h5 className="steps-title">図示ガイド</h5>
                    <p className="diagram-guide-text">
                      {result.answer.diagramGuide}
                    </p>
                  </div>
                )}

                {/* インタラクティブグラフ */}
                {result.answer.plotData?.needPlot && (
                  <div className="answer-graph">
                    <h5 className="steps-title">グラフ</h5>
                    <MathGraph data={result.answer.plotData} />
                  </div>
                )}

                {result.answer.steps.length > 0 && (
                  <div className="answer-steps">
                    <h5 className="steps-title">解説ステップ</h5>
                    <ol className="steps-list">
                      {result.answer.steps.map((step, i) => {
                        // $が含まれない場合、LaTeXコマンドを検出して自動ラップ
                        let displayStep = step;
                        if (!step.includes("$") && /\\[a-zA-Z{(]/.test(step)) {
                          // LaTeX改行 \\ を含む場合は aligned 環境で包む
                          if (/\\\\/.test(step)) {
                            displayStep = `$$\\begin{aligned}${step}\\end{aligned}$$`;
                          } else {
                            displayStep = `$$${step}$$`;
                          }
                        }
                        return (
                          <li key={i} className="step-item">
                            <MathText text={displayStep} />
                          </li>
                        );
                      })}
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
