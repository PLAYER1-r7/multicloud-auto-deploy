import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

/**
 * Handles OAuth2 implicit-flow callback.
 * Cognito:  /sns/auth/callback#access_token=…&id_token=…&expires_in=…
 * Azure AD: /sns/auth/callback#id_token=…
 */
export default function CallbackPage() {
  const { setTokens } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("Processing tokens...");

  useEffect(() => {
    const hash = window.location.hash.slice(1); // remove leading '#'
    if (!hash) {
      setStatus("No token in URL. Please retry login.");
      return;
    }

    const params = new URLSearchParams(hash);

    const error = params.get("error");
    if (error) {
      const desc = params.get("error_description") ?? "";
      setStatus(`Login error: ${error} — ${desc}`);
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

    // Clear the hash from the URL bar, then redirect to profile
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
