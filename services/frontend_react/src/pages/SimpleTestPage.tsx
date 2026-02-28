import { useEffect, useState } from "react";

export default function SimplePage() {
  const [message, setMessage] = useState("ローディング中...");
  const [apiStatus, setApiStatus] = useState("確認中...");

  useEffect(() => {
    // Set message after a short delay to confirm React is working
    setTimeout(() => {
      setMessage("✅ React は正常に動作しています!");
    }, 500);

    // Check API
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => {
        setApiStatus(`✅ API サーバー: ${data.status}`);
      })
      .catch((err) => {
        setApiStatus(`❌ API エラー: ${err.message}`);
      });
  }, []);

  return (
    <div
      style={{
        padding: "2rem",
        fontFamily: "monospace",
        maxWidth: "800px",
        margin: "0 auto",
      }}
    >
      <h1>🧪 React 動作確認ページ</h1>

      <div
        style={{
          background: "#f0f0f0",
          padding: "1.5rem",
          borderRadius: "8px",
          marginTop: "1rem",
          border: "2px solid #667eea",
        }}
      >
        <p style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>
          <strong>React ステータス:</strong>
        </p>
        <p style={{ color: "#4caf50", fontSize: "1.1rem", fontWeight: "bold" }}>
          {message}
        </p>
      </div>

      <div
        style={{
          background: "#f0f0f0",
          padding: "1.5rem",
          borderRadius: "8px",
          marginTop: "1rem",
          border: "2px solid #667eea",
        }}
      >
        <p style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>
          <strong>API ステータス:</strong>
        </p>
        <p
          style={{
            color: apiStatus.includes("✅") ? "#4caf50" : "#f44336",
            fontSize: "1.1rem",
            fontWeight: "bold",
          }}
        >
          {apiStatus}
        </p>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <h2>📍 ナビゲーション</h2>
        <ul style={{ fontSize: "1rem", lineHeight: "1.8" }}>
          <li>
            <a href="/" style={{ color: "#667eea", textDecoration: "none" }}>
              ↩️ ホームに戻る
            </a>
          </li>
          <li>
            <a
              href="/exam"
              style={{ color: "#667eea", textDecoration: "none" }}
            >
              🧮 PHASE 3 (SolverPage) を開く
            </a>
          </li>
        </ul>
      </div>

      <div style={{ marginTop: "2rem", color: "#666", fontSize: "0.9rem" }}>
        <p>
          💡 <strong>このページが表示されている場合:</strong> React
          は正常に動作しています
        </p>
        <p>
          🐛 <strong>SolverPage で「くるくる」が表示される場合:</strong> Vite
          をリロードしてください (Ctrl+Shift+R)
        </p>
      </div>
    </div>
  );
}
