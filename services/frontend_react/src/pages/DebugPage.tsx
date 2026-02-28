import { useEffect, useState } from "react";

export default function DebugPage() {
  const [info, setInfo] = useState<{
    location: string;
    timestamp: string;
    apiAvailable: boolean;
  }>({
    location: "N/A",
    timestamp: new Date().toISOString(),
    apiAvailable: false,
  });

  useEffect(() => {
    const checkApi = async () => {
      try {
        const res = await fetch("http://localhost:8000/health");
        setInfo((prev) => ({
          ...prev,
          apiAvailable: res.ok,
          location: window.location.href,
          timestamp: new Date().toISOString(),
        }));
      } catch {
        setInfo((prev) => ({
          ...prev,
          apiAvailable: false,
          location: window.location.href,
        }));
      }
    };

    checkApi();
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "monospace" }}>
      <h1>🔧 Debug Page - PHASE 3 確認</h1>

      <div
        style={{
          background: "#f0f0f0",
          padding: "1rem",
          borderRadius: "4px",
          marginTop: "1rem",
        }}
      >
        <p>
          <strong>ページロケーション:</strong> {info.location}
        </p>
        <p>
          <strong>タイムスタンプ:</strong> {info.timestamp}
        </p>
        <p>
          <strong>API ステータス:</strong>{" "}
          {info.apiAvailable ? (
            <span style={{ color: "green" }}>✅ 利用可能</span>
          ) : (
            <span style={{ color: "red" }}>❌ 接続不可</span>
          )}
        </p>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <h2>🎯 検証チェック</h2>
        <ul>
          <li>
            ✅ React dev サーバー: <strong>起動中</strong> (localhost:5173)
          </li>
          <li>
            {info.apiAvailable ? "✅" : "❌"} API サーバー:{" "}
            <strong>{info.apiAvailable ? "起動中" : "停止"}</strong>{" "}
            (localhost:8000)
          </li>
          <li>✅ Router: 正常に動作</li>
        </ul>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <h2>📝 PHASE 3 ページへのリンク</h2>
        <p>
          <a
            href="/exam"
            style={{
              display: "inline-block",
              padding: "0.75rem 1.5rem",
              background: "#007bff",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
              marginRight: "1rem",
            }}
          >
            SolverPage を開く
          </a>
          <a
            href="/"
            style={{
              display: "inline-block",
              padding: "0.75rem 1.5rem",
              background: "#6c757d",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
            }}
          >
            ホームに戻る
          </a>
        </p>
      </div>

      <div style={{ marginTop: "2rem", fontSize: "0.85rem", color: "#666" }}>
        <h3>💡 トラブルシューティング</h3>
        <ol>
          <li>このページが表示される → React 自体は正常です</li>
          <li>
            API ステータスが ❌ → API サーバーを起動してください:
            <br />
            <code>cd services/api && uvicorn app.main:app --reload</code>
          </li>
          <li>
            /exam に移動して何も表示されない →
            コンソールエラーを確認してください
            <br />
            (ブラウザ: F12 → Console タブ)
          </li>
        </ol>
      </div>
    </div>
  );
}
