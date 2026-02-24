import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./App.css";
import App from "./App.tsx";

// www なしの azure.ashnova.jp でアクセスされた場合、www 付きに強制リダイレクト
// (古いブックマーク・キャッシュ・Safe Browsing 警告対策)
if (
  typeof window !== "undefined" &&
  window.location.hostname === "azure.ashnova.jp"
) {
  window.location.replace(
    "https://www.azure.ashnova.jp" + window.location.pathname + window.location.search + window.location.hash
  );
}

// basename from Vite's base config (e.g. /sns/ → /sns)
const basename = import.meta.env.BASE_URL.replace(/\/$/, "") || "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
