import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./App.css";
import App from "./App.tsx";

// www なしドメインへのアクセスを www 付きに強制リダイレクト
// (古いブックマーク・DNSキャッシュ・Safe Browsing 警告対策)
// azure.ashnova.jp は一時的にAFDに設定されGoogleにクロールされたため警告が発生した実績あり。
// AWS/GCP も同様のリスクに備えて予防的に対処する。
const NON_WWW_REDIRECT: Record<string, string> = {
  "azure.ashnova.jp": "www.azure.ashnova.jp",
  "aws.ashnova.jp": "www.aws.ashnova.jp",
  "gcp.ashnova.jp": "www.gcp.ashnova.jp",
};
if (typeof window !== "undefined") {
  const wwwHost = NON_WWW_REDIRECT[window.location.hostname];
  if (wwwHost) {
    window.location.replace(
      "https://" +
        wwwHost +
        window.location.pathname +
        window.location.search +
        window.location.hash,
    );
  }
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
