import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { getTokenFromCode } from "../config/auth";

/**
 * Handles OAuth2 callback for two flows:
 *
 * 1. PKCE authorization code flow (Cognito AWS):
 *    /sns/auth/callback?code=AUTH_CODE
 *    → POST /oauth2/token (code + code_verifier) → tokens
 *
 * 2. Implicit flow (Azure AD):
 *    /sns/auth/callback#id_token=…
 *    → parse hash fragment directly
 */
export default function CallbackPage() {
  const { setTokens } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("Processing tokens...");

  useEffect(() => {
    // ---- PKCE authorization code flow ----
    const searchParams = new URLSearchParams(window.location.search);
    const code = searchParams.get("code");
    const oauthError = searchParams.get("error");

    if (oauthError) {
      const desc = searchParams.get("error_description") ?? "";
      setStatus(`Login error: ${oauthError} — ${desc}`);
      return;
    }

    if (code) {
      // Exchange authorization code for tokens via Cognito /oauth2/token
      getTokenFromCode(code)
        .then(({ idToken, accessToken, expiresIn }) => {
          if (!idToken && !accessToken) {
            setStatus("Token exchange succeeded but no tokens returned");
            return;
          }
          setTokens({ idToken, accessToken, expiresIn });
          // Clear ?code= from URL bar, then redirect to profile
          history.replaceState(null, "", window.location.pathname);
          navigate("/profile", { replace: true });
        })
        .catch((e: unknown) => {
          const msg =
            (e as { message?: string }).message ?? "Token exchange failed";
          setStatus(`Error: ${msg}`);
        });
      return;
    }

    // ---- Implicit flow fallback (Azure AD: #id_token=…) ----
    const hash = window.location.hash.slice(1);
    if (!hash) {
      setStatus("No token in URL. Please retry login.");
      return;
    }

    const params = new URLSearchParams(hash);
    const hashError = params.get("error");
    if (hashError) {
      const desc = params.get("error_description") ?? "";
      setStatus(`Login error: ${hashError} — ${desc}`);
      return;
    }

    const idToken = params.get("id_token") ?? undefined;
    const accessToken = params.get("access_token") ?? undefined;
    const expiresIn = Number(params.get("expires_in") ?? 3600);

    if (!idToken && !accessToken) {
      setStatus(
        `Token missing. Params: ${Array.from(params.keys()).join(", ")}`,
      );
      return;
    }

    setTokens({ idToken, accessToken, expiresIn });
    history.replaceState(null, "", window.location.pathname);
    navigate("/profile", { replace: true });
  }, [setTokens, navigate]);

  return (
    <section className="panel">
      <h1>Signing you in</h1>
      <p className="muted">{status}</p>
    </section>
  );
}
