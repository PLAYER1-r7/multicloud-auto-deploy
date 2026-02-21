import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  authProvider,
  isFirebase,
  FIREBASE_CONFIG,
  getLoginUrl,
} from "../config/auth";
import { useAuth } from "../contexts/AuthContext";
import Alert from "../components/Alert";

export default function LoginPage() {
  const { isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const firebaseInitialized = useRef(false);

  // Already logged in → go home
  useEffect(() => {
    if (isLoggedIn) navigate("/", { replace: true });
  }, [isLoggedIn, navigate]);

  // ----- AWS Cognito / Azure AD: simple redirect -----
  const handleRedirectLogin = () => {
    const url = getLoginUrl();
    if (url) {
      window.location.href = url;
    } else {
      setError("認証設定が不完全です。管理者に連絡してください。");
    }
  };

  // ----- Firebase: dynamic import + signInWithPopup -----
  const handleFirebaseLogin = async () => {
    setStatus("Googleに接続中...");
    setError("");
    try {
      // @ts-ignore — CDN URL dynamic import, no TypeScript type declarations available
      const { initializeApp, getApps } =
        (await import("https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js")) as {
          initializeApp: (config: object) => object;
          getApps: () => object[];
        };
      // @ts-ignore
      const { getAuth, signInWithPopup, GoogleAuthProvider } =
        (await import("https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js")) as {
          getAuth: () => object;
          signInWithPopup: (
            auth: object,
            provider: object,
          ) => Promise<{ user: { getIdToken: () => Promise<string> } }>;
          GoogleAuthProvider: new () => object;
        };

      if (!firebaseInitialized.current) {
        if (getApps().length === 0) initializeApp(FIREBASE_CONFIG);
        firebaseInitialized.current = true;
      }

      const auth = getAuth();
      setStatus("本人確認中...");
      const result = await signInWithPopup(auth, new GoogleAuthProvider());
      const idToken = await result.user.getIdToken();

      // Store token in localStorage — AuthContext will pick it up
      localStorage.setItem("id_token", idToken);
      window.dispatchEvent(new Event("storage"));
      navigate("/", { replace: true });
    } catch (e: unknown) {
      const msg =
        (e as { message?: string }).message ?? "ログインに失敗しました";
      setError(msg);
      setStatus("");
    }
  };

  const providerLabel =
    authProvider === "aws"
      ? "Cognito"
      : authProvider === "azure"
        ? "Azure AD"
        : authProvider === "firebase"
          ? "Google"
          : "—";

  const handleLogin = isFirebase ? handleFirebaseLogin : handleRedirectLogin;

  return (
    <section className="panel">
      <h1>Login</h1>

      <p>Sign in with your {providerLabel} account</p>

      <Alert type="error" message={error} />

      <div className="actions">
        <button
          className="button"
          type="button"
          onClick={handleLogin}
          disabled={!!status}
        >
          <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 10V7a5 5 0 0 1 10 0v3" />
            <rect x="4" y="10" width="16" height="10" rx="2" />
          </svg>
          <span>Sign in with {providerLabel}</span>
        </button>
      </div>

      {status && (
        <p className="muted" style={{ marginTop: "0.5rem" }}>
          {status}
        </p>
      )}
    </section>
  );
}
